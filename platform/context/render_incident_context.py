from __future__ import annotations

from decimal import Decimal
from typing import Protocol

ACTION_CODE = "INVESTIGATE_UPSTREAM_INGESTION_AND_VERIFY_THRESHOLD"


class StructuredIncidentContext(Protocol):
    qualified_table: str
    evaluation_status: str
    severity: str
    expected_freshness_hours: Decimal | None
    observed_freshness_hours: Decimal | None
    recommended_action_code: str


def _display(value: Decimal | None) -> str:
    return "unknown" if value is None else str(value)


def render_what_happened(context: StructuredIncidentContext) -> str:
    status = {
        "EXCEEDED_THRESHOLD": "was exceeded",
        "WITHIN_THRESHOLD": "was not exceeded",
        "UNKNOWN": "could not be evaluated",
    }[context.evaluation_status]
    return (
        f"The freshness threshold for {context.qualified_table} {status}. "
        f"Expected <= {_display(context.expected_freshness_hours)} hours; "
        f"observed {_display(context.observed_freshness_hours)} hours."
    )


def render_why_it_matters(context: StructuredIncidentContext) -> str:
    detail = {
        "EXCEEDED_THRESHOLD": "The data is older than the configured freshness expectation.",
        "WITHIN_THRESHOLD": "The observed age is within the configured freshness expectation.",
        "UNKNOWN": "The freshness values could not be compared.",
    }[context.evaluation_status]
    return (
        f"This is a {context.severity} severity incident affecting "
        f"{context.qualified_table}. {detail}"
    )


def render_recommended_next_step(context: StructuredIncidentContext) -> str:
    if context.recommended_action_code != ACTION_CODE:
        raise ValueError(f"Unsupported action code {context.recommended_action_code!r}")
    return (
        "Investigate the upstream ingestion process and verify that the configured "
        f"freshness threshold is appropriate for {context.qualified_table}."
    )
