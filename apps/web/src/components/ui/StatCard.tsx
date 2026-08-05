import { InfoTip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/cn";
import { metricHelp } from "@/lib/metrics";

export function StatCard({
  label,
  value,
  sub,
  metricKey,
  valueClassName,
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  metricKey?: string;
  valueClassName?: string;
}) {
  const help = metricKey ? metricHelp(metricKey) : undefined;
  return (
    <div className="rounded-card border border-border bg-surface p-4">
      <div className="flex items-center text-xs uppercase tracking-wide text-muted">
        {label}
        {help && <InfoTip text={help} label={label} />}
      </div>
      <div className={cn("tabular mt-1 text-2xl font-semibold", valueClassName)}>{value}</div>
      {sub && <div className="mt-1 text-xs text-muted">{sub}</div>}
    </div>
  );
}
