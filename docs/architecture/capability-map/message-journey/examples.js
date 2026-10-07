/* Authored illustration only. Source beats govern when each fictional value appears. */
(function (global) {
  'use strict';

  function create(data) {
    const user = data.current_user, fact = data.existing_fact;
    const proposal = data.review_decision.proposals[0];
    const persona = `${data.persona.name} ${data.persona.version}`;
    const correction = `${fact.value} (v${fact.version}) -> ${proposal.value} (v${fact.version + 1})`;
    const row = (tag, text, meta) => [{tag, text, ...(meta ? {meta} : {})}];
    const timeline = [
      [1, {chat: row('DEMO USER', user.content), accept: row('INPUT', `Message ID: ${user.id}`, `New message from ${data.subject}.`)}],
      [4, {capture: row('SOURCE', `Message ID: ${user.id}`, `Speaker: ${data.subject} (user). Run ID: ${data.run_id}. Exact text, not an accepted fact.`)}],
      [5, {dialogue: row('SAVED MESSAGE', `"${proposal.evidence_quote}"`, `Excerpt; message ID: ${user.id}. Full text retained.`),
        runs: row('QUEUED', `Run ID: ${data.run_id}`, 'Processing job saved with the message; no reply yet.')}],
      [7, {attempt: row('CLAIMED', `Run ID: ${data.run_id}`, 'Worker holds the lease for this attempt.'),
        runs: row('RUNNING', `Run ID: ${data.run_id}`, 'Processing job claimed; no reply yet.')}],
      [9, {binding: row('BOUND', persona, 'Existing immutable version, not a new persona edit.')}],
      [16, {scope: row('SUBJECT', `${data.subject}; subject ID: ${data.subject_id}`, 'Local chat + subject facts; no historical recall.')}],
      [20, {search: row('FACT MATCH', `Location: ${fact.value}`, `Fact ID: ${fact.fact_id}; version ${fact.version}.`)}],
      [22, {delivery: row('LOCAL CHAT', data.previous_user.content, `Selected fact: ${fact.value} v${fact.version}; current user says ${proposal.value}.`)}],
      [23, {dispatch: row('REQUEST', `${persona}; message ID: ${user.id}; local context`, 'No summary in this fictional case.')}],
      [24, {behavior: row('INPUT', `${persona}: ${data.persona.intent}`, 'Current message + tomorrow\'s presentation from local chat.')}],
      [27, {candidate: row('CANDIDATE', data.candidate_reply, 'Not saved or displayed yet.')}],
      [28, {review: row('TYPED INPUT', `Message ID: ${user.id}; location ${fact.value} v${fact.version}`, 'Prior user messages / entities; candidate reply excluded.')}],
      [30, {review: row('PROPOSED', `Correct fact ID: ${fact.fact_id} -> ${proposal.value}`, `Expected version ${proposal.expected_version}; quote: "${proposal.evidence_quote}"`)}],
      [31, {embedding: row('FACT DOCUMENT', `${data.subject}: location ${proposal.value}`, 'Prepared for this proposed correction.')}],
      [33, {embedding: row('VECTOR READY', `Location: ${proposal.value}`, 'Illustrative only; no numeric vector is invented.')}],
      [34, {commit: row('PROPOSAL', correction, 'Not committed yet.')}],
      [36, {commit: row('PENDING', 'Reply + correction + vector', 'Recheck lease, cancellation, v1 and source.')}],
      [37, {commit: row('ATOMIC SUCCESS', `Location: ${proposal.value} v${fact.version + 1}`, 'Reply + fact + index + success saved together.'),
        candidate: row('CANDIDATE', data.candidate_reply, 'Same text saved at commit; not displayed yet.'),
        facts: row('COMMITTED', `Location: ${proposal.value} v${fact.version + 1}`, `Source message ID: ${user.id}`),
        dialogue: row('SAVED REPLY', data.candidate_reply),
        runs: row('SUCCEEDED', `Run ID: ${data.run_id}`, 'Processing job finished; lease released; no new summary.')}],
      [38, {outcome: row('SUCCEEDED', `Run ID: ${data.run_id}`, 'Processing job finished successfully.')}],
      [39, {chat: row('DISPLAYED', data.candidate_reply, 'Reloaded persisted reply; not candidate streaming.')}],
      [40, {lineage: row('CORRECTION', correction, `Source message ID: ${user.id}, not assistant text.`)}],
      [41, {activity: row('PUBLIC STATUS', `Run ID: ${data.run_id}; succeeded`, 'Retained metadata is incomplete; not hidden reasoning.')}],
    ];

    const lessons = global.AdeJourneyTransferExample.create(data);
    const identifiers = [
      [`Message ID: ${user.id}`, 'Identifies Alex\'s exact message, not Alex. It lets saved facts cite their source text.'],
      [`Run ID: ${data.run_id}`, 'Identifies the processing job for this accepted turn. One run can have several worker attempts, but still refers to the same user message.'],
      [`Subject ID: ${data.subject_id}`, 'Identifies whose profile facts these are within the workspace: Alex\'s.'],
      [`Fact ID: ${fact.fact_id}`, 'Identifies the location fact across its revisions: Ottawa v1, then Toronto v2 after a successful correction.'],
      [`Persona version: ${data.persona.version}`, 'Identifies the existing immutable Rowan definition bound to this conversation.'],
    ];

    function forBeat(beat) {
      const ids = global.AdeFlowModel.beatHops(beat).map(hop => hop.edge);
      const lesson = lessons[ids[0]];
      if (!lesson || JSON.stringify(ids) !== JSON.stringify(lesson.edges || [ids[0]])) {
        throw new Error(`Missing or mismatched worked example: ${ids.join(', ')}`);
      }
      return lesson;
    }
    function at(sourceBeat) {
      const values = {};
      for (const [when, changes] of timeline) if (when <= sourceBeat) Object.assign(values, changes);
      return values;
    }
    function decorate(figure) {
      return {...figure, title: `${figure.title} - Fictional worked example`, props: {...figure.props,
        steps: figure.props.steps.map(step => ({...step,
          flow: step.flow.map(beat => {
            forBeat(beat);
            return {...beat, show: {...beat.show,
              ...Object.fromEntries(Object.entries(at(beat.sourceBeat)).filter(([id]) => step.nodes.includes(id))),
            }};
          }),
        })),
      }};
    }
    return {data, timeline, identifiers, lessons, forBeat, at, decorate};
  }

  function render(root, example, chapter, beat) {
    const panel = root.querySelector('[data-example]');
    panel.hidden = chapter == null;
    if (chapter == null) return;
    const key = `${chapter}:${beat.sourceBeat}`;
    if (panel.dataset.action === key) return;
    panel.dataset.action = key;
    panel.dataset.chapter = String(chapter);
    root.querySelector('[data-example-caption]').textContent = example.data.caption;
    const preview = example.forBeat(beat);
    root.querySelector('[data-example-action]').textContent = preview.action;
    for (const [side, values] of [['input', preview.input], ['output', preview.output], ['identifiers', example.identifiers]]) {
      const target = root.querySelector(`[data-example-${side}]`);
      target.replaceChildren();
      for (const [label, value] of values) {
        const term = document.createElement('dt'), description = document.createElement('dd');
        term.textContent = label; description.textContent = value;
        target.append(term, description);
      }
    }
    root.querySelector('[data-example-note]').textContent = preview.note;
  }

  global.AdeJourneyExample = {create, render};
})(globalThis);
