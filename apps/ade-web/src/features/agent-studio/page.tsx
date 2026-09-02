"use client";

import { Suspense } from "react";

import { useI18n } from "@/shared/i18n";

import { AgentStudioView } from "./agent-studio-view";
import { useAgentStudio } from "./use-agent-studio";

export default function AgentStudioPage() {
  return <Suspense fallback={<p className="muted">Loading Agent Studio...</p>}><AgentStudioContent /></Suspense>;
}

function AgentStudioContent() {
  const { locale } = useI18n();
  const controller = useAgentStudio();
  const t = (english: string, chinese: string) => (locale === "zh" ? chinese : english);

  return <AgentStudioView controller={controller} t={t} />;
}
