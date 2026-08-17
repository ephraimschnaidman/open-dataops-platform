"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, Boxes, Database, Network, Plus, Search } from "lucide-react";
import type { DataSourceListResponse } from "@/lib/api-contract";
import { mapDataSource, environmentApiValue, enumApiValue } from "@/lib/core-resource-adapters";
import { useApiQuery } from "@/lib/use-api-query";
import { useEnvironmentContext } from "@/lib/environment-context";
import { Button, EmptyState, ErrorState, FilterSelect, MetricCard, PageHeader, SearchField, Skeleton, StatusBadge } from "@/components/ui";

const LIMIT = 20;

export function DataSourcesPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { currentEnvironment } = useEnvironmentContext();
    const [query, setQuery] = useState(searchParams.get("q") ?? "");
    const [status, setStatus] = useState(searchParams.get("status") ?? "All");
    const [sourceType, setSourceType] = useState(searchParams.get("type") ?? "All");
    const [environment, setEnvironment] = useState(searchParams.get("environment") ?? currentEnvironment);
    const [offset, setOffset] = useState(0);
    useEffect(() => setOffset(0), [query, status, sourceType, environment]);
    const request = useApiQuery<DataSourceListResponse>("/api/v1/data-sources", { limit: LIMIT, offset, environment: environmentApiValue(environment), operational_status: enumApiValue(status), source_type: enumApiValue(sourceType), search: query.trim() || undefined }, 250);
    const sources = useMemo(() => request.data?.items.map(mapDataSource) ?? [], [request.data]);
    const total = request.data?.pagination.total ?? 0;
    const hasFilters = Boolean(query || status !== "All" || sourceType !== "All" || environment !== "All");
    const clearFilters = () => { setQuery(""); setStatus("All"); setSourceType("All"); setEnvironment(currentEnvironment); };
    if (request.loading && !request.data) return <DataSourcesSkeleton />;
    return <div className="animate-enter">
        <PageHeader title="Data Sources" description="Manage systems that provide data to your pipelines." eyebrow={<><Network className="h-3 w-3" /> {environment === "All" ? "All environments" : environment} workspace</>} action={<Button variant="primary" disabled title="Adding data sources is not available in this MVP"><Plus className="h-3.5 w-3.5" /> Add Data Source</Button>} />
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Connected sources" value={String(total)} detail="Matching the current scope" icon={Database} /><MetricCard label="Healthy" value={String(sources.filter((source) => source.status === "Healthy").length)} detail="On this page" icon={Network} tone="positive" /><MetricCard label="Needs attention" value={String(sources.filter((source) => source.status === "Warning" || source.status === "Disconnected").length)} detail="On this page" icon={AlertTriangle} tone="warning" /><MetricCard label="Dependent pipelines" value={String(sources.reduce((sum, source) => sum + source.pipelines, 0))} detail="On this page" icon={Boxes} /></div>
        <section className="mt-7"><div className="mb-3 flex flex-col gap-2 xl:flex-row xl:items-center"><SearchField value={query} onChange={setQuery} placeholder="Search by name or type..." className="xl:max-w-xs" /><FilterSelect label="Filter by status" value={status} onChange={setStatus} options={["All","Healthy","Warning","Disconnected","Disabled"].map((value) => ({ label: value === "All" ? "All statuses" : value, value }))} /><FilterSelect label="Filter by type" value={sourceType} onChange={setSourceType} options={["All","Kafka","Postgresql","Snowflake","Sql Server"].map((value) => ({ label: value === "All" ? "All source types" : value.replace("Postgresql","PostgreSQL").replace("Sql Server","SQL Server"), value }))} /><FilterSelect label="Filter by environment" value={environment} onChange={setEnvironment} options={["All","Production","Staging","Development"].map((value) => ({ label: value === "All" ? "All environments" : value, value }))} /><span className="text-[11px] text-zinc-400 xl:ml-auto">{total} {total === 1 ? "source" : "sources"}</span></div>
            {request.error ? <ErrorState title={request.error.kind === "permission" ? "Permission denied" : "Unable to load data sources"} description={request.error.message} actionLabel={request.error.retryable ? "Try Again" : undefined} onRetry={request.error.retryable ? request.retry : undefined} technicalDetails={[{ label: "Platform Code", value: request.error.code }, ...(request.error.status ? [{ label: "HTTP Status", value: String(request.error.status) }] : [])]} /> : !sources.length ? <EmptyState title={hasFilters ? "No sources match your criteria" : "No data sources connected"} description={hasFilters ? "Try another search or clear the current filters." : "No canonical data sources are available."} icon={hasFilters ? <Search className="h-4 w-4" /> : <Database className="h-4 w-4" />} action={hasFilters ? <Button onClick={clearFilters}>Clear filters</Button> : undefined} /> : <><div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white shadow-card"><table className="w-full min-w-[850px] text-left"><thead><tr className="border-b border-zinc-200 bg-zinc-50/70 text-[10px] font-semibold uppercase tracking-wider text-zinc-400"><th className="px-4 py-2.5">Source</th><th className="px-3 py-2.5">Type</th><th className="px-3 py-2.5">Status</th><th className="px-3 py-2.5 text-right">Pipelines</th><th className="px-3 py-2.5">Last observed</th><th className="px-3 py-2.5">Environment</th></tr></thead><tbody>{sources.map((source) => <tr key={source.id} tabIndex={0} onClick={() => router.push(`/data-sources/${source.id}`)} onKeyDown={(event) => { if (event.key === "Enter") router.push(`/data-sources/${source.id}`); }} className="cursor-pointer border-b border-zinc-100 text-xs last:border-0 hover:bg-zinc-50"><td className="px-4 py-3"><span className="font-mono font-medium text-zinc-800">{source.name}</span><span className="mt-0.5 block font-mono text-[10px] text-zinc-400">{source.id}</span></td><td className="px-3 py-3 text-zinc-600">{source.type}</td><td className="px-3 py-3"><StatusBadge status={source.status} /></td><td className="px-3 py-3 text-right tabular-nums">{source.pipelines}</td><td className="px-3 py-3 text-zinc-500">{source.lastCheck}</td><td className="px-3 py-3 text-zinc-600">{source.environment}</td></tr>)}</tbody></table></div><div className="mt-3 flex items-center justify-between text-xs text-zinc-500"><span>{request.data?.pagination.returned_count ?? 0} shown · {total} total</span><div className="flex gap-2"><Button disabled={offset === 0 || request.loading} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>Previous</Button><Button disabled={offset + (request.data?.pagination.returned_count ?? 0) >= total || request.loading} onClick={() => setOffset(offset + LIMIT)}>Next</Button></div></div></>}
        </section>
    </div>;
}

export function DataSourcesSkeleton() { return <div className="space-y-7"><Skeleton className="h-16" /><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({length:4}).map((_,i)=><Skeleton key={i} className="h-28" />)}</div><Skeleton className="h-80" /></div>; }
