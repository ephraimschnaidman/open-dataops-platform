import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { mapSettingsResponse, notificationApiPayload, operationalDefaultsApiPayload, validateOperationalDefaults, type SettingsApiResponse } from "../lib/settings-data.ts";

const response: SettingsApiResponse = {
  general: { workspace_name: "Corvetra", workspace_id: "workspace_01J4X8K97B", default_environment: "qa", timezone: "America/New_York", date_time_display: "LOCAL_WORKSPACE_TIME" },
  environments: [{ environment_key: "qa", name: "QA", description: null, status: "ACTIVE", resources: 0, pipelines: 0, sources: 0, other: 0, created_at: "2026-08-11", is_default: true }],
  notifications: { enabled: true, recipients: ["ops@example.com", "owner@example.com"], severity: "CRITICAL_AND_WARNING", notify_resolved: true },
  operational_defaults: { pipeline: { healthy: 98, warning: 95 }, schedule: { healthy: 99, warning: 95 }, source: { healthy: 99.5, warning: 98 }, runtime_warning: 35, freshness_hours: 2, validation_severity: "WARNING", blocking_alerts: true, warning_alerts: false },
};

test("persisted settings response hydrates notification recipients and operational defaults after reload", () => {
  const mapped = mapSettingsResponse(response);
  assert.equal(mapped.notifications.recipients, "ops@example.com\nowner@example.com");
  assert.equal(mapped.operationalDefaults.runtimeWarning, "35");
  assert.equal(mapped.general.defaultEnvironment, "qa");
  assert.equal(mapped.environments[0].isDefault, true);
});

test("frontend rejects percentages over 100 and invalid runtime/freshness values", () => {
  const defaults = mapSettingsResponse(response).operationalDefaults;
  assert.deepEqual(validateOperationalDefaults(defaults), {});
  assert.match(validateOperationalDefaults({ ...defaults, pipeline: { ...defaults.pipeline, healthy: "101" } }).pipeline?.healthy ?? "", /between 0 and 100/);
  assert.match(validateOperationalDefaults({ ...defaults, runtimeWarning: "101" }).runtimeWarning ?? "", /between 0 and 100/);
  assert.ok(validateOperationalDefaults({ ...defaults, freshnessHours: "0" }).freshnessHours);
});

test("API payload adapters preserve values sent through the BFF", () => {
  const mapped = mapSettingsResponse(response);
  assert.deepEqual(notificationApiPayload(mapped.notifications).recipients, ["ops@example.com", "owner@example.com"]);
  assert.equal(operationalDefaultsApiPayload(mapped.operationalDefaults).runtime_warning, 35);
});

test("Settings UI uses persisted mutations, blocks default deletion, and clears resolved errors", async () => {
  const root = fileURLToPath(new URL("..", import.meta.url));
  const component = await readFile(`${root}/components/settings.tsx`, "utf8");
  const bff = await readFile(`${root}/app/api/v1/[...path]/route.ts`, "utf8");
  assert.match(component, /useApiQuery<SettingsApiResponse>.*\/api\/v1\/settings/);
  assert.match(component, /disabled=\{environment\.isDefault\}/);
  assert.match(component, /DEFAULT_ENVIRONMENT_REQUIRED/);
  assert.match(component, /setSectionError\(null\)[\s\S]*showToast\("Notifications saved"\)/);
  assert.match(component, /setSectionError\(null\)[\s\S]*showToast\("Default environment updated"\)/);
  assert.match(component, /setSectionError\(null\)[\s\S]*showToast\("User role updated"\)/);
  assert.match(bff, /proxyBackendMutation/);
  assert.match(bff, /path\[0\] !== "settings"/);
});
