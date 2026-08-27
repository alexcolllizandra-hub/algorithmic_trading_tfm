import { ErrorState } from "@/components/ui/States";
import { useI18n } from "@/lib/i18n";
import { ApiError } from "@/lib/api";

/**
 * The study endpoints answer 503 while the consolidated artifact has not been
 * built, which is a build step and not a failure — say so explicitly.
 */
export function StudyUnavailable({ error }: { error: unknown }) {
  const t = useI18n();
  if (error instanceof ApiError && error.status === 503) {
    return <ErrorState title={t.study.unavailable.title} detail={t.study.unavailable.detail} />;
  }
  return (
    <ErrorState
      title={t.study.unavailable.generic}
      detail={error instanceof Error ? error.message : String(error)}
    />
  );
}
