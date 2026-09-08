# Test Center

Test Center is the ADE workspace for launching and inspecting maintained
workflows. It has three explicit forms, each with local state:

1. Behavior evaluation.
2. Agent runtime qualification.
3. Current-stack smoke testing.

`api.ts` owns the discriminated Test Center request/response contracts.
`page.tsx` composes the three launchers. `use-test-center-runs.ts` owns run
polling and selection. `test-center-view.tsx` is the shared run-detail and
artifact viewer.

The UI never auto-starts a run or synchronizes unrelated workflow selections.
Artifacts are secondary diagnostics; the primary view is the workflow's typed
status and evidence.
