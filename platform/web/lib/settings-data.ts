export type SettingsSectionId = "general" | "environments" | "users" | "notifications" | "operational-defaults";
export type UserRole = "Admin" | "Operator" | "Viewer";
export type SettingsQaState = "normal" | "unsaved" | "save-success" | "save-failure" | "single-environment" | "add-environment" | "environment-in-use" | "invite-user" | "role-change" | "last-admin" | "notifications-configured" | "notifications-unconfigured" | "notification-test-success" | "notification-test-failure" | "invalid-threshold" | "error" | "partial" | "stale" | "narrow";

export interface EnvironmentSetting {
    id: string; name: string; status: "Active"; resources: number; pipelines: number; sources: number; other: number; created: string; description?: string; isDefault: boolean;
}

export interface WorkspaceUser {
    id: string; name: string; email: string; role: UserRole; status: "Active" | "Invited"; lastActive: string;
}

export interface GeneralSettings {
    workspaceName: string; workspaceId: string; defaultEnvironment: string; timezone: string; dateTimeDisplay: "Local workspace time";
}

export interface NotificationSettings {
    enabled: boolean; recipients: string; severity: "Critical only" | "Critical + Warning"; notifyResolved: boolean;
}

export interface ThresholdSetting { healthy: string; warning: string; }

export interface OperationalDefaults {
    pipeline: ThresholdSetting; schedule: ThresholdSetting; source: ThresholdSetting; runtimeWarning: string; freshnessHours: string;
    validationSeverity: "Warning" | "Blocking"; blockingAlerts: boolean; warningAlerts: boolean;
}

export interface SettingsApiResponse {
    general: { workspace_name: string; workspace_id: string; default_environment: string; timezone: string; date_time_display: "LOCAL_WORKSPACE_TIME" };
    environments: Array<{ environment_key: string; name: string; description: string | null; status: "ACTIVE"; resources: number; pipelines: number; sources: number; other: number; created_at: string; is_default: boolean }>;
    notifications: { enabled: boolean; recipients: string[]; severity: "CRITICAL_ONLY" | "CRITICAL_AND_WARNING"; notify_resolved: boolean };
    operational_defaults: { pipeline: { healthy: number | string; warning: number | string }; schedule: { healthy: number | string; warning: number | string }; source: { healthy: number | string; warning: number | string }; runtime_warning: number | string; freshness_hours: number | string; validation_severity: "WARNING" | "BLOCKING"; blocking_alerts: boolean; warning_alerts: boolean };
}

export function mapSettingsResponse(response: SettingsApiResponse) {
    const general: GeneralSettings = { workspaceName: response.general.workspace_name, workspaceId: response.general.workspace_id, defaultEnvironment: response.general.default_environment, timezone: response.general.timezone, dateTimeDisplay: "Local workspace time" };
    const environments: EnvironmentSetting[] = response.environments.map((item) => ({ id: item.environment_key, name: item.name, description: item.description ?? undefined, status: "Active", resources: item.resources, pipelines: item.pipelines, sources: item.sources, other: item.other, created: new Date(`${item.created_at}T00:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", year: "numeric", month: "long", day: "numeric" }), isDefault: item.is_default }));
    const notifications: NotificationSettings = { enabled: response.notifications.enabled, recipients: response.notifications.recipients.join("\n"), severity: response.notifications.severity === "CRITICAL_ONLY" ? "Critical only" : "Critical + Warning", notifyResolved: response.notifications.notify_resolved };
    const value = response.operational_defaults;
    const operationalDefaults: OperationalDefaults = { pipeline: { healthy: String(value.pipeline.healthy), warning: String(value.pipeline.warning) }, schedule: { healthy: String(value.schedule.healthy), warning: String(value.schedule.warning) }, source: { healthy: String(value.source.healthy), warning: String(value.source.warning) }, runtimeWarning: String(value.runtime_warning), freshnessHours: String(value.freshness_hours), validationSeverity: value.validation_severity === "BLOCKING" ? "Blocking" : "Warning", blockingAlerts: value.blocking_alerts, warningAlerts: value.warning_alerts };
    return { general, environments, notifications, operationalDefaults };
}

export function notificationApiPayload(settings: NotificationSettings) {
    return { enabled: settings.enabled, recipients: settings.recipients.split(/\r?\n/).map((item) => item.trim()).filter(Boolean), severity: settings.severity === "Critical only" ? "CRITICAL_ONLY" : "CRITICAL_AND_WARNING", notify_resolved: settings.notifyResolved };
}

export function operationalDefaultsApiPayload(settings: OperationalDefaults) {
    const threshold = (value: ThresholdSetting) => ({ healthy: Number(value.healthy), warning: Number(value.warning) });
    return { pipeline: threshold(settings.pipeline), schedule: threshold(settings.schedule), source: threshold(settings.source), runtime_warning: Number(settings.runtimeWarning), freshness_hours: Number(settings.freshnessHours), validation_severity: settings.validationSeverity === "Blocking" ? "BLOCKING" : "WARNING", blocking_alerts: settings.blockingAlerts, warning_alerts: settings.warningAlerts };
}

export type OperationalDefaultErrors = Partial<Record<"pipeline" | "schedule" | "source", { healthy?: string; warning?: string }>> & { runtimeWarning?: string; freshnessHours?: string };

export function validateOperationalDefaults(settings: OperationalDefaults): OperationalDefaultErrors {
    const result: OperationalDefaultErrors = {};
    (["pipeline", "schedule", "source"] as const).forEach((key) => {
        const healthy = Number(settings[key].healthy); const warning = Number(settings[key].warning);
        if (!settings[key].healthy || !Number.isFinite(healthy) || healthy < 0 || healthy > 100) result[key] = { healthy: "Healthy threshold must be between 0 and 100%." };
        else if (healthy <= warning) result[key] = { healthy: "Healthy threshold must be higher than the Warning threshold." };
        if (!settings[key].warning || !Number.isFinite(warning) || warning < 0 || warning > 100) result[key] = { ...result[key], warning: "Warning threshold must be between 0 and 100%." };
    });
    const runtime = Number(settings.runtimeWarning);
    if (!settings.runtimeWarning || !Number.isFinite(runtime) || runtime < 0 || runtime > 100) result.runtimeWarning = "Runtime warning threshold must be between 0 and 100%.";
    const freshness = Number(settings.freshnessHours);
    if (!settings.freshnessHours || !Number.isFinite(freshness) || freshness <= 0 || freshness > 8760) result.freshnessHours = "Freshness window must be greater than 0 and no more than 8760 hours.";
    return result;
}

export const settingsSections: Array<{ id: SettingsSectionId; label: string; description: string }> = [
    { id: "general", label: "General", description: "Workspace identity and basic preferences." },
    { id: "environments", label: "Environments", description: "Operational separation within this Corvetra workspace." },
    { id: "users", label: "Users & Access", description: "Workspace users and their access roles." },
    { id: "notifications", label: "Notifications", description: "Destinations for operational alert notifications." },
    { id: "operational-defaults", label: "Operational Defaults", description: "Workspace-wide health and validation defaults." },
];

export const initialGeneralSettings: GeneralSettings = { workspaceName: "Corvetra Demo Workspace", workspaceId: "workspace_01J4X8K97B", defaultEnvironment: "production", timezone: "America/New_York", dateTimeDisplay: "Local workspace time" };

export const initialEnvironments: EnvironmentSetting[] = [
    { id: "production", name: "Production", status: "Active", resources: 18, pipelines: 8, sources: 5, other: 5, created: "January 12, 2025", isDefault: true },
    { id: "staging", name: "Staging", status: "Active", resources: 7, pipelines: 3, sources: 2, other: 2, created: "January 12, 2025", isDefault: false },
    { id: "development", name: "Development", status: "Active", resources: 4, pipelines: 2, sources: 1, other: 1, created: "February 3, 2025", isDefault: false },
];

export const initialUsers: WorkspaceUser[] = [
    { id: "sidney-weiser", name: "Sidney Weiser", email: "sidney@example.com", role: "Admin", status: "Active", lastActive: "Today" },
    { id: "alex-chen", name: "Alex Chen", email: "alex@example.com", role: "Operator", status: "Active", lastActive: "2 hr ago" },
    { id: "jamie-lee", name: "Jamie Lee", email: "jamie@example.com", role: "Viewer", status: "Invited", lastActive: "—" },
];

export const initialNotifications: NotificationSettings = { enabled: true, recipients: "ops@example.com\nengineering@example.com", severity: "Critical + Warning", notifyResolved: true };

export const initialOperationalDefaults: OperationalDefaults = {
    pipeline: { healthy: "98", warning: "95" }, schedule: { healthy: "99", warning: "95" }, source: { healthy: "99.5", warning: "98" },
    runtimeWarning: "30", freshnessHours: "2", validationSeverity: "Warning", blockingAlerts: true, warningAlerts: false,
};

export const roleDefinitions = [
    { role: "Admin" as const, description: "Can configure Settings and manage users." },
    { role: "Operator" as const, description: "Can operate pipelines, runs, alerts, validation, and sources. Cannot manage workspace-wide access settings." },
    { role: "Viewer" as const, description: "Read-only operational access." },
];
