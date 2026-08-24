# Agent Studio

Persistent-agent workspace for creation, chat, memory inspection, prompt updates, lifecycle actions, and tool probes.

- Entry route: `/agent-studio`
- API client: `api.ts`
- Main view: `page.tsx`; it composes creation, lifecycle, chat, execution trace, and inspection hooks.
- Setup controls: `agent-creation-form.tsx` owns new-agent configuration, while `agent-selection-controls.tsx` owns selecting, refreshing, and lifecycle actions. `agent-setup-controls.tsx` places both in the inspector.
- Inspector tabs: `agent-details-inspector.tsx` selects the model, prompt, and tool tabs. Each tab has its own view module: `model-inspector-tab.tsx`, `prompt-inspector-tab.tsx`, and `tool-inspector-tab.tsx`.
- Inspection hooks: `use-agent-inspection.ts` coordinates tab state and selection cleanup. `use-agent-model-editor.ts`, `use-prompt-inspection.ts`, and `use-tool-inspection.ts` own their respective requests and view state.
- Tests: colocated beside deterministic view-model helpers.
