import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Platform ADE",
  description: "Separate ADE frontend for Agent Platform migration",
};

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/agent-studio", label: "Agent Studio" },
  { href: "/prompt-persona-lab", label: "Prompt and Persona Lab" },
  { href: "/toolbench", label: "Toolbench" },
  { href: "/test-center", label: "Test Center" },
  { href: "/api-docs", label: "API Docs" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <div className="topbar-inner">
            <div className="brand">Agent Platform ADE (Preview)</div>
            <nav className="nav" aria-label="ADE navigation">
              {NAV_ITEMS.map((item) => (
                <Link className="nav-link" key={item.href} href={item.href}>
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
