import type { Metadata } from "next";
import "./globals.css";
import "./responsive-audit.css";
import "./next-action-layout.css";
import { TickerProfileEnhancer } from "@/components/ticker-profile";

export const metadata: Metadata = {
  title: "Momentum Console",
  description:
    "モメンタム戦略の市場判定、銘柄選定、配分、バックテストを一元管理します。",
  icons: {
    icon: "./icon.svg",
    shortcut: "./icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" suppressHydrationWarning>
      <body>{children}<TickerProfileEnhancer /></body>
    </html>
  );
}
