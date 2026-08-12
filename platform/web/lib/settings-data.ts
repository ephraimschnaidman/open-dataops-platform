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

export const settingsSections: Array<{ id: SettingsSectionId; label: string; description: string }> = [
    { id: "general", label: "General", description: "Workspace identity and basic preferences." },
    { id: "environments", label: "Environments", description: "Operational separation within this Datum workspace." },
    { id: "users", label: "Users & Access", description: "Workspace users and their access roles." },
    { id: "notifications", label: "Notifications", description: "Destinations for operational alert notifications." },
    { id: "operational-defaults", label: "Operational Defaults", description: "Workspace-wide health and validation defaults." },
];

export const initialGeneralSettings: GeneralSettings = { workspaceName: "Datum Demo Workspace", workspaceId: "workspace_01J4X8K97B", defaultEnvironment: "production", timezone: "America/New_York", dateTimeDisplay: "Local workspace time" };

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
