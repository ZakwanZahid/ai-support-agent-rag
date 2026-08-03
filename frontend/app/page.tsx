import { CtaSection } from "@/components/marketing/cta-section";
import { FeatureGrid } from "@/components/marketing/feature-grid";
import { Hero } from "@/components/marketing/hero";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { LandingHeader } from "@/components/marketing/landing-header";
import { ProblemSection } from "@/components/marketing/problem-section";
import { SiteFooter } from "@/components/marketing/site-footer";
import { UseCases } from "@/components/marketing/use-cases";

export default function LandingPage() {
  return (
    <div className="min-h-dvh bg-background">
      <LandingHeader />
      <main id="main-content">
        <Hero />
        <ProblemSection />
        <HowItWorks />
        <FeatureGrid />
        <UseCases />
        <CtaSection />
      </main>
      <SiteFooter />
    </div>
  );
}
