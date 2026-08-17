"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Activity, FileText } from "lucide-react";

import { mapValidation, NOT_AVAILABLE } from "@/lib/core-resource-adapters";
import type { ValidationExecutionDetail } from "@/lib/api-contract";
import { useApiQuery } from "@/lib/use-api-query";
import {
  Breadcrumbs,
  Button,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
  StatusBadge,
  TechnicalDetails,
} from "@/components/ui";

export function ValidationDetailSkeleton() {
  return (
    <div className="space-y-7">
      <Skeleton className="h-20" />
      <div className="grid gap-7 xl:grid-cols-2">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}

export function ValidationDetailPage({ checkKey }: { checkKey: string }) {
  const params = useSearchParams();
  const runId = params.get("run");
  const request = useApiQuery<ValidationExecutionDetail>(
    runId
      ? `/api/v1/validation/${encodeURIComponent(checkKey)}/runs/${encodeURIComponent(runId)}`
      : null,
  );

  if (!runId) {
    return (
      <ErrorState
        title="Validation execution identity required"
        description="A validation detail link must include its canonical run ID."
        technicalDetails={[{ label: "Platform Code", value: "VALIDATION_RUN_REQUIRED" }]}
      />
    );
  }

  if (request.loading && !request.data) return <ValidationDetailSkeleton />;

  if (request.error) {
    const title =
      request.error.kind === "not_found"
        ? "Validation execution not found"
        : request.error.kind === "permission"
          ? "Permission denied"
          : "Validation execution couldn't be loaded";

    return (
      <>
        <Breadcrumbs items={[{ label: "Validation", href: "/validation" }, { label: checkKey }]} />
        <ErrorState
          title={title}
          description={request.error.message}
          actionLabel={request.error.retryable ? "Try Again" : undefined}
          onRetry={request.error.retryable ? request.retry : undefined}
          technicalDetails={[{ label: "Platform Code", value: request.error.code }]}
        />
      </>
    );
  }

  if (!request.data) return null;

  const item = mapValidation(request.data);

  return (
    <div className="animate-enter">
      <Breadcrumbs items={[{ label: "Validation", href: "/validation" }, { label: item.name }]} />
      <PageHeader
        title={item.name}
        description={item.message}
        eyebrow={
          <>
            Check definition: <span className="font-mono">{item.checkKey}</span> · Execution:{" "}
            <span className="font-mono">{item.runId}</span>
            <StatusBadge status={item.result} />
            <StatusBadge status={item.severity} />
          </>
        }
        action={
          <div className="flex flex-wrap gap-2">
            <Link href={`/pipeline-runs/${item.runId}`}><Button>View Run</Button></Link>
            <Link href={`/pipelines/${item.pipelineId}`}><Button>View Pipeline</Button></Link>
            <Link href={`/data-sources/${item.sourceId}`}><Button>View Source</Button></Link>
            <Link href={`/logs?check=${encodeURIComponent(item.checkKey)}&run=${encodeURIComponent(item.runId)}`}>
              <Button><FileText className="h-3.5 w-3.5" /> View Evidence</Button>
            </Link>
          </div>
        }
      />

      <div className="grid gap-7 xl:grid-cols-2">
        <Card title="Check Definition" description="Stable validation-check identity and configured semantics.">
          <div className="p-4">
            <TechnicalDetails items={[
              { label: "Check key", value: item.checkKey },
              { label: "Name", value: item.name },
              { label: "Check type", value: item.checkType },
              { label: "Dataset", value: item.datasetName },
              { label: "Column", value: item.columnName },
              { label: "Severity", value: item.severity },
            ]} />
          </div>
        </Card>
        <Card title="Execution Result" description="Result for the canonical pipeline run.">
          <div className="p-4">
            <TechnicalDetails items={[
              { label: "Run ID", value: item.runId },
              { label: "Result", value: item.result },
              { label: "Stage", value: item.stage },
              { label: "Evaluated", value: item.evaluatedAt },
              { label: "Actual", value: item.actual },
              { label: "Expected", value: item.expected },
            ]} />
          </div>
        </Card>
      </div>

      <div className="mt-7 grid gap-7 xl:grid-cols-2">
        <Card title="Technical Semantics" description="Backend codes remain separate.">
          <div className="p-4">
            <TechnicalDetails items={[
              { label: "Platform Code", value: item.platformCode },
              { label: "Vendor Code", value: item.vendorCode ?? NOT_AVAILABLE },
              { label: "Rule Code", value: item.ruleCode ?? NOT_AVAILABLE },
              { label: "Environment", value: item.environment },
            ]} />
          </div>
        </Card>
        <Card title="Related Alerts" description="Alerts associated with this validation execution.">
          {request.data.related_alerts.length ? (
            <div className="space-y-3 p-4">
              {request.data.related_alerts.map((alert) => (
                <Link
                  key={alert.alert_key}
                  href={`/alerts/${alert.alert_key}`}
                  className="block rounded border p-3 text-xs hover:bg-zinc-50"
                >
                  <div className="flex justify-between">
                    <strong>{alert.title}</strong>
                    <StatusBadge status={alert.status} />
                  </div>
                  <p className="mt-2 font-mono text-[10px]">
                    {alert.alert_key} · {alert.platform_code}
                    {alert.rule_code
                      ? ` · Rule: ${alert.rule_code}`
                      : alert.vendor_code
                        ? ` · Vendor: ${alert.vendor_code}`
                        : ""}
                  </p>
                </Link>
              ))}
            </div>
          ) : (
            <div className="p-4">
              <EmptyState title="No related alerts" description="No alerts were returned for this execution." icon={<Activity className="h-4 w-4" />} />
            </div>
          )}
        </Card>
      </div>

      <div className="mt-7">
        <Card title="Technical Evidence" description={`${request.data.technical_evidence_count} related events.`}>
          {request.data.technical_evidence.length ? (
            <ol className="space-y-4 p-4">
              {request.data.technical_evidence.map((event) => (
                <li key={event.event_key} className="border-l-2 pl-4 text-xs">
                  <p className="font-medium">{event.message}</p>
                  <p className="mt-1 font-mono text-[10px]">
                    {event.platform_code}
                    {event.vendor_code ? ` · Vendor: ${event.vendor_code}` : ""}
                    {event.rule_code ? ` · Rule: ${event.rule_code}` : ""}
                  </p>
                </li>
              ))}
            </ol>
          ) : (
            <div className="p-4">
              <EmptyState title="No technical evidence" description="No evidence was returned." icon={<Activity className="h-4 w-4" />} />
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
