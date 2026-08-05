import { Topbar } from "@/components/layout/Topbar";

export function PageShell({
  title,

  children,
}: {
  title: string;

  children: React.ReactNode;
}) {
  return (
    <>
      <Topbar title={title} />

      <main className="mx-auto w-full max-w-[1400px] flex-1 space-y-6 px-6 py-6">{children}</main>
    </>
  );
}
