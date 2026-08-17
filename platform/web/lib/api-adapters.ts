import type { AggregationMetric, MetricAvailability, PaginationMetadata } from "./api-contract.ts";

export interface PaginationView {
    firstItem: number;
    lastItem: number;
    total: number;
    hasPrevious: boolean;
    hasNext: boolean;
}

export function enumDisplayLabel(value: string): string {
    return value.toLowerCase().split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

export function statusDisplayLabel(value: string): string {
    return enumDisplayLabel(value);
}

export function formatTimestamp(value: string | null | undefined, locale = "en-US"): string {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function formatDuration(seconds: number | null | undefined): string {
    if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return "—";
    const rounded = Math.round(seconds);
    const hours = Math.floor(rounded / 3600);
    const minutes = Math.floor((rounded % 3600) / 60);
    const remainingSeconds = rounded % 60;
    return [hours && `${hours}h`, (hours || minutes) && `${minutes}m`, `${remainingSeconds}s`].filter(Boolean).join(" ");
}

export function mapPagination(pagination: PaginationMetadata): PaginationView {
    const firstItem = pagination.returned_count ? pagination.offset + 1 : 0;
    return {
        firstItem,
        lastItem: pagination.offset + pagination.returned_count,
        total: pagination.total,
        hasPrevious: pagination.offset > 0,
        hasNext: pagination.offset + pagination.returned_count < pagination.total,
    };
}

export function isMetricAvailable(availability: MetricAvailability): availability is "AVAILABLE" {
    return availability === "AVAILABLE";
}

export function metricValue(metric: AggregationMetric): number | null {
    return isMetricAvailable(metric.availability) ? metric.value : null;
}

export function preserveCanonicalId<T extends string>(id: T): T {
    return id;
}
