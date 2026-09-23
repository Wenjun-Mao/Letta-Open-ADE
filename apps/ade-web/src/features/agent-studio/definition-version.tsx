"use client";

import type { useAgentStudio } from "./use-agent-studio";

type Controller = ReturnType<typeof useAgentStudio>;
type Translate = (english: string, chinese: string) => string;

export function DefinitionVersion({ controller, t }: { controller: Controller; t: Translate }) {
  const definition = controller.session?.agent_definition;
  if (!definition) return null;
  const prompt = controller.prompts.find((item) => item.key === controller.versionPromptKey);
  const persona = controller.personas.find((item) => item.key === controller.versionPersonaKey);
  return <div className="studio-version-draft">
    <h3>{t("Create next immutable version", "创建下一个不可变版本")}</h3>
    <p className="muted">{t("Edit persona text in Prompt Center, then select the active prompt and persona here. This creates a new snapshot for future conversations; it does not change this conversation.", "在提示词中心编辑人设文本，再在这里选择活跃的提示词和人设。这将为未来对话创建新快照，不会更改当前对话。")}</p>
    <a href="/prompt-center">{t("Open Prompt Center to edit persona", "打开提示词中心编辑人设")}</a>
    <label className="field"><span>{t("Version name", "版本名称")}</span><input className="input" value={controller.versionName} onChange={(event) => controller.setVersionName(event.target.value)} /></label>
    <label className="field"><span>{t("Prompt", "提示词")}</span><select className="input" value={controller.versionPromptKey} onChange={(event) => controller.setVersionPromptKey(event.target.value)}>{controller.prompts.map((item) => <option value={item.key} key={item.key}>{item.label || item.key}</option>)}</select></label>
    {prompt ? <pre className="studio-template-preview">{prompt.content}</pre> : null}
    <label className="field"><span>{t("Persona", "人设")}</span><select className="input" value={controller.versionPersonaKey} onChange={(event) => controller.setVersionPersonaKey(event.target.value)}>{controller.personas.map((item) => <option value={item.key} key={item.key}>{item.label || item.key}</option>)}</select></label>
    {persona ? <pre className="studio-template-preview">{persona.content}</pre> : null}
    <button className="button" disabled={controller.busy || !prompt || !persona || !controller.versionName.trim()} onClick={() => void controller.createDefinitionVersion()}>{t("Create version and select for new conversation", "创建版本并选作新对话定义")}</button>
    <p className="muted">{t("Current conversation remains bound to", "当前对话仍绑定于")} {definition.definition_key} v{definition.version}.</p>
  </div>;
}
