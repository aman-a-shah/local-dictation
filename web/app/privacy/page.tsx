import type { Metadata } from "next";
import { renderLegal } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "Local Dictation runs 100% on-device. Your voice and transcripts never leave your machine. Read the full policy.",
};

export default function PrivacyPage() {
  const { html } = renderLegal("privacy");
  return (
    <article className="container container--narrow section">
      <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />
    </article>
  );
}
