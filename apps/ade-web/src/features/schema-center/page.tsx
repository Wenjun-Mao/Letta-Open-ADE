"use client";

import { COPY } from "./copy";
import { LabelSchemaEditor, LabelSchemaList, SchemaCenterToolbar } from "./panels";
import { useSchemaCenter } from "./use-schema-center";
import { useI18n } from "@/shared/i18n";

export default function SchemaCenterPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const controller = useSchemaCenter(copy);

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <p className="muted" style={{ maxWidth: 820 }}>{copy.subtitle}</p>

      <SchemaCenterToolbar copy={copy} controller={controller} />

      {controller.error ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#fecaca" }}>
          <p>{controller.error}</p>
        </div>
      ) : null}
      {controller.status ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#bbf7d0" }}>
          <p>{controller.status}</p>
        </div>
      ) : null}

      <div className="card-grid" style={{ marginTop: 14, alignItems: "start" }}>
        <LabelSchemaList copy={copy} controller={controller} />
        <LabelSchemaEditor copy={copy} controller={controller} />
      </div>
    </section>
  );
}
