import type { Metadata } from "next";

import { AuthPanel } from "@/components/auth/AuthPanel";
import { SiteFooter } from "@/components/landing/SiteFooter";
import { SiteHeader } from "@/components/landing/SiteHeader";

export const metadata: Metadata = {
  title: "Acceso",
  description: "Entra o crea una cuenta para seguir los experimentos del estudio.",
  robots: { index: false, follow: false },
};

export default function AccesoPage() {
  return (
    <div className="landing flex min-h-screen flex-col">
      <SiteHeader />
      <main className="flex flex-1 items-center px-6 py-16 md:py-24">
        <AuthPanel />
      </main>
      <SiteFooter />
    </div>
  );
}
