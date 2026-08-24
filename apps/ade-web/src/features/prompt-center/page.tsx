"use client";

import { COPY } from "./copy";
import { PromptCenterToolbar, PromptTemplateEditor, PromptTemplateList } from "./panels";
import { usePromptCenter } from "./use-prompt-center";
import { useI18n } from "@/shared/i18n";

export default function PromptCenterPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const controller = usePromptCenter(copy);

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <p className="muted" style={{ maxWidth: 840 }}>{copy.subtitle}</p>

      <PromptCenterToolbar copy={copy} controller={controller} />

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
        <PromptTemplateList copy={copy} controller={controller} />
        <PromptTemplateEditor copy={copy} controller={controller} />
      </div>
    </section>
  );
}
