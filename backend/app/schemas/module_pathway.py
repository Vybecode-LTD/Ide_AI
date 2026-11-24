"""
module_pathway.py — Pydantic v2 schemas for the modular pathway system.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.limits import CHAT_MESSAGE_MAX_CHARS


# --- Categorization ---

class CategorizeResponse(BaseModel):
    """Response from AI project categorization."""
    primary_category: str
    secondary_category: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


# --- Module Library Metadata ---

class ModuleDefinition(BaseModel):
    """A single module from the library."""
    id: str
    label: str
    group: str
    description: str
    estimated_time_lite: str
    estimated_time_deep: str
    default_mode: str = "lite"


class ConceptCategory(BaseModel):
    """A concept category with its default module stack."""
    id: str
    label: str
    examples: list[str] = []
    default_modules: list[str] = []


# --- Pathway Assembly ---

class PathwayModuleEntry(BaseModel):
    """A module in the assembled pathway, with AI reasoning."""
    module_id: str
    label: str
    description: str
    group: str
    estimated_time: str
    mode: str = "lite"  # lite | deep
    reason: str = ""  # Why the AI included this module


class PathwayAssembleResponse(BaseModel):
    """Response from pathway assembly."""
    modules: list[PathwayModuleEntry]
    primary_category: str
    secondary_category: Optional[str] = None


class PathwayRead(BaseModel):
    """Current pathway state for a project."""
    id: uuid.UUID
    project_id: uuid.UUID
    modules: list[str]
    lite_deep_settings: dict[str, str] = {}
    status: str = "pending"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PathwayUpdate(BaseModel):
    """User edits to the pathway before locking."""
    modules: list[str]
    lite_deep_settings: dict[str, str] = {}


# --- Module Execution ---

class ModuleStartResponse(BaseModel):
    """Response when starting a module session."""
    module_id: str
    question: str
    question_number: int = 1
    total_questions: int = 3


class ModuleRespondPayload(BaseModel):
    """User's response to a module question.

    Length-capped: each answer is sent to Claude and replayed on later turns.
    """
    content: str = Field(min_length=1, max_length=CHAT_MESSAGE_MAX_CHARS)


class ModuleRespondResponse(BaseModel):
    """AI response after processing a module answer."""
    question: Optional[str] = None  # None when module is complete
    question_number: int
    total_questions: int
    complete: bool = False
    summary: Optional[dict] = None  # Populated when complete


class ModuleResponseRead(BaseModel):
    """Read schema for a module's collected responses."""
    id: uuid.UUID
    project_id: uuid.UUID
    module_id: str
    responses: dict
    status: str = "pending"
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModuleSummaryResponse(BaseModel):
    """Structured summary of a completed module."""
    module_id: str
    label: str
    status: str
    responses: dict
    extracted: dict = {}  # Structured output extracted from responses
