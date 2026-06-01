/**
 * SignUpPage — Clerk-managed sign-up with dark glassmorphism styling.
 * After sign-up, checks for a pending plan selection and redirects to checkout.
 * @module pages/SignUpPage
 */
import { SignUp } from '@clerk/clerk-react'
import { PublicHeader } from '../components/layout/PublicHeader'

export function SignUpPage() {
  // If user selected a paid plan before signing up, redirect to checkout flow
  const pendingPlan = sessionStorage.getItem('pending_plan')
  const redirectUrl = pendingPlan ? '/checkout-redirect' : '/home'

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <PublicHeader />
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <SignUp
          routing="path"
          path="/sign-up"
          signInUrl="/sign-in"
          forceRedirectUrl={redirectUrl}
        />
      </div>
    </div>
  )
}
