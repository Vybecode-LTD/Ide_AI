"""
billing.py — Stripe subscription billing. Creates checkout sessions and
manages the billing portal.

Stripe price IDs must be configured as environment variables. The webhook
endpoint handles subscription lifecycle events and persists full
subscription state (ID, status, price, period end) so the entitlement
service can make plan-limit decisions from local state.
"""
import logging
import stripe
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

stripe.api_key = settings.STRIPE_SECRET_KEY

# Maps logical plan IDs → Stripe price IDs (set in env)
PRICE_MAP = {
    "price_basic_monthly": settings.STRIPE_PRICE_BASIC_MONTHLY,
    "price_basic_yearly": settings.STRIPE_PRICE_BASIC_YEARLY,
    "price_pro_monthly": settings.STRIPE_PRICE_PRO_MONTHLY,
    "price_pro_yearly": settings.STRIPE_PRICE_PRO_YEARLY,
}


class CheckoutRequest(BaseModel):
    price_id: str
    cycle: Optional[str] = "monthly"


class PortalRequest(BaseModel):
    return_url: Optional[str] = None


@router.post("/checkout")
async def create_checkout_session(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout Session for subscription signup."""
    stripe_price = PRICE_MAP.get(payload.price_id)
    if not stripe_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid price ID",
        )

    try:
        checkout_kwargs = {
            "mode": "subscription",
            "payment_method_types": ["card"],
            "line_items": [{"price": stripe_price, "quantity": 1}],
            "client_reference_id": str(current_user.id),
            "success_url": f"{settings.FRONTEND_URL}/home?billing=success",
            "cancel_url": f"{settings.FRONTEND_URL}/#pricing",
            "metadata": {
                "user_id": str(current_user.id),
                "price_id": payload.price_id,
            },
        }
        # Reuse existing Stripe customer to avoid duplicates
        if current_user.stripe_customer_id:
            checkout_kwargs["customer"] = current_user.stripe_customer_id
        else:
            checkout_kwargs["customer_email"] = current_user.email
        session = stripe.checkout.Session.create(**checkout_kwargs)
    except stripe.StripeError as e:
        logger.error("Stripe checkout error for user %s: %s", current_user.id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider error. Please try again.",
        )

    return {"checkout_url": session.url}


@router.post("/portal")
async def create_billing_portal(
    payload: PortalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Billing Portal session for managing subscriptions."""
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found",
        )

    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=payload.return_url or f"{settings.FRONTEND_URL}/settings",
        )
    except stripe.StripeError as e:
        logger.error("Stripe portal error for user %s: %s", current_user.id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider error. Please try again.",
        )

    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events for subscription lifecycle."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        # Link Stripe customer to our user and persist subscription state
        user_id = data.get("client_reference_id")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if user_id and customer_id:
            from sqlalchemy import select, update
            from app.models.user import User as UserModel
            import uuid

            values = {
                "stripe_customer_id": customer_id,
                "account_type": _plan_from_metadata(data.get("metadata", {})),
            }
            # Persist subscription ID from the checkout session
            if subscription_id:
                values["stripe_subscription_id"] = subscription_id
                values["subscription_status"] = "active"
                # Fetch the full subscription to get price + period end
                try:
                    sub = stripe.Subscription.retrieve(subscription_id)
                    if sub.get("items", {}).get("data"):
                        values["subscription_price_id"] = (
                            sub["items"]["data"][0]["price"]["id"]
                        )
                    if sub.get("current_period_end"):
                        values["subscription_current_period_end"] = (
                            datetime.fromtimestamp(
                                sub["current_period_end"], tz=timezone.utc
                            )
                        )
                except stripe.StripeError:
                    pass  # Non-critical — subscription.updated will fill these

            await db.execute(
                update(UserModel)
                .where(UserModel.id == uuid.UUID(user_id))
                .values(**values)
            )
            await db.commit()

    elif event_type in (
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        customer_id = data.get("customer")
        if customer_id:
            from sqlalchemy import select, update
            from app.models.user import User as UserModel

            sub_status = data.get("status", "canceled")
            is_active = sub_status in ("active", "trialing")
            new_type = _plan_from_price(data) if is_active else "free"

            values = {
                "account_type": new_type,
                "stripe_subscription_id": data.get("id"),
                "subscription_status": sub_status,
            }

            # Extract the price ID from the first line item
            try:
                values["subscription_price_id"] = (
                    data["items"]["data"][0]["price"]["id"]
                )
            except (KeyError, IndexError):
                pass

            # Convert Unix timestamp → aware datetime
            period_end = data.get("current_period_end")
            if period_end:
                values["subscription_current_period_end"] = (
                    datetime.fromtimestamp(period_end, tz=timezone.utc)
                )
            elif event_type == "customer.subscription.deleted":
                values["subscription_current_period_end"] = None

            await db.execute(
                update(UserModel)
                .where(UserModel.stripe_customer_id == customer_id)
                .values(**values)
            )
            await db.commit()

    return {"received": True}


def _plan_from_metadata(metadata: dict) -> str:
    """Derive plan name from checkout metadata."""
    price_id = metadata.get("price_id", "")
    if "pro" in price_id:
        return "pro"
    if "basic" in price_id:
        return "basic"
    return "free"


def _plan_from_price(subscription: dict) -> str:
    """Derive plan name from active subscription price."""
    try:
        price_id = subscription["items"]["data"][0]["price"]["id"]
        if price_id in (settings.STRIPE_PRICE_PRO_MONTHLY, settings.STRIPE_PRICE_PRO_YEARLY):
            return "pro"
        if price_id in (settings.STRIPE_PRICE_BASIC_MONTHLY, settings.STRIPE_PRICE_BASIC_YEARLY):
            return "basic"
    except (KeyError, IndexError):
        pass
    return "free"
