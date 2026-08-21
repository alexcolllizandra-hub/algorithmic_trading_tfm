"use client";

// Notebook index (phase 5 of the panel restructure): the eight analysis
// notebooks with their frozen figure/table inventory and the thesis-chapter
// destination, read from the static export written by
// scripts/export_notebooks_index.py. The chapter labels quote the committed
// chapter map (docs/thesis/mapa_capitulos_artefactos.md).

import useSWR from "swr";

import { PageShell } from "@/components/layout/PageShell";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { useI18n } from "@/lib/i18n";

interface NotebookEntry {
  id: string;
  file: string;
  title: string;
  n_cells: number;
  theme: string | null;
  builder: string;
  chapter: string;
  figures: { id: string; kb: number }[];
  tables: string[];
  chain: string[];
}

interface NotebooksFile {
  generated_at: string;
  chapter_source: string;
  notebooks: NotebookEntry[];
}

const load = async (path: string): Promise<NotebooksFile> => {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return response.json();
};

function ChipList({ items }: { items: string[] }) {
  return (
    <span className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <code
          key={item}
          className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted"
        >
          {item}
        </code>
      ))}
    </span>
  );
}

function NotebookCard({ nb, source }: { nb: NotebookEntry; source: string }) {
  const t = useI18n();
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-3">
            <span className="tabular flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent/15 text-sm font-semibold text-accent">
              {nb.id}
            </span>
            <span className="text-base font-semibold">{nb.title}</span>
          </p>
          <p className="mt-1.5 font-mono text-xs text-muted">
            notebooks/{nb.file} · {nb.n_cells} {t.cuadernos.cells}
          </p>
        </div>
        <Badge tone="accent">{nb.theme ?? "síntesis"}</Badge>
      </div>

      <dl className="mt-4 space-y-3 text-sm">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
            {t.cuadernos.chapterLabel}{" "}
            <span className="font-normal normal-case">
              ({t.cuadernos.chapterSource} <code className="font-mono text-[10px]">{source}</code>)
            </span>
          </dt>
          <dd className="mt-1">{nb.chapter}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
            {t.cuadernos.builderLabel}
          </dt>
          <dd className="mt-1 font-mono text-xs text-accent">
            uv run python {nb.builder.replace(/\\/g, "/")}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
            {t.cuadernos.figuresLabel} ({nb.figures.length})
          </dt>
          <dd className="mt-1.5">
            {nb.figures.length ? (
              <ChipList items={nb.figures.map((f) => f.id)} />
            ) : (
              t.cuadernos.none
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
            {t.cuadernos.tablesLabel} ({nb.tables.length})
          </dt>
          <dd className="mt-1.5">
            {nb.tables.length ? <ChipList items={nb.tables} /> : t.cuadernos.none}
          </dd>
        </div>
        {nb.chain.length > 0 && (
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
              {t.cuadernos.chainLabel}
            </dt>
            <dd className="mt-1.5">
              <ChipList items={nb.chain} />
            </dd>
          </div>
        )}
      </dl>
    </Card>
  );
}

export default function CuadernosPage() {
  const t = useI18n();
  const { data, error } = useSWR<NotebooksFile>("/data/notebooks.json", load, {
    revalidateOnFocus: false,
  });

  return (
    <PageShell title={t.cuadernos.title}>
      <Card>
        <CardHeader title={t.cuadernos.title} subtitle={t.cuadernos.subtitle} />
        <dl className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {[
            { q: t.cuadernos.que, a: t.cuadernos.queAnswer },
            { q: t.cuadernos.como, a: t.cuadernos.comoAnswer },
            { q: t.cuadernos.queNo, a: t.cuadernos.queNoAnswer },
          ].map(({ q, a }) => (
            <div key={q} className="rounded-md border border-border bg-surface-2 px-4 py-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-accent">{q}</dt>
              <dd className="mt-2 text-sm text-muted">{a}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {error && <ErrorState title={t.cuadernos.loadError} />}
      {!data && !error && <Skeleton className="h-96" />}

      {data && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          {data.notebooks.map((nb) => (
            <NotebookCard key={nb.id} nb={nb} source={data.chapter_source} />
          ))}
        </div>
      )}
    </PageShell>
  );
}
