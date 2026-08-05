"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo } from "react";

import { RunKindBadge } from "@/components/ui/Badge";
import { useRuns } from "@/lib/hooks";

/** URL-synced run selector. Writes the chosen run id to `?run=`. */
export function RunPicker({ selected }: { selected: string | null }) {
  const { data } = useRuns();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const runs = useMemo(() => data?.items ?? [], [data]);

  // Default to the newest run when none is selected.
  useEffect(() => {
    if (!selected && runs.length > 0) {
      const sp = new URLSearchParams(params.toString());
      sp.set("run", runs[0].run_id);
      router.replace(`${pathname}?${sp.toString()}`);
    }
  }, [selected, runs, params, pathname, router]);

  const current = runs.find((r) => r.run_id === selected) ?? null;

  function onChange(runId: string) {
    const sp = new URLSearchParams(params.toString());
    sp.set("run", runId);
    router.replace(`${pathname}?${sp.toString()}`);
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <label htmlFor="run-select" className="text-sm text-muted">
        Run
      </label>
      <select
        id="run-select"
        value={selected ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-[22rem] rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
      >
        {runs.length === 0 && <option value="">No runs available</option>}
        {runs.map((r) => (
          <option key={r.run_id} value={r.run_id}>
            {r.run_id} · {r.family} · {r.symbol} {r.timeframe}
          </option>
        ))}
      </select>
      {current && <RunKindBadge kind={current.kind} />}
    </div>
  );
}

export function useSelectedRun(): string | null {
  const params = useSearchParams();
  return params.get("run");
}
