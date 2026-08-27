import type { Metadata } from "next";

import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { I18nProvider } from "@/lib/i18n";
import { AuthProvider } from "@/lib/auth/AuthContext";
import "@/app/globals.css";

// Absolute base for Open Graph and canonical URLs. Override per deployment with
// NEXT_PUBLIC_SITE_URL; without it, share cards would resolve against localhost.
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://quantivelasystems.com";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Alx Systems",
    template: "%s · Alx Systems",
  },
  description:
    "Laboratorio reproducible de estrategias intradía sobre futuros perpetuos de BTC y ETH.",
  applicationName: "Alx Systems",
  openGraph: {
    type: "website",
    locale: "es_ES",
    url: SITE_URL,
    siteName: "Alx Systems",
    title: "Alx Systems · Investigación reproducible en futuros perpetuos",
    description:
      "Seis años de datos reales de BTC y ETH perpetuo, validación cronológica y resultados " +
      "negativos publicados. Todo reproducible desde el código.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Alx Systems · Investigación reproducible en futuros perpetuos",
    description:
      "Seis años de datos reales de BTC y ETH perpetuo, validación cronológica y resultados " +
      "negativos publicados.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <I18nProvider>
            <AuthProvider>{children}</AuthProvider>
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
