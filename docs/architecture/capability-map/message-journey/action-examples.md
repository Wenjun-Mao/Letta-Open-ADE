# Action-Level Worked Examples

Presentation refinement, 2026-10-07. Supersedes the initial chapter-wide Input /
Output preview; the fictional scenario, source boundaries and six chapters remain.
This changes teaching and navigation only, not ADE runtime behavior or product
intent (PC-04/05/08/09/12).

## Problem And Decision

The chapter-wide preview stayed constant while the animation highlighted smaller
transfers. It could show a future chapter result without explaining the current
arrow. Payload shorthand also confused the user with their message (`original
user`) and left `u-demo` and `r-demo` unexplained. The defect was presentation,
not source capture or runtime processing.

Use the existing example panel for the **current action**: a plain-language action,
concrete input, after-action example and a qualification of what has not happened.
Every guided transfer has a lesson bound to its existing edge identity. Grouped
atomic transfers share one lesson and cannot be split by navigation. Missing or
mismatched lessons fail instead of silently reverting to a generic chapter preview.
The guide still omits repeated/provider mechanics; relevant lessons say so rather
than fabricating their internal output or adding architecture phases.

Message, run, subject and fact IDs have explicit type labels wherever they appear
in the diagram. The same panel defines their meanings, including the distinction
between a processing job (run) and one worker attempt. Source capture shows the
message/run links; the next grouped beat shows atomic saving. Recording Alex's
statement does not itself accept the Toronto fact, and the typed reviewer still
excludes the candidate reply. All values remain authored fiction, not API JSON,
provider observations or measured success.

## Navigation And Guardrails

Previous/Next action stays in the selected chapter, pauses motion and respects
action boundaries. The existing chapter Back/Forward, playback end-stops and saved
presentation revision remain compatible. Manual actions work with reduced motion.
The example updates only on beat changes, not on every animation frame. Detailed,
conditional and experimental tours do not inherit this fictional success scenario.

Rejected: more permanent panels, a new pipeline, replacing chapter navigation,
inventing provider responses, or labeling IDs solely in tooltips. These would add
complexity or hide the essential explanation.

Offline tests cover all 23 actions, exact transfer/group bindings, ID meanings,
pending/committed/displayed distinctions, playback interruption, saved action,
reduced motion, inert strings, stable geometry and regenerated output. Native SVG
snapshots check diagram labels at wide and narrow widths. These do not qualify
Safari page layout, host integration, assistive technology or semantic reliability.
