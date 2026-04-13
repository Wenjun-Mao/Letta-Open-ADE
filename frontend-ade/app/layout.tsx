import type { Metadata } from "next";
import "./globals.css";
import { TopNav } from "./components/top-nav";
import { I18nProvider } from "../lib/i18n";

export const metadata: Metadata = {
  title: "Agent Platform ADE",
  description: "Operator frontend for Agent Platform workflows",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <I18nProvider>
          <header className="topbar">
            <div className="topbar-inner">
              <div className="brand">Agent Platform ADE</div>
              <TopNav />
            </div>
          </header>
          <main>{children}</main>
        </I18nProvider>
      </body>
    </html>
  );
}
