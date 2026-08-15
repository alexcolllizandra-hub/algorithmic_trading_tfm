import type { Metadata } from "next";

import { Concepts } from "@/components/landing/Concepts";
import { FinalCta } from "@/components/landing/FinalCta";
import { Hero } from "@/components/landing/Hero";
import { Integrity } from "@/components/landing/Integrity";
import { MarketDashboard } from "@/components/landing/MarketDashboard";
import { Pipeline } from "@/components/landing/Pipeline";
import { PlainExplanation } from "@/components/landing/PlainExplanation";
import { Roadmap } from "@/components/landing/Roadmap";

export const metadata: Metadata = {
  title: "Alx Systems · Investigación reproducible en futuros perpetuos",
  description:
    "Laboratorio para descubrir y validar estrategias intradía sobre BTC y ETH perpetuo. " +
    "Datos reales, validación cronológica, holdout congelado y resultados negativos publicados.",
};

export default function LandingPage() {
  return (
    <>
      <Hero />
      <PlainExplanation />
      <Pipeline />
      <Integrity />
      <Concepts />
      <MarketDashboard />
      <Roadmap />
      <FinalCta />
    </>
  );
}
