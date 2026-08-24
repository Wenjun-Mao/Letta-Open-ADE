"use client";

import { COMMENT_LAB_COPY } from "./copy";
import {
  CommentLabDiagnosticsPanel,
  CommentLabPayloadModal,
  CommentLabSettingsPanel,
  CommentLabWorkspacePanel,
} from "./panels";
import { useCommentLab } from "./use-comment-lab";
import { useI18n } from "@/shared/i18n";

export default function CommentLabPage() {
  const { locale } = useI18n();
  const copy = COMMENT_LAB_COPY[locale];
  const controller = useCommentLab(copy);

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <p className="muted" style={{ maxWidth: 860 }}>{copy.intro}</p>
      {controller.status ? <div className="card" style={{ marginTop: 12, borderColor: "#86efac" }}><p>{controller.status}</p></div> : null}
      {controller.error ? <div className="card" style={{ marginTop: 12, borderColor: "#fecaca" }}><p>{controller.error}</p></div> : null}
      <div className="studio-layout" style={{ marginTop: 14 }}>
        <CommentLabSettingsPanel copy={copy} controller={controller} />
        <CommentLabWorkspacePanel copy={copy} controller={controller} />
        <CommentLabDiagnosticsPanel copy={copy} controller={controller} />
      </div>
      <CommentLabPayloadModal copy={copy} card={controller.popOutCard} onClose={() => controller.setPopOutCard(null)} />
    </section>
  );
}
