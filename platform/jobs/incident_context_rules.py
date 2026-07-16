from __future__ import annotations

from dataclasses import dataclass

STALE_DATA_CONTEXT_VERSION = "stale_data_v1"
SUPPORTED_INCIDENT_TYPE = "STALE_DATA"


class IncidentContextRuleError(ValueError):
    """Raised when incident metadata cannot be rendered safely."""


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
    what_happened: str
    why_it_matters: str
    recommended_next_step: str


def generate_stale_data_context(incident: IncidentMetadata) -> IncidentContext:
    """Render deterministic Version 1 context from a STALE_DATA incident."""
    if incident.incident_type != SUPPORTED_INCIDENT_TYPE:
        raise IncidentContextRuleError(
            f"Unsupported incident type {incident.incident_type!r}; "
            f"only {SUPPORTED_INCIDENT_TYPE} is supported"
        )
    if not incident.expected_value or not incident.observed_value:
        raise IncidentContextRuleError(
            "STALE_DATA context requires expected_value and observed_value"
        )

    qualified_table = f"{incident.table_schema}.{incident.table_name}"
    return IncidentContext(
        context_version=STALE_DATA_CONTEXT_VERSION,
        what_happened=(
            f"The freshness threshold for {qualified_table} was exceeded. "
            f"Expected {incident.expected_value}; observed {incident.observed_value}."
        ),
        why_it_matters=(
            f"This is a {incident.severity} severity incident affecting {qualified_table}. "
            "The data is older than the configured freshness expectation."
        ),
        recommended_next_step=(
            "Investigate the upstream ingestion process and verify that the configured "
            f"freshness threshold is appropriate for {qualified_table}."
        ),
    )
