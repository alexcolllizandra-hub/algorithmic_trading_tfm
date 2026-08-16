import type { Metadata } from "next";

import { Architecture } from "@/components/landing/Architecture";
import { Concepts } from "@/components/landing/Concepts";
import { CostErosion } from "@/components/landing/CostErosion";
import { FinalCta } from "@/components/landing/FinalCta";
import { Hero } from "@/components/landing/Hero";
import { Integrity } from "@/components/landing/Integrity";
import { MarketDashboard } from "@/components/landing/MarketDashboard";
import { Overfitting } from "@/components/landing/Overfitting";
import { Pipeline } from "@/components/landing/Pipeline";
import { PlainExplanation } from "@/components/landing/PlainExplanation";
import { Roadmap } from "@/components/landing/Roadmap";
import { Verdict } from "@/components/landing/Verdict";

export const metadata: Metadata = {
  // Absolute: the root template already appends the brand, and the landing is
  // the one page whose title should carry the full positioning line.
  title: { absolute: "Alx Systems · Investigación reproducible en futuros perpetuos" },
  description:
    "Laboratorio para descubrir y validar estrategias intradía sobre BTC y ETH perpetuo. " +
    "Datos reales, validación cronológica, holdout congelado y resultados negativos publicados.",
};

export default function LandingPage() {
  return (
    <>
      <Hero />
      <PlainExplanation />
      <Concepts />
      <Overfitting />
      <CostErosion />
      <Pipeline />
      <Architecture />
      <Integrity />
      <MarketDashboard />
      <Verdict />
      <Roadmap />
      <FinalCta />
    </>
  );
}
