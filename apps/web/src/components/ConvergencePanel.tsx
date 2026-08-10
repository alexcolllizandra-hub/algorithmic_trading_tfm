"use client";

import { useState } from "react";

import { ConvergenceChart } from "@/components/charts/ConvergenceChart";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/States";
import type { ConvergencePoint } from "@/lib/api-types";

/**
 * Convergence for one outer fold at a time.
 *
 * Search runs independently inside every outer fold (ADR 0012), so each fold has
 * its own trace measured on its own validation window. Overlaying them would
 * suggest a single search that never happened.
 */
export function ConvergencePanel({
  series,
  folds,
  title,
  subtitle,
  emptyTitle,
  foldLabel,
}: {
  series: Record<string, ConvergencePoint[]>;
  folds: number[];
  title: string;
  subtitle: string;
  emptyTitle: string;
  foldLabel: string;
}) {
  const available = folds.length > 0 ? folds : [0];
  const [fold, setFold] = useState(available[0]);
  const isEmpty = Object.keys(series).length === 0;

  return (
    <Card>
      <CardHeader
        title={title}
        subtitle={subtitle}
        right={
          isEmpty ? undefined : (
            <label className="flex items-center gap-2 text-xs text-muted">
              {foldLabel}
              <select
                value={fold}
                onChange={(e) => setFold(Number(e.target.value))}
                className="rounded-md border border-border bg-surface px-2 py-1 text-xs"
              >
                {available.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </label>
          )
        }
      />
      {isEmpty ? (
        <EmptyState title={emptyTitle} />
      ) : (
        <ConvergenceChart series={series} fold={fold} />
      )}
    </Card>
  );
}
