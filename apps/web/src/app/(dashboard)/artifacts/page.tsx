"use client";

import { Suspense } from "react";

import { PageShell } from "@/components/layout/PageShell";
import { RunPicker, useSelectedRun } from "@/components/RunPicker";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState, ErrorState, PartialNotice, Skeleton } from "@/components/ui/States";
import { useArtifacts } from "@/lib/hooks";

function JsonBlock({ value }: { value: unknown }) {
  if (value == null) return <PartialNotice>Artifact missing or unreadable.</PartialNotice>;
  return (
    <pre className="max-h-80 overflow-auto rounded-md border border-border bg-surface-2 p-3 text-xs">
      <code>{JSON.stringify(value, null, 2)}</code>
    </pre>
  );
}

function ArtifactsInner() {
  const runId = useSelectedRun();
  const { data, error, isLoading } = useArtifacts(runId);

  const failedTotal = data
    ? Object.values(data.failed_candidates).reduce((a, arr) => a + arr.length, 0)
    : 0;

  return (
    <div className="space-y-6">
      <RunPicker selected={runId} />

      {!runId ? (
        <EmptyState title="Select a run" />
      ) : isLoading ? (
        <Skeleton className="h-72" />
      ) : error ? (
        <ErrorState title="No artifacts" detail={error.message} />
      ) : !data ? (
        <EmptyState title="No artifact bundle" />
      ) : (
        <>
          {data.warnings.length > 0 && (
            <Card>
              <CardHeader title="Warnings" />
              <ul className="list-inside list-disc space-y-1 text-sm text-warn">
                {data.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </Card>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader title="Dataset manifests" subtitle="Provenance & content hashes" />
              <JsonBlock value={data.dataset_manifests} />
            </Card>
            <Card>
              <CardHeader title="Feature manifest" />
              <JsonBlock value={data.feature_manifest} />
            </Card>
            <Card>
              <CardHeader title="Search space" />
              <JsonBlock value={data.search_space} />
            </Card>
            <Card>
              <CardHeader title="Objective definition" />
              <JsonBlock value={data.objective} />
            </Card>
            <Card>
              <CardHeader title="Environment" />
              <JsonBlock value={data.environment} />
            </Card>
            <Card>
              <CardHeader title="Git state" />
              <JsonBlock value={data.git_state} />
            </Card>
          </div>

          <Card>
            <CardHeader
              title="Failed candidates"
              right={<Badge tone={failedTotal ? "warn" : "positive"}>{failedTotal} failed</Badge>}
            />
            {failedTotal === 0 ? (
              <EmptyState title="No failed candidates recorded" />
            ) : (
              <JsonBlock value={data.failed_candidates} />
            )}
          </Card>

          <Card>
            <CardHeader
              title="Artifact files"
              subtitle={`${data.files.length} files in this run directory`}
            />
            <div className="flex flex-wrap gap-2">
              {data.files.map((f) => (
                <span
                  key={f}
                  className="rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-xs text-muted"
                >
                  {f}
                </span>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

export default function ArtifactsPage() {
  return (
    <PageShell title="Artifact Inspector">
      <Suspense fallback={<Skeleton className="h-72" />}>
        <ArtifactsInner />
      </Suspense>
    </PageShell>
  );
}
