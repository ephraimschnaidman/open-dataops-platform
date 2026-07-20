from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

STALE_DATA_CONTEXT_VERSION = "stale_data_v1"
SCHEMA_CHANGE_CONTEXT_VERSION = "schema_change_v1"
SUPPORTED_INCIDENT_TYPE = "STALE_DATA"
RECOMMENDED_ACTION_CODE = "INVESTIGATE_UPSTREAM_INGESTION_AND_VERIFY_THRESHOLD"
SCHEMA_CHANGE_ACTION_CODE = "REVIEW_SCHEMA_CHANGE_AND_VALIDATE_CONSUMERS"
SCHEMA_CHANGE_TYPES = {
    "COLUMN_ADDED": "COLUMN_ADDED",
    "COLUMN_REMOVED": "COLUMN_REMOVED",
    "COLUMN_TYPE_CHANGED": "COLUMN_TYPE_CHANGED",
    # The current detector uses this source name; context exposes the v1 name above.
    "DATA_TYPE_CHANGED": "COLUMN_TYPE_CHANGED",
}
EVALUATION_STATUSES = frozenset({"EXCEEDED_THRESHOLD", "WITHIN_THRESHOLD", "UNKNOWN"})
_HOURS_PATTERN = re.compile(r"^\s*(?:<=\s*)?([0-9]+(?:\.[0-9]+)?)\s+hours?\s*$", re.I)


class IncidentContextRuleError(ValueError):
    """Raised when incident metadata cannot be converted safely."""


@dataclass(frozen=True)
class IncidentMetadata:
    incident_type: str
    severity: str
    table_schema: str
    table_name: str
    expected_value: str | None
    observed_value: str | None
    incident_status: str
    column_name: str | None = None


@dataclass(frozen=True)
class IncidentContext:
    context_version: str
    qualified_table: str
    evaluation_status: str
    severity: str
    expected_freshness_hours: Decimal | None
    observed_freshness_hours: Decimal | None
    recommended_action_code: str
    change_type: str | None = None
    affected_column: str | None = None


def parse_freshness_hours(value: str | None) -> Decimal | None:
    """Parse a detector freshness display value into non-negative hours."""
    if value is None:
        return None
    match = _HOURS_PATTERN.fullmatch(value)
    if not match:
        return None
    try:
        return Decimal(match.group(1))
    except InvalidOperation:
        return None


def qualify_table(table_schema: str, table_name: str) -> str:
    if not table_schema or not table_name:
        raise IncidentContextRuleError(
            "STALE_DATA context requires non-empty table_schema and table_name"
        )
    return f"{table_schema}.{table_name}"


def evaluate_freshness(expected: Decimal | None, observed: Decimal | None) -> str:
    if expected is None or observed is None:
        return "UNKNOWN"
    return "EXCEEDED_THRESHOLD" if observed > expected else "WITHIN_THRESHOLD"


def generate_stale_data_context(incident: IncidentMetadata) -> IncidentContext:
    """Build deterministic structured Version 1 context for STALE_DATA."""
    if incident.incident_type != SUPPORTED_INCIDENT_TYPE:
        raise IncidentContextRuleError(
            f"Unsupported incident type {incident.incident_type!r}; "
            f"only {SUPPORTED_INCIDENT_TYPE} is supported"
        )
    if not incident.severity:
        raise IncidentContextRuleError("STALE_DATA context requires severity")

    expected = parse_freshness_hours(incident.expected_value)
    observed = parse_freshness_hours(incident.observed_value)
    return IncidentContext(
        context_version=STALE_DATA_CONTEXT_VERSION,
        qualified_table=qualify_table(incident.table_schema, incident.table_name),
        evaluation_status=evaluate_freshness(expected, observed),
        severity=incident.severity,
        expected_freshness_hours=expected,
        observed_freshness_hours=observed,
        recommended_action_code=RECOMMENDED_ACTION_CODE,
    )


def generate_schema_change_context(incident: IncidentMetadata) -> IncidentContext:
    """Build deterministic structured Version 1 context for supported schema changes."""
    if incident.incident_type not in SCHEMA_CHANGE_TYPES:
        raise IncidentContextRuleError(
            f"Unsupported schema change type {incident.incident_type!r}"
        )
    if not incident.severity:
        raise IncidentContextRuleError("SCHEMA_CHANGE context requires severity")
    if not incident.column_name:
        raise IncidentContextRuleError("SCHEMA_CHANGE context requires affected column")
    return IncidentContext(
        context_version=SCHEMA_CHANGE_CONTEXT_VERSION,
        qualified_table=qualify_table(incident.table_schema, incident.table_name),
        evaluation_status="UNKNOWN",
        severity=incident.severity,
        expected_freshness_hours=None,
        observed_freshness_hours=None,
        recommended_action_code=SCHEMA_CHANGE_ACTION_CODE,
        change_type=SCHEMA_CHANGE_TYPES[incident.incident_type],
        affected_column=incident.column_name,
    )
