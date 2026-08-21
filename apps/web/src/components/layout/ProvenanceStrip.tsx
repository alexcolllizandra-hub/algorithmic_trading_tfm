"use client";

// Provenance strip shown at the bottom of every panel page (phase 7 of the
// restructure): when the static exports were generated, from which code
// commit, and the command that regenerates them. Values come from the
// committed provenance export; nothing renders while it loads.

import { useI18n } from "@/lib/i18n";
import { useProvenance } from "@/lib/site-data";

export function ProvenanceStrip() {
  const t = useI18n();
  const { data } = useProvenance();
  if (!data) return null;

  return (
    <p className="border-t border-border pt-4 font-mono text-[11px] leading-relaxed text-muted/70">
      {t.provenance.generated} {data.generated_at.slice(0, 10)} · commit{" "}
      {data.code_commit?.slice(0, 12) ?? "—"} · {t.provenance.contract} v{data.contract_version} ·{" "}
      {t.provenance.holdout} {data.holdout_start.slice(0, 10)} · {t.provenance.regen}{" "}
      <span className="text-accent">uv run python scripts/export_web_data.py</span>
    </p>
  );
}
