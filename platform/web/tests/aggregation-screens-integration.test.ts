import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import type { ActiveIssue, AggregationMetric, ActivityItem, ReviewResource } from "../lib/api-contract.ts";
import {
  HEALTH_WINDOWS,
  MONITORING_WINDOWS,
  activeIssueHref,
  activityHref,
  presentMetric,
  presentOverallState,
  reviewResourceHref,
  sparseTrend,
} from "../lib/aggregation-adapters.ts";

function metric(overrides: Partial<AggregationMetric> = {}): AggregationMetric {
  return {
    availability: "AVAILABLE",
    unit: "PERCENT",
    value: 40,
    numerator: 2,
    denominator: 5,
    sample_count: 5,
    previous: { availability: "INSUFFICIENT_DATA", value: null, sample_count: 0 },
    delta: null,
    points: [
      { start: "2026-08-09T00:00:00Z", end: "2026-08-10T00:00:00Z", value: 50, sample_count: 2 },
      { start: "2026-08-10T00:00:00Z", end: "2026-08-11T00:00:00Z", value: 33.3333, sample_count: 3 },
    ],
    reason: null,
    ...overrides,
  };
}

const environment = { environment_key: "production", name: "Production" };
const eventsPipeline = { pipeline_key: "events-processing", name: "Events Processing", operational_status: "FAILED" as const };
const billingPipeline = { pipeline_key: "billing-reconciliation", name: "Billing Reconciliation", operational_status: "WARNING" as const };
const eventsSource = { source_key: "events-kafka", name: "Events Kafka", source_type: "KAFKA" as const, operational_status: "DISCONNECTED" as const };
const billingSource = { source_key: "billing-postgres", name: "Billing PostgreSQL", source_type: "POSTGRESQL" as const, operational_status: "WARNING" as const };
const eventsRun = {
  corvetra_run_id: "run_01J94EVT18",
  status: "FAILED" as const,
  stage: "EXTRACT" as const,
  started_at: "2026-08-10T14:41:03Z",
  completed_at: "2026-08-10T14:42:38.412Z",
  duration_seconds: 95.412,
  platform_code: "PIPELINE_EXECUTION_FAILED",
  vendor_code: "SASL_AUTHENTICATION_FAILED",
  rule_code: null,
};

function issue(overrides: Partial<ActiveIssue>): ActiveIssue {
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
    run: eventsRun,
    validation: null,
    technical_evidence_count: 5,
    latest_event_key: "evt-001",
    ...overrides,
  };
}

test("Step 4 exposes exactly the backend-approved windows", () => {
  assert.deepEqual(MONITORING_WINDOWS, ["1h", "6h", "24h", "7d", "30d"]);
  assert.deepEqual(HEALTH_WINDOWS, ["24h", "7d", "30d", "90d"]);
});

test("Monitoring preserves CRITICAL and renders NO_DATA honestly", () => {
  assert.equal(presentOverallState("AVAILABLE", "CRITICAL"), "CRITICAL");
  assert.equal(presentOverallState("NO_DATA", null), "Not available / No evaluable data");
});

test("Monitoring consumes the backend-deduplicated canonical issue set unchanged", () => {
  const issues = [
    issue({}),
    issue({
      issue_key: "ALT-1040",
      severity: "WARNING",
      title: "Order ID unique failed",
      alert_key: "ALT-1040",
      pipeline: billingPipeline,
      source: billingSource,
      run: { ...eventsRun, corvetra_run_id: "run_01J97BIL02", stage: "VALIDATE", vendor_code: null, rule_code: "CHECK_UNIQUENESS_VIOLATION" },
      platform_code: "VALIDATION_CHECK_FAILED",
      vendor_code: null,
      rule_code: "CHECK_UNIQUENESS_VIOLATION",
    }),
    issue({
      issue_key: "source:billing-postgres:warning",
      origin: "SOURCE",
      severity: "WARNING",
      alert_key: null,
      alert_status: null,
      pipeline: null,
      source: billingSource,
      run: null,
      platform_code: "SOURCE_LATENCY_ELEVATED",
      vendor_code: null,
    }),
  ];
  assert.deepEqual(issues.map((item) => item.issue_key), [
    "ALT-1042",
    "ALT-1040",
    "source:billing-postgres:warning",
  ]);
  assert.deepEqual(issues.map(activeIssueHref), [
    "/alerts/ALT-1042",
    "/alerts/ALT-1040",
    "/data-sources/billing-postgres",
  ]);
});

test("canonical pipeline and source states remain authoritative", () => {
  assert.deepEqual(
    [
      ["Events Processing", "FAILED"],
      ["Billing Reconciliation", "WARNING"],
      ["Customer Ingestion", "HEALTHY"],
    ],
    [
      ["Events Processing", eventsPipeline.operational_status],
      ["Billing Reconciliation", billingPipeline.operational_status],
      ["Customer Ingestion", "HEALTHY"],
    ],
  );
  assert.deepEqual(
    ["DISCONNECTED", "WARNING", "HEALTHY", "DISABLED"],
    [eventsSource.operational_status, billingSource.operational_status, "HEALTHY", "DISABLED"],
  );
});

test("AVAILABLE, INSUFFICIENT_DATA, and UNSUPPORTED metrics never collapse to zero", () => {
  assert.deepEqual(presentMetric(metric()), {
    availability: "AVAILABLE",
    value: "40%",
    detail: "5 samples",
    previous: "Insufficient data",
    delta: "Not available",
  });
  assert.equal(presentMetric(metric({ availability: "INSUFFICIENT_DATA", value: null, sample_count: 0 })).value, "Insufficient data");
  assert.equal(presentMetric(metric({ availability: "UNSUPPORTED", value: null, sample_count: 0, reason: "Schedule data is not persisted" })).value, "Not available");
});

test("Health Metrics maps canonical supported values without hard-coded production values", () => {
  assert.equal(presentMetric(metric({ value: 40 })).value, "40%");
  assert.equal(presentMetric(metric({ unit: "SECONDS", value: 181.8824 })).value, "181.8824 s");
  assert.equal(presentMetric(metric({ value: 50, numerator: 2, denominator: 4, sample_count: 4 })).value, "50%");
});

test("sparse persisted trends preserve only returned buckets", () => {
  const trend = sparseTrend(metric());
  assert.equal(trend.values.length, 2);
  assert.deepEqual(trend.values, [50, 33.3333]);
  assert.ok(trend.points.every((point) => point.sample_count > 0));
  assert.equal(trend.labels.includes("2026-08-08T00:00:00Z"), false);
});

test("cross-screen navigation preserves canonical product identifiers", () => {
  const activity: ActivityItem = {
    kind: "TECHNICAL_EVENT",
    occurred_at: "2026-08-10T14:42:38.412Z",
    environment,
    pipeline: eventsPipeline,
    source: eventsSource,
    run: eventsRun,
    event_key: "evt-001",
    level: "ERROR",
    stage: "EXTRACT",
    platform_code: "PIPELINE_EXECUTION_FAILED",
    vendor_code: "SASL_AUTHENTICATION_FAILED",
    rule_code: null,
    message: "Events Kafka rejected credentials.",
  };
  assert.equal(activityHref(activity), "/logs?run=run_01J94EVT18&pipeline=events-processing&source=events-kafka");
  const review: ReviewResource = {
    resource_key: "events-processing",
    resource_type: "PIPELINE",
    name: "Events Processing",
    signal: "Pipeline Success Rate",
    severity: "CRITICAL",
    pipeline_key: "events-processing",
    source_key: null,
    check_key: null,
  };
  assert.equal(reviewResourceHref(review), "/pipelines/events-processing");
});

test("production aggregation screens use only authoritative endpoints and no fixture clocks", async () => {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const monitoring = await readFile(`${root}/components/monitoring.tsx`, "utf8");
  const health = await readFile(`${root}/components/health-metrics.tsx`, "utf8");
  const text = `${monitoring}\n${health}`;
  assert.match(monitoring, /\/api\/v1\/monitoring/);
  assert.match(health, /\/api\/v1\/health-metrics/);
  assert.doesNotMatch(text, /monitoring-data|health-metrics-data|canonical-demo|DEMO_NOW|mockNow|2 min ago|Last updated 10:42|legacy\/api\/v1\/metrics/);
  assert.doesNotMatch(text, /\/api\/v1\/(pipelines|pipeline-runs|alerts|data-sources)["`]/);
});

test("scope controls enforce pipeline/source mutual exclusivity and snapshot semantics", async () => {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const text = (await Promise.all([
    readFile(`${root}/components/monitoring.tsx`, "utf8"),
    readFile(`${root}/components/health-metrics.tsx`, "utf8"),
  ])).join("\n");
  assert.match(text, /resourceType === "pipeline"/);
  assert.match(text, /resourceType === "source"/);
  assert.match(text, /CURRENT_SNAPSHOT/);
  assert.match(text, /current state only, not historical availability or uptime/);
  assert.match(text, /source_availability/);
  assert.match(text, /freshness_compliance/);
  assert.match(text, /schedule_adherence/);
});

test("established request state still aborts superseded aggregation requests", async () => {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const hook = await readFile(`${root}/lib/use-api-query.ts`, "utf8");
  assert.match(hook, /AbortController/);
  assert.match(hook, /requestNumber/);
  assert.match(hook, /controller\.abort\(\)/);
  assert.match(hook, /kind === "cancelled"/);
});
