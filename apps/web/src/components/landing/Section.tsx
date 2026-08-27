import { Reveal } from "@/components/landing/Reveal";
import { cn } from "@/lib/cn";

export function Section({
  id,
  children,
  className,
}: {
  id: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      id={id}
      className={cn("scroll-mt-20 border-t border-border/70 py-20 md:py-28", className)}
    >
      <div className="mx-auto w-full max-w-6xl px-6">{children}</div>
    </section>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  lead,
  align = "left",
}: {
  eyebrow: string;
  title: React.ReactNode;
  lead?: React.ReactNode;
  align?: "left" | "center";
}) {
  return (
    <Reveal className={cn("max-w-3xl", align === "center" && "mx-auto text-center")}>
      <p className="rule-label text-accent">{eyebrow}</p>
      <h2 className="mt-4 text-balance text-3xl font-semibold tracking-tight md:text-4xl">
        {title}
      </h2>
      {lead && <p className="mt-4 text-pretty text-lg leading-relaxed text-muted">{lead}</p>}
    </Reveal>
  );
}
