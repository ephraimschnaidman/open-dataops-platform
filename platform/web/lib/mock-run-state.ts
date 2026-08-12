import type { PipelineRun, PipelineRunStatus } from "@/lib/pipeline-runs-data";

const statusKey = "datum-run-status-overrides";
const retryKey = "datum-conceptual-retry-runs";

export function readRunStatusOverrides(): Record<string, PipelineRunStatus> {
    try { return JSON.parse(window.sessionStorage.getItem(statusKey) ?? "{}"); } catch { return {}; }
}

export function persistRunStatus(runId: string, status: PipelineRunStatus) {
    window.sessionStorage.setItem(statusKey, JSON.stringify({ ...readRunStatusOverrides(), [runId]: status }));
}

export function readConceptualRetries(): PipelineRun[] {
    try { return JSON.parse(window.sessionStorage.getItem(retryKey) ?? "[]"); } catch { return []; }
}

export function persistConceptualRetry(run: PipelineRun) {
    const existing = readConceptualRetries().filter((item) => item.id !== run.id);
    window.sessionStorage.setItem(retryKey, JSON.stringify([run, ...existing]));
}

export function conceptualRetryId(originalRunId: string) {
    return `${originalRunId}_R${Date.now().toString(36).toUpperCase()}`;
}

export function createConceptualManualRun(pipelineId: string, pipelineName: string): PipelineRun {
    return {
        id: `run_MANUAL_${Date.now().toString(36).toUpperCase()}`,
        pipelineId,
        pipelineName,
        status: "Running",
        stage: "Extract",
        trigger: "Manual",
        startedAt: new Date().toISOString(),
        platformCode: "PIPELINE_RUNNING",
        message: "The manual execution is currently running.",
        recommendedAction: "No action is required while execution continues.",
    };
}
