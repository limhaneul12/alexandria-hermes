"""Hermes librarian collaboration enum definitions."""

from __future__ import annotations

from enum import StrEnum


class AcquisitionDecision(StrEnum):
    """Decision returned when Hermes asks for missing-capability help."""

    SUGGEST_HERMES_RESEARCH = "SUGGEST_HERMES_RESEARCH"
    DELEGATE_TO_LIBRARIAN = "DELEGATE_TO_LIBRARIAN"


class LibrarianDelegationStatus(StrEnum):
    """Status for the lightweight librarian delegation job contract."""

    ACCEPTED = "ACCEPTED"
    GUIDANCE_ONLY = "GUIDANCE_ONLY"
    COMPLETED = "COMPLETED"
    NOT_FOUND = "NOT_FOUND"


class SkillAcquisitionJobStatus(StrEnum):
    """Durable skill-acquisition job lifecycle status."""

    ACCEPTED = "ACCEPTED"
    GUIDANCE_ONLY = "GUIDANCE_ONLY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class LibrarianProfileRole(StrEnum):
    """Routing role assigned to a saved librarian profile."""

    DEFAULT_SEARCH = "DEFAULT_SEARCH"
    SPECIALIST = "SPECIALIST"
    QUALITY_REVIEWER = "QUALITY_REVIEWER"
    ARCHIVIST_CURATOR = "ARCHIVIST_CURATOR"


class QualityReviewRoutingToken(StrEnum):
    """Prompt token that can request a quality-review librarian profile."""

    SECURITY = "security"
    OAUTH = "oauth"
    AUTH = "auth"
    TOKEN = "token"
    SECRET = "secret"
    PRODUCTION = "production"
    DEPLOY = "deploy"
    RISK = "risk"
    DANGEROUS = "dangerous"
    REVIEW = "review"
    VALIDATE = "validate"
    VERIFY = "verify"
    CANDIDATE = "candidate"
    PROMPT = "prompt"


class ArchiveRoutingToken(StrEnum):
    """Prompt token that can request an archive-curator librarian profile."""

    ARCHIVE = "archive"
    CURATE = "curate"
    STALE = "stale"
    DUPLICATE = "duplicate"
    HYGIENE = "hygiene"


class LibrarianDelegateStatus(StrEnum):
    """Status for one synchronous librarian delegate lane."""

    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class LibrarianDelegateKind(StrEnum):
    """Kind of local delegate lane executed by the collaboration service."""

    LIBRARY_SEARCH = "LIBRARY_SEARCH"
    SPECIALTY_REVIEW = "SPECIALTY_REVIEW"
    QUALITY_REVIEW = "QUALITY_REVIEW"
    ARCHIVE_CURATION = "ARCHIVE_CURATION"
