import type { Metadata } from "next";
import "./globals.css";
import { TopNav } from "@/shared/components/top-nav";
import { I18nProvider } from "@/shared/i18n";

export const metadata: Metadata = {
  title: "Letta Open ADE",
  description: "Operator workspace for agent and model development",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <I18nProvider>
          <header className="topbar">
            <div className="topbar-inner">
              <div className="brand">Letta Open ADE</div>
              <TopNav />
            </div>
          </header>
          <main>{children}</main>
        </I18nProvider>
      </body>
    </html>
  );
}
