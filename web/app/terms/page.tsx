import type { Metadata } from "next";
import { renderLegal } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Terms of Use",
  description: "The terms governing your use of Voca.",
};

export default function TermsPage() {
  const { html } = renderLegal("terms");
  return (
    <article className="container container--narrow section">
      <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />
    </article>
  );
}
