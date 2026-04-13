"use client";

import { useI18n } from "../../lib/i18n";

const COPY = {
  en: {
    kicker: "Docs",
    title: "Documentation Entry",
    description: "This local route provides a direct documentation entry point for operators and developers.",
    configFile: "Mintlify config file",
    openapiArtifact: "OpenAPI artifact",
    exporterScript: "Exporter script",
    validatorScript: "Validator script",
  },
  zh: {
    kicker: "文档",
    title: "文档入口",
    description: "该本地路由为运维与开发提供直接的文档入口。",
    configFile: "Mintlify 配置文件",
    openapiArtifact: "OpenAPI 产物",
    exporterScript: "导出脚本",
    validatorScript: "校验脚本",
  },
} as const;

export default function LocalDocsPage() {
  const { locale } = useI18n();
  const copy = COPY[locale];

  return (
    <section>
      <div className="kicker">{copy.kicker}</div>
      <h1 className="section-title">{copy.title}</h1>
      <div className="card">
        <p className="muted">{copy.description}</p>
        <ul className="list">
          <li>{copy.configFile}: docs/docs.json</li>
          <li>{copy.openapiArtifact}: docs/openapi/agent-platform-openapi.json</li>
          <li>{copy.exporterScript}: scripts/export_openapi.py</li>
          <li>{copy.validatorScript}: scripts/validate_docs_config.py</li>
        </ul>
      </div>
    </section>
  );
}
