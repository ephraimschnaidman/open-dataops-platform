from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

STALE_DATA_CONTEXT_VERSION = "stale_data_v1"
SUPPORTED_INCIDENT_TYPE = "STALE_DATA"
RECOMMENDED_ACTION_CODE = "INVESTIGATE_UPSTREAM_INGESTION_AND_VERIFY_THRESHOLD"
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


@dataclass(frozen=True)
class IncidentContext:
    context_version: str
    qualified_table: str
    evaluation_status: str
    severity: str
    expected_freshness_hours: Decimal | None
    observed_freshness_hours: Decimal | None
    recommended_action_code: str


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
