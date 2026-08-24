"use client";

import { COPY } from "./copy";
import { ToolCenterToolbar, ToolEditor, ToolList } from "./panels";
import { useToolCenter } from "./use-tool-center";
import { useI18n } from "@/shared/i18n";

export default function ToolCenterPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const controller = useToolCenter(copy);

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <p className="muted" style={{ maxWidth: 840 }}>{copy.subtitle}</p>

      <ToolCenterToolbar copy={copy} controller={controller} />

      {controller.error ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#fecaca" }}>
          <h3>Error</h3>
          <p className="muted">{controller.error}</p>
        </div>
      ) : null}
      {controller.status ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#bbf7d0" }}>
          <h3>Status</h3>
          <p className="muted">{controller.status}</p>
        </div>
      ) : null}

      <div className="card-grid" style={{ marginTop: 14, alignItems: "start" }}>
        <ToolList copy={copy} controller={controller} />
        <ToolEditor copy={copy} controller={controller} />
      </div>
    </section>
  );
}
