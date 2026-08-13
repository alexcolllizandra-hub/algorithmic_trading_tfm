import { ErrorState } from "@/components/ui/States";
import { ApiError } from "@/lib/api";
import { es } from "@/lib/i18n/es";

/**
 * The study endpoints answer 503 while the consolidated artifact has not been
 * built, which is a build step and not a failure — say so explicitly.
 */
export function StudyUnavailable({ error }: { error: unknown }) {
  if (error instanceof ApiError && error.status === 503) {
    return <ErrorState title={es.study.unavailable.title} detail={es.study.unavailable.detail} />;
  }
  return (
    <ErrorState
      title={es.study.unavailable.generic}
      detail={error instanceof Error ? error.message : String(error)}
    />
  );
}
