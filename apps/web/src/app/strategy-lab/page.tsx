"use client";

import { PageShell } from "@/components/layout/PageShell";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { PartialNotice } from "@/components/ui/States";

interface Family {
  name: string;
  title: string;
  summary: string;
  params: { name: string; kind: string; note: string }[];
  constraints: string[];
}

// Static, human-readable description of the strategy families and their tunable
// spaces. The authoritative machine definition lives in the API search-space
// artifact (Artifact Inspector); this page is the readable narrative.
const FAMILIES: Family[] = [
  {
    name: "momentum",
    title: "Momentum crossover",
    summary:
      "Trades the sign of a fast/slow moving-average crossover, with optional momentum, volatility and regime filters.",
    params: [
      { name: "fast", kind: "int", note: "fast MA window (bars)" },
      { name: "slow", kind: "int", note: "slow MA window (bars); must exceed fast" },
      { name: "use_momentum_filter", kind: "bool", note: "gate entries on positive momentum" },
      { name: "vol_filter_pct", kind: "float?", note: "optional volatility ceiling percentile" },
      { name: "regime_filter", kind: "categorical?", note: "restrict to regime label(s)" },
    ],
    constraints: ["fast < slow", "windows within configured warm-up budget"],
  },
  {
    name: "breakout",
    title: "Channel breakout",
    summary:
      "Enters on breaks of a Donchian channel built only from PRIOR highs/lows (current bar excluded), with a confirmation period and configurable exit.",
    params: [
      { name: "channel", kind: "int", note: "lookback for the high/low channel" },
      { name: "confirm", kind: "int", note: "bars price must hold beyond the channel" },
      { name: "exit_rule", kind: "categorical", note: "opposite-channel / mid / time exit" },
    ],
    constraints: ["channel excludes the current bar", "confirm ≥ 1"],
  },
  {
    name: "mean_reversion",
    title: "Z-score mean reversion",
    summary:
      "Fades extreme rolling price z-scores; enters beyond entry_z and exits inside exit_z, with optional volatility/trend/regime filters.",
    params: [
      { name: "window", kind: "int", note: "rolling window for mean/std" },
      { name: "entry_z", kind: "float", note: "entry threshold (|z|)" },
      { name: "exit_z", kind: "float", note: "exit threshold; must be < entry_z" },
    ],
    constraints: ["exit_z < entry_z", "window within warm-up budget"],
  },
];

export default function StrategyLabPage() {
  return (
    <PageShell title="Strategy Lab">
      <PartialNotice>
        Read-only in V1. Execution controls will be added only after asynchronous jobs and safety
        controls exist. Parameter values are sourced from the validated experiment configuration.
      </PartialNotice>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {FAMILIES.map((f) => (
          <Card key={f.name}>
            <CardHeader title={f.title} right={<Badge tone="accent">{f.name}</Badge>} />
            <p className="mb-4 text-sm text-muted">{f.summary}</p>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
              Parameters
            </h3>
            <ul className="mb-4 space-y-1.5 text-sm">
              {f.params.map((p) => (
                <li key={p.name} className="flex items-baseline justify-between gap-3">
                  <span className="font-mono text-xs text-fg">{p.name}</span>
                  <span className="text-right text-xs text-muted">
                    <Badge>{p.kind}</Badge> {p.note}
                  </span>
                </li>
              ))}
            </ul>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
              Constraints
            </h3>
            <ul className="list-inside list-disc space-y-1 text-xs text-muted">
              {f.constraints.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </PageShell>
  );
}
