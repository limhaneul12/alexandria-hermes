"""Library search enum definitions."""

from __future__ import annotations

from enum import StrEnum


class SearchContentMode(StrEnum):
    """Content inclusion mode for broad library search."""

    CANDIDATE = "candidate"
    FULL = "full"


class SearchStrategy(StrEnum):
    """Candidate search strategy requested at the API boundary."""

    DEFAULT = "default"
    FTS = "fts"
    METADATA = "metadata"


class LibrarySearchField(StrEnum):
    """Allowed FTS fields for broad candidate search."""

    TITLE = "title"
    SUMMARY = "summary"
    TAGS = "tags"
    DETAILS = "details"
    CONTENT = "content"

    @classmethod
    def default_fields(cls) -> tuple[LibrarySearchField, ...]:
        """Return the default metadata-safe search fields.

        Returns:
            tuple[LibrarySearchField, ...]: Default candidate search fields.
        """
        return (cls.TITLE, cls.SUMMARY, cls.TAGS, cls.DETAILS)

    @classmethod
    def from_request_value(cls, value: str) -> LibrarySearchField:
        """Normalize one public field value into an enum member.

        Args:
            value: Raw field value from the API or CLI boundary.

        Returns:
            LibrarySearchField: Normalized enum member.
        """
        normalized = cls.CONTENT.value if value == "body" else value
        return cls(normalized)


class SkillPreviewKey(StrEnum):
    """Detail keys exposed in skill candidate previews."""

    PURPOSE = "purpose"
    REQUIRED_TOOLS = "required_tools"
    RISK_LEVEL = "risk_level"
    VERSION = "version"
    ACQUISITION_METHOD = "acquisition_method"


class PromptPreviewKey(StrEnum):
    """Detail keys exposed in prompt candidate previews."""

    PROMPT_KIND = "prompt_kind"
    PROMPT_DOMAIN = "prompt_domain"
    PROMPT_TASK_TYPE = "prompt_task_type"
    CONTENT_FORMAT = "content_format"
    LANGUAGE = "language"
    VERSION = "version"


class CommonPreviewKey(StrEnum):
    """Detail keys exposed in non-specialized candidate previews."""

    VERSION = "version"
    SOURCE_SUMMARY = "source_summary"
    CHANGE_SUMMARY = "change_summary"
