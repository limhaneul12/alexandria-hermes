"""Prompt concept enum definitions."""

from __future__ import annotations

from enum import StrEnum


class PromptContentFormat(StrEnum):
    """Prompt body serialization format."""

    MARKDOWN = "MARKDOWN"
    XML = "XML"
    JSON = "JSON"
    TEXT = "TEXT"


class PromptKind(StrEnum):
    """Where or how a prompt is meant to be used."""

    SYSTEM = "SYSTEM"
    DEVELOPER = "DEVELOPER"
    USER_TEMPLATE = "USER_TEMPLATE"
    EVAL = "EVAL"
    TOOL_GUIDE = "TOOL_GUIDE"
    CHAIN = "CHAIN"


class PromptDomain(StrEnum):
    """Business domain for prompt discovery."""

    DEVELOPMENT = "DEVELOPMENT"
    DESIGN = "DESIGN"
    WRITING = "WRITING"
    RESEARCH = "RESEARCH"
    ANALYSIS = "ANALYSIS"
    PLANNING = "PLANNING"
    REVIEW = "REVIEW"
    TESTING = "TESTING"
    DEBUGGING = "DEBUGGING"
    OPERATIONS = "OPERATIONS"
    DATA = "DATA"
    EDUCATION = "EDUCATION"
    MARKETING = "MARKETING"
    PRODUCT = "PRODUCT"
    SECURITY = "SECURITY"
    GENERAL = "GENERAL"


class PromptTaskType(StrEnum):
    """Concrete task intent for prompt discovery."""

    CODE_GENERATION = "CODE_GENERATION"
    CODE_REVIEW = "CODE_REVIEW"
    TEST_GENERATION = "TEST_GENERATION"
    BUG_DIAGNOSIS = "BUG_DIAGNOSIS"
    FEATURE_PLANNING = "FEATURE_PLANNING"
    UI_COPYWRITING = "UI_COPYWRITING"
    DOCUMENT_SUMMARY = "DOCUMENT_SUMMARY"
    DOCUMENT_CREATION = "DOCUMENT_CREATION"
    REQUIREMENTS_ANALYSIS = "REQUIREMENTS_ANALYSIS"
    RESEARCH_SYNTHESIS = "RESEARCH_SYNTHESIS"
    IMAGE_PROMPTING = "IMAGE_PROMPTING"
    AGENT_INSTRUCTION = "AGENT_INSTRUCTION"
    TOOL_USAGE_GUIDE = "TOOL_USAGE_GUIDE"
    EVALUATION = "EVALUATION"
    GENERAL_TASK = "GENERAL_TASK"


class PromptDetailField(StrEnum):
    """Prompt details keys accepted by public patch payloads."""

    CONTENT_FORMAT = "content_format"
    PROMPT_KIND = "prompt_kind"
    PROMPT_DOMAIN = "prompt_domain"
    PROMPT_TASK_TYPE = "prompt_task_type"
    INPUT_VARIABLES = "input_variables"
    OUTPUT_FORMAT = "output_format"
    TARGET_ACTOR = "target_actor"
    TARGET_MODEL_FAMILY = "target_model_family"
    LANGUAGE = "language"
    RELATED_ITEM_IDS = "related_item_ids"
    SAFETY_NOTES = "safety_notes"
    VERSION = "version"
    CHANGE_SUMMARY = "change_summary"
