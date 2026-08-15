import { SiteFooter } from "@/components/landing/SiteFooter";
import { SiteHeader } from "@/components/landing/SiteHeader";

// `.landing` swaps the design-system variables for the brand palette, so the
// public site stays dark regardless of the dashboard's theme toggle.
export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="landing flex min-h-screen flex-col">
      <SiteHeader />
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </div>
  );
}
