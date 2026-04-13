export default function LocalDocsPage() {
  return (
    <section>
      <div className="kicker">Docs</div>
      <h1 className="section-title">Documentation Entry</h1>
      <div className="card">
        <p className="muted">
          This local route provides a direct documentation entry point for operators and developers.
        </p>
        <ul className="list">
          <li>Mintlify config file: docs/docs.json</li>
          <li>OpenAPI artifact: docs/openapi/agent-platform-openapi.json</li>
          <li>Exporter script: scripts/export_openapi.py</li>
          <li>Validator script: scripts/validate_docs_config.py</li>
        </ul>
      </div>
    </section>
  );
}
