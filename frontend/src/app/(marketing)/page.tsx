import { Cta } from "@/components/landing/cta";
import { Features } from "@/components/landing/features";
import { Footer } from "@/components/landing/footer";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Industries } from "@/components/landing/industries";
import { Navbar } from "@/components/landing/navbar";

export default function LandingPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        <Hero />
        <HowItWorks />
        <Features />
        <Industries />
        <Cta />
      </main>
      <Footer />
    </>
  );
}
