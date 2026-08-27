import { Badge } from "@/components/ui/Badge";
import { statusDescriptor } from "@/lib/study";

/**
 * Renders a backend status through the shared vocabulary. The machine code stays
 * available as the title so the Spanish label never hides what the API said.
 */
export function StatusBadge({
  status,
  className,
}: {
  status: string | null | undefined;
  className?: string;
}) {
  const { code, label, tone } = statusDescriptor(status);
  return (
    <Badge tone={tone} className={className}>
      <span title={code}>{label}</span>
    </Badge>
  );
}
