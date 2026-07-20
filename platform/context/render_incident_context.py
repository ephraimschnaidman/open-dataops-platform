from __future__ import annotations

from decimal import Decimal
from typing import Protocol

ACTION_CODE = "INVESTIGATE_UPSTREAM_INGESTION_AND_VERIFY_THRESHOLD"
SCHEMA_CHANGE_ACTION_CODE = "REVIEW_SCHEMA_CHANGE_AND_VALIDATE_CONSUMERS"


class StructuredIncidentContext(Protocol):
    qualified_table: str
    evaluation_status: str
    severity: str
    expected_freshness_hours: Decimal | None
    observed_freshness_hours: Decimal | None
    recommended_action_code: str
    change_type: str | None
    affected_column: str | None


def _display(value: Decimal | None) -> str:
    return "unknown" if value is None else str(value)


def render_what_happened(context: StructuredIncidentContext) -> str:
    if context.change_type is not None:
        verb = {
            "COLUMN_ADDED": "was added",
            "COLUMN_REMOVED": "was removed",
            "COLUMN_TYPE_CHANGED": "changed data types",
        }.get(context.change_type)
        if verb is None or not context.affected_column:
            raise ValueError(f"Unsupported schema change metadata {context.change_type!r}")
        return (
            f"A schema change was detected for {context.qualified_table}.\n"
            f"Column {context.affected_column} {verb}."
        )
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
    if context.change_type is not None:
        return "The table structure has changed and may affect downstream consumers."
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
    if context.recommended_action_code == SCHEMA_CHANGE_ACTION_CODE:
        return (
            "Review the schema change and verify that downstream consumers are expected "
            "to handle it."
        )
    if context.recommended_action_code != ACTION_CODE:
        raise ValueError(f"Unsupported action code {context.recommended_action_code!r}")
    return (
        "Investigate the upstream ingestion process and verify that the configured "
        f"freshness threshold is appropriate for {context.qualified_table}."
    )
