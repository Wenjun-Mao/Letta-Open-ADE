"use client";

import { LABEL_LAB_COPY } from "./copy";
import {
  LabelLabDiagnosticsPanels,
  LabelLabResultPanel,
  LabelLabSettingsPanel,
  LabelLabWorkspacePanel,
} from "./panels";
import { useLabelLab } from "./use-label-lab";
import { useI18n } from "@/shared/i18n";

export default function LabelLabPage() {
  const { locale } = useI18n();
  const copy = LABEL_LAB_COPY[locale];
  const controller = useLabelLab(copy);

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <p className="muted" style={{ maxWidth: 860 }}>{copy.intro}</p>
      {controller.status ? <div className="card" style={{ marginTop: 12, borderColor: "#86efac" }}><p>{controller.status}</p></div> : null}
      {controller.error ? <div className="card" style={{ marginTop: 12, borderColor: "#fecaca" }}><p>{controller.error}</p></div> : null}
      <div className="studio-layout" style={{ marginTop: 14 }}>
        <LabelLabSettingsPanel copy={copy} controller={controller} />
        <LabelLabWorkspacePanel copy={copy} controller={controller} />
        <LabelLabResultPanel copy={copy} controller={controller} />
      </div>
      <LabelLabDiagnosticsPanels copy={copy} controller={controller} />
    </section>
  );
}
