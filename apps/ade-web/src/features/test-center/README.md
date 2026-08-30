# Test Center

Workspace for launching and diagnosing ADE workflows. The chat-memory evaluation path is
evaluation-first: operators compare behavior by configuration and inspect evidence before
falling back to raw artifacts.

- Entry route: `/test-center`
- API contracts: `api.ts`, including generic test runs and chat-memory evaluation list/detail responses.
- Launch state: `chat-memory-evaluation-helpers.ts` parses the one-time URL preset, validates safe numeric values, reconciles it with live chat options, and builds rerun/Prompt Center links.
- Launcher: `test-run-launcher.tsx` displays focused chat-memory and native-v3 acceptance setups and never auto-starts a preset, rerun, or promotion.
- Native qualification: `agent-runtime-v3-acceptance-fields.tsx` selects role-compatible fingerprinted deployments and canonical focused diagnostic cases. A focused case selection forces one round without llama compatibility and cannot claim promotion evidence.
- Evaluation read model: `use-chat-memory-evaluations.ts` owns list/detail selection and cancellation-safe requests; `chat-memory-evaluation-view.tsx` renders comparisons, scorecards, explicit deterministic failures, final memory layers, line-level memory deltas, and complete round/turn tool evidence.
- Secondary diagnostics: `run-artifact-viewer.tsx` keeps generic artifacts and output tails accessible without making raw files the primary workflow.
- Tests: `chat-memory-evaluation-helpers.test.ts` covers query hydration, option reconciliation, polling eligibility, Prompt Center links, and rerun presets.
