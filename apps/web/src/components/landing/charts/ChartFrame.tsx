import { LANDING_CHART } from "@/components/landing/charts/palette";

/** Shared tooltip shell so every chart on the site reads the same way. */
export function TooltipShell({
  label,
  rows,
}: {
  label: string;
  rows: { key: string; value: string; color?: string }[];
}) {
  return (
    <div
      className="rounded-md border px-3 py-2 text-xs shadow-lg"
      style={{ background: LANDING_CHART.surface, borderColor: LANDING_CHART.border }}
    >
      <p className="mb-1.5 font-mono text-[11px] text-muted">{label}</p>
      {rows.map((row) => (
        <p key={row.key} className="flex items-center gap-2 leading-relaxed">
          {row.color && (
            <span className="h-2 w-2 rounded-full" style={{ background: row.color }} aria-hidden />
          )}
          <span className="text-muted">{row.key}</span>
          <span className="tabular ml-auto pl-3 font-medium">{row.value}</span>
        </p>
      ))}
    </div>
  );
}

export function ChartCaption({ children }: { children: React.ReactNode }) {
  return <p className="mt-3 text-xs leading-relaxed text-muted">{children}</p>;
}
