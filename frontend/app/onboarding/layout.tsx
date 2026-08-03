import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Set up your workspace",
};

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
