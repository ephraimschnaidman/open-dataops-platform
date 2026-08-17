import type { DashboardSummary, PipelineRunListItem } from "@/lib/api-contract";

export interface DashboardSummaryItem {
  label: string;
  value: string;
  detail: string;
}

export function presentDashboardSummary(summary: DashboardSummary): DashboardSummaryItem[] {
  return [
    { label: "Configured Pipelines", value: String(summary.configured_pipelines), detail: `${summary.enabled_pipelines} enabled` },
    { label: "Successful Runs", value: String(summary.successful_runs), detail: "Inside the Dashboard period" },
    { label: "Failed Runs", value: String(summary.failed_runs), detail: "Inside the Dashboard period" },
    { label: "Active Alerts", value: String(summary.active_alerts.total), detail: `${summary.active_alerts.critical} critical · ${summary.active_alerts.warning} warning` },
    { label: "Sources", value: String(summary.sources), detail: `${summary.non_disabled_sources} non-disabled` },
  ];
}

export function latestRunHref(run: PipelineRunListItem): string {
  return `/pipeline-runs/${run.corvetra_run_id}`;
}
