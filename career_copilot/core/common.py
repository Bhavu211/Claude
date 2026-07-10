"""Shared types used across multiple agents' input/output schemas.

Keeping these in one place means downstream agents (Gap Analysis, Critic,
Final Report, ...) can consume upstream agents' output without redefining
the same enums with slightly different values.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"


class RequirementPriority(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    NICE_TO_HAVE = "nice_to_have"


class VerbStrength(str, Enum):
    STRONG = "strong"
    WEAK = "weak"
    NEUTRAL = "neutral"


class QualityIssue(BaseModel):
    """A single flagged issue with enough context to act on without re-deriving it."""

    issue: str = Field(..., description="What is wrong")
    location: str = Field(..., description="Where in the source document this occurs")
    severity: Severity
    recommendation: str = Field(..., description="Concrete fix, not a vague suggestion")


class SourceRef(BaseModel):
    """A citation for a claim grounded in external research (e.g. web search).

    Used by any agent that runs a research phase, so a human (or the Critic
    Agent) can trace a claim back to where it came from.
    """

    title: str
    publisher: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None


class SourcedClaim(BaseModel):
    """A claim that must be traceable back to the document it came from.

    Used wherever an agent asserts something about the candidate ('has 5 years
    of X', 'led a team of 3') so a downstream Critic Agent can verify it was
    not fabricated.
    """

    claim: str
    evidence_text: str = Field(..., description="Verbatim or close paraphrase from the source document")
    source_section: str = Field(..., description="Section/heading the evidence was found in")
    confidence: ConfidenceLevel
