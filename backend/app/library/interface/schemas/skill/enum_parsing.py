"""Enum parsing helpers for skill API schema boundaries."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import ItemStatus
from app.library.domain.event_enum.skill_enums import RiskLevel


# Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
def item_status(value: object) -> ItemStatus:
    """Accept public JSON item status values at API boundaries.

    Args:
        value [object]: Value supplied to item_status.

    Returns:
        ItemStatus: Value produced by item_status.
    """
    if isinstance(value, ItemStatus):
        parsed_status = value
    elif isinstance(value, str):
        parsed_status = ItemStatus(value)
    else:
        raise ValueError("status must be a valid item status")
    return parsed_status


# Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
def risk_level(value: object) -> RiskLevel:
    """Accept public JSON risk level values at API boundaries.

    Args:
        value [object]: Value supplied to risk_level.

    Returns:
        RiskLevel: Value produced by risk_level.
    """
    if isinstance(value, RiskLevel):
        parsed_level = value
    elif isinstance(value, str):
        parsed_level = RiskLevel(value)
    else:
        raise ValueError("risk_level must be a valid risk level")
    return parsed_level
