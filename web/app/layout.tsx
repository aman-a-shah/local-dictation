import type { Metadata, Viewport } from "next";
import "@local-dictation/ui/tokens.css";
import "@local-dictation/ui/components.css";
import "@local-dictation/ui/fonts";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { SmoothScroll } from "@/components/SmoothScroll";

const description =
  "Push-to-talk voice typing that runs 100% on your device. Hold a key, speak, release — your words are transcribed locally and pasted at your cursor. No cloud, no account, your voice never leaves your machine.";

export const metadata: Metadata = {
  metadataBase: new URL("https://local-transcription-tool.vercel.app"),
  title: {
    default: "Local Dictation — private, on-device voice typing",
    template: "%s — Local Dictation",
  },
  description,
  applicationName: "Local Dictation",
  openGraph: {
    title: "Local Dictation — private, on-device voice typing",
    description,
    type: "website",
  },
  twitter: { card: "summary_large_image" },
  icons: { icon: "/favicon.svg" },
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
  colorScheme: "light",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <SmoothScroll />
        <Nav />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
