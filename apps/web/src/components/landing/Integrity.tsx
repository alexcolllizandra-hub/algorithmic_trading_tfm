"use client";

import { useLandingCopy } from "@/components/landing/copy";
import { Reveal } from "@/components/landing/Reveal";
import { Section, SectionHeading } from "@/components/landing/Section";
import { useIntlLocale } from "@/lib/i18n";
import { useProvenance } from "@/lib/site-data";

/** The real hash of a real file: the receipt the last principle talks about. */
function ProvenanceReceipt() {
  const { data } = useProvenance();
  const c = useLandingCopy();
  const intl = useIntlLocale();
  const dataset = data?.datasets.find((entry) => entry.partition === "development");

  if (!dataset) return null;

  const rows = [
    { key: "dataset", value: dataset.dataset_id },
    { key: "sha256", value: dataset.sha256 ?? "—" },
    { key: c.integrity.rowRows, value: dataset.rows.toLocaleString(intl) },
    { key: "commit", value: data?.code_commit?.slice(0, 12) ?? "—" },
    {
      key: c.integrity.rowGenerated,
      value: data?.generated_at?.slice(0, 19).replace("T", " ") ?? "—",
    },
  ];

  return (
    <Reveal delay={0.1}>
      <figure className="mt-12 overflow-hidden rounded-card border border-border bg-surface">
        <figcaption className="flex items-center gap-2 border-b border-border px-5 py-3 text-xs text-muted">
          <span className="h-2 w-2 rounded-full bg-positive" aria-hidden />
          {c.integrity.receiptCaption}
        </figcaption>
        <dl className="divide-y divide-border font-mono text-xs">
          {rows.map((row) => (
            <div key={row.key} className="flex flex-col gap-1 px-5 py-3 sm:flex-row sm:gap-4">
              <dt className="w-24 shrink-0 text-muted">{row.key}</dt>
              <dd className="break-all text-fg">{row.value}</dd>
            </div>
          ))}
        </dl>
      </figure>
    </Reveal>
  );
}

export function Integrity() {
  const c = useLandingCopy();

  return (
    <Section id="integridad">
      <SectionHeading
        eyebrow={c.integrity.eyebrow}
        title={c.integrity.title}
        lead={c.integrity.lead}
      />

      <div className="mt-14 grid gap-6 md:grid-cols-2">
        {c.integrity.principles.map((principle, index) => (
          <Reveal key={principle.title} delay={index * 0.06}>
            <article className="flex h-full flex-col rounded-card border border-border bg-surface p-7 transition-colors hover:border-accent/40">
              <h3 className="text-lg font-semibold tracking-tight">{principle.title}</h3>
              <p className="mt-3 text-pretty leading-relaxed text-muted">{principle.plain}</p>
              <p className="mt-5 border-t border-border pt-4 text-sm leading-relaxed text-muted/85">
                <span className="rule-label mr-2 text-accent">{c.integrity.techLabel}</span>
                {principle.technical}
              </p>
            </article>
          </Reveal>
        ))}
      </div>

      <ProvenanceReceipt />
    </Section>
  );
}
