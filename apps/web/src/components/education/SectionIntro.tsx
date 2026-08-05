import { Card, CardHeader } from "@/components/ui/Card";

export interface SectionQuestions {
  que: string;
  queAnswer: string;
  porQue: string;
  porQueAnswer: string;
  comoInterpretar: string;
  comoInterpretarAnswer: string;
  queConcluir: string;
  queConcluirAnswer: string;
}

export function SectionIntro({
  title,
  subtitle,
  questions,
}: {
  title: string;
  subtitle: string;
  questions: SectionQuestions;
}) {
  const items = [
    { q: questions.que, a: questions.queAnswer },
    { q: questions.porQue, a: questions.porQueAnswer },
    { q: questions.comoInterpretar, a: questions.comoInterpretarAnswer },
    { q: questions.queConcluir, a: questions.queConcluirAnswer },
  ];

  return (
    <Card>
      <CardHeader title={title} subtitle={subtitle} />
      <dl className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {items.map(({ q, a }) => (
          <div key={q} className="rounded-md border border-border bg-surface-2 px-4 py-3">
            <dt className="text-xs font-semibold uppercase tracking-wide text-accent">{q}</dt>
            <dd className="mt-2 text-sm text-muted">{a}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
