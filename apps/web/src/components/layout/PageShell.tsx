import { ProvenanceStrip } from "@/components/layout/ProvenanceStrip";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

export function PageShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={title} />
        <main className="mx-auto w-full max-w-[1400px] flex-1 space-y-6 px-6 py-6">
          {children}
          <ProvenanceStrip />
        </main>
      </div>
    </div>
  );
}
