import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import type {
  ActiveIssue,
  ActivityItem,
  AggregationMetric,
  DashboardSummary,
  PipelineRunListItem,
} from "../lib/api-contract.ts";
import { activeIssueHref, activityHref, presentMetric, presentOverallState } from "../lib/aggregation-adapters.ts";
import { latestRunHref, presentDashboardSummary } from "../lib/dashboard-adapters.ts";
import { environmentApiKey } from "../lib/environment-context.ts";

const environment = { environment_key: "production", name: "Production" };
const eventsPipeline = { pipeline_key: "events-processing", name: "Events Processing", operational_status: "FAILED" as const };
const billingPipeline = { pipeline_key: "billing-reconciliation", name: "Billing Reconciliation", operational_status: "WARNING" as const };
const eventsSource = { source_key: "events-kafka", name: "Events Kafka", source_type: "KAFKA" as const, operational_status: "DISCONNECTED" as const };
const billingSource = { source_key: "billing-postgres", name: "Billing PostgreSQL", source_type: "POSTGRESQL" as const, operational_status: "WARNING" as const };

function metric(overrides: Partial<AggregationMetric> = {}): AggregationMetric {
  return {
    availability: "AVAILABLE",
    unit: "PERCENT",
    value: 50,
    numerator: 2,
    denominator: 4,
    sample_count: 4,
    previous: { availability: "INSUFFICIENT_DATA", value: null, sample_count: 0 },
    delta: null,
    points: [],
    reason: null,
    ...overrides,
  };
}

function run(overrides: Partial<PipelineRunListItem> = {}): PipelineRunListItem {
  return {
    corvetra_run_id: "run_01J94EVT18",
    pipeline: eventsPipeline,
    source: eventsSource,
    environment,
    status: "FAILED",
    stage: "EXTRACT",
    started_at: "2026-08-10T14:41:03Z",
    completed_at: "2026-08-10T14:42:38.412Z",
    duration_seconds: 95.412,
    platform_code: "PIPELINE_EXECUTION_FAILED",
    vendor_code: "SASL_AUTHENTICATION_FAILED",
    rule_code: null,
    active_alert_count: 1,
    ...overrides,
  };
}

function issue(overrides: Partial<ActiveIssue> = {}): ActiveIssue {
  return {
    issue_key: "ALT-1042",
    origin: "ALERT",
    severity: "CRITICAL",
    title: "Pipeline execution failing",
    message: "Events Kafka rejected credentials.",
    platform_code: "PIPELINE_EXECUTION_FAILED",
    vendor_code: "SASL_AUTHENTICATION_FAILED",
    rule_code: null,
    observed_at: "2026-08-10T14:42:38.412Z",
    alert_key: "ALT-1042",
    alert_status: "OPEN",
    environment,
    pipeline: eventsPipeline,
    source: eventsSource,
    run: run(),
    validation: null,
    technical_evidence_count: 5,
    latest_event_key: "evt-001",
    ...overrides,
  };
}

test("Dashboard preserves backend CRITICAL and NO_DATA state semantics", () => {
  assert.equal(presentOverallState("AVAILABLE", "CRITICAL"), "CRITICAL");
  assert.equal(presentOverallState("NO_DATA", null), "Not available / No evaluable data");
});

test("Dashboard summary uses exact backend counts instead of fixture totals", () => {
  const summary: DashboardSummary = {
    configured_pipelines: 3,
    enabled_pipelines: 3,
    successful_runs: 2,
    failed_runs: 2,
    active_alerts: { total: 2, critical: 1, warning: 1 },
    sources: 3,
    non_disabled_sources: 3,
  };
  assert.deepEqual(presentDashboardSummary(summary).map(({ label, value }) => [label, value]), [
    ["Configured Pipelines", "3"],
    ["Successful Runs", "2"],
    ["Failed Runs", "2"],
    ["Active Alerts", "2"],
    ["Sources", "3"],
  ]);
  assert.equal(presentDashboardSummary(summary)[3].detail, "1 critical · 1 warning");
});

test("Dashboard health indicators honor all availability states", () => {
  assert.equal(presentMetric(metric({ value: 50 })).value, "50%");
  assert.equal(presentMetric(metric({ availability: "INSUFFICIENT_DATA", value: null, sample_count: 0 })).value, "Insufficient data");
  assert.equal(presentMetric(metric({ availability: "UNSUPPORTED", value: null, sample_count: 0, reason: "Freshness history is unsupported" })).value, "Not available");
});

test("Dashboard active issues retain canonical alert and source drill-down identity", () => {
  const issues = [
    issue(),
    issue({
      issue_key: "ALT-1040",
      alert_key: "ALT-1040",
      severity: "WARNING",
      pipeline: billingPipeline,
      source: billingSource,
      run: run({
        corvetra_run_id: "run_01J97BIL02",
        pipeline: billingPipeline,
        source: billingSource,
        stage: "VALIDATE",
        platform_code: "VALIDATION_CHECK_FAILED",
        vendor_code: null,
        rule_code: "CHECK_UNIQUENESS_VIOLATION",
      }),
      platform_code: "VALIDATION_CHECK_FAILED",
      vendor_code: null,
      rule_code: "CHECK_UNIQUENESS_VIOLATION",
    }),
    issue({
      issue_key: "source:billing-postgres:warning",
      origin: "SOURCE",
      alert_key: null,
      alert_status: null,
      pipeline: null,
      source: billingSource,
      run: null,
      severity: "WARNING",
    }),
  ];
  assert.deepEqual(issues.map(activeIssueHref), [
    "/alerts/ALT-1042",
    "/alerts/ALT-1040",
    "/data-sources/billing-postgres",
  ]);
});

test("latest runs preserve product IDs, stages, and technical-code separation", () => {
  const events = run();
  const billing = run({
    corvetra_run_id: "run_01J97BIL02",
    pipeline: billingPipeline,
    source: billingSource,
    stage: "VALIDATE",
    platform_code: "VALIDATION_CHECK_FAILED",
    vendor_code: null,
    rule_code: "CHECK_UNIQUENESS_VIOLATION",
  });
  assert.equal(latestRunHref(events), "/pipeline-runs/run_01J94EVT18");
  assert.equal(events.stage, "EXTRACT");
  assert.equal(events.vendor_code, "SASL_AUTHENTICATION_FAILED");
  assert.equal(latestRunHref(billing), "/pipeline-runs/run_01J97BIL02");
  assert.equal(billing.pipeline.operational_status, "WARNING");
  assert.equal(billing.vendor_code, null);
  assert.equal(billing.rule_code, "CHECK_UNIQUENESS_VIOLATION");
});

test("recent activity links use canonical run and log scopes without actors or synthetic recency", () => {
  const activity: ActivityItem = {
    kind: "TECHNICAL_EVENT",
    occurred_at: "2026-08-10T14:42:38.412Z",
    environment,
    pipeline: eventsPipeline,
    source: eventsSource,
    run: run(),
    event_key: "evt-001",
    level: "ERROR",
    stage: "EXTRACT",
    platform_code: "PIPELINE_EXECUTION_FAILED",
    vendor_code: "SASL_AUTHENTICATION_FAILED",
    rule_code: null,
    message: "Events Kafka rejected credentials.",
  };
  assert.equal(activityHref(activity), "/logs?run=run_01J94EVT18&pipeline=events-processing&source=events-kafka");
});

test("Production environment maps coherently to the canonical backend key", () => {
  assert.equal(environmentApiKey("Production"), "production");
  assert.equal(environmentApiKey("Staging"), "staging");
  assert.equal(environmentApiKey("Development"), "development");
});

test("production Dashboard uses one aggregation read and no fixture source", async () => {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const dashboard = await readFile(`${root}/components/dashboard.tsx`, "utf8");
  assert.match(dashboard, /\/api\/v1\/dashboard/);
  assert.doesNotMatch(dashboard, /dashboard-data|pipelines-data|canonical-demo|DEMO_NOW|mockNow/);
  assert.doesNotMatch(dashboard, /\/api\/v1\/(pipelines|pipeline-runs|alerts|monitoring|health-metrics)/);
  assert.doesNotMatch(dashboard, /13 pipelines|value:\s*"4"|2 min ago|Today|Yesterday|actor|trigger|records processed|historical delta/i);
});

test("global shell is truthful about alert count, search, profile, and Settings", async () => {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const shell = await readFile(`${root}/components/app-shell.tsx`, "utf8");
  assert.doesNotMatch(shell, /count:\s*4|searchItems|Search anything|Customer Ingestion.*Search|Sidney Weiser|sidney@example|Usage this month|68% of included runs/);
  assert.match(shell, /Global search is not available in this release/);
  assert.match(shell, /Authenticated session/);
  assert.match(shell, /\/api\/auth\/logout/);
  assert.match(shell, /Demo-only settings; changes are not persisted/);
});

test("static owner walkthrough routes remain complete across all API-backed screens", async () => {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const files = [
    "components/dashboard.tsx",
    "components/alert-detail.tsx",
    "components/pipeline-detail.tsx",
    "components/pipeline-run-detail.tsx",
    "components/validation-detail.tsx",
    "components/logs.tsx",
  ];
  const text = (await Promise.all(files.map((file) => readFile(`${root}/${file}`, "utf8"))).then((items) => items.join("\n")));
  assert.match(text, /\/alerts\/\$\{/);
  assert.match(text, /\/pipelines\/\$\{/);
  assert.match(text, /\/pipeline-runs\/\$\{/);
  assert.match(text, /\/validation\/\$\{/);
  assert.match(text, /\/logs/);
  assert.doesNotMatch(text, /generateStaticParams|dynamicParams\s*=\s*false/);
});

test("Dashboard reuses cancellation, normalized errors, and stale-response prevention", async () => {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const [dashboard, hook, client] = await Promise.all([
    readFile(`${root}/components/dashboard.tsx`, "utf8"),
    readFile(`${root}/lib/use-api-query.ts`, "utf8"),
    readFile(`${root}/lib/api-client.ts`, "utf8"),
  ]);
  assert.match(dashboard, /useApiQuery/);
  assert.match(dashboard, /permission/);
  assert.match(dashboard, /unavailable/);
  assert.match(hook, /AbortController/);
  assert.match(hook, /requestNumber/);
  assert.match(hook, /kind === "cancelled"/);
  for (const status of ["401", "403", "422", "503"]) assert.match(client, new RegExp(status));
});
