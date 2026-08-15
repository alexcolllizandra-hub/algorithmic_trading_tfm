import type { Metadata } from "next";

import { ThemeProvider } from "@/components/layout/ThemeProvider";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: {
    default: "perp-lab",
    template: "%s · perp-lab",
  },
  description:
    "Laboratorio reproducible de estrategias intradía sobre futuros perpetuos de BTC y ETH.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
