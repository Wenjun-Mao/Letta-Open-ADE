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
      [1, {chat: row('DEMO USER', user.content), accept: row('INPUT', `${user.id}; new turn`)}],
      [4, {capture: row('SOURCE', `${user.id} / ${data.subject}`, 'Exact original text, not an accepted fact.')}],
      [5, {dialogue: row('SAVED USER', `"${proposal.evidence_quote}"`, `Excerpt of ${user.id}; full message retained.`),
        runs: row('QUEUED', data.run_id, 'User + run saved together; no reply yet.')}],
      [7, {attempt: row('CLAIMED', `${data.run_id}; lease held`),
        runs: row('RUNNING', data.run_id, 'Worker claimed the run; no reply yet.')}],
      [9, {binding: row('BOUND', persona, 'Existing immutable version, not a new persona edit.')}],
      [16, {scope: row('SUBJECT', `${data.subject} / ${data.subject_id}`, 'Local chat + subject facts; no historical recall.')}],
      [20, {search: row('FACT MATCH', `Location: ${fact.value}`, `${fact.fact_id} / v${fact.version}`)}],
      [22, {delivery: row('LOCAL CHAT', data.previous_user.content, `Selected fact: ${fact.value} v${fact.version}; current user says ${proposal.value}.`)}],
      [23, {dispatch: row('REQUEST', `${persona} + ${user.id} + local context`, 'No summary in this fictional case.')}],
      [24, {behavior: row('INPUT', `${persona}: ${data.persona.intent}`, 'Current message + tomorrow\'s presentation from local chat.')}],
      [27, {candidate: row('CANDIDATE', data.candidate_reply, 'Not saved or displayed yet.')}],
      [28, {review: row('TYPED INPUT', `${user.id} + ${fact.value} v${fact.version}`, 'Prior user messages / entities; candidate reply excluded.')}],
      [30, {review: row('PROPOSED', `correct ${fact.fact_id} -> ${proposal.value}`, `Expected v${proposal.expected_version}; quote: "${proposal.evidence_quote}"`)}],
      [31, {embedding: row('FACT DOCUMENT', `${data.subject}: location ${proposal.value}`, 'Prepared for this proposed correction.')}],
      [33, {embedding: row('VECTOR READY', `Location: ${proposal.value}`, 'Illustrative only; no numeric vector is invented.')}],
      [34, {commit: row('PROPOSAL', correction, 'Not committed yet.')}],
      [36, {commit: row('PENDING', 'Reply + correction + vector', 'Recheck lease, cancellation, v1 and source.')}],
      [37, {commit: row('ATOMIC SUCCESS', `Location: ${proposal.value} v${fact.version + 1}`, 'Reply + fact + index + success saved together.'),
        candidate: row('CANDIDATE', data.candidate_reply, 'Same text saved at commit; not displayed yet.'),
        facts: row('COMMITTED', `Location: ${proposal.value} v${fact.version + 1}`, `Source: ${user.id}`),
        dialogue: row('SAVED REPLY', data.candidate_reply),
        runs: row('SUCCEEDED', data.run_id, 'Lease released; no new summary.')}],
      [38, {outcome: row('SUCCEEDED', data.run_id)}],
      [39, {chat: row('DISPLAYED', data.candidate_reply, 'Reloaded persisted reply; not candidate streaming.')}],
      [40, {lineage: row('CORRECTION', correction, `Source: ${user.id}, not assistant text.`)}],
      [41, {activity: row('PUBLIC STATUS', `${data.run_id}: succeeded`, 'Retained metadata is incomplete; not hidden reasoning.')}],
    ];

    const previews = [
      {
        input: [['Alex says', user.content]],
        output: [['Saved user', `${user.id}: exact original text`], ['Accepted run', `${data.run_id}: queued, then claimed; no assistant reply yet`]],
        note: 'Recording a statement does not automatically accept it as a fact.',
      },
      {
        input: [['Current user', user.content], ['Persona', `${persona}: ${data.persona.intent}`], ['Local chat', data.previous_user.content], ['Existing fact', `Location: ${fact.value} v${fact.version}`]],
        output: [['Conversation input', `${persona}; ${user.id}; "presentation tomorrow"; location ${fact.value} v${fact.version}.`]],
        note: `The current message says ${proposal.value}; the stored ${fact.value} fact has not been corrected yet. No general historical recall.`,
      },
      {
        input: [['Situation', 'Slides finished, no rehearsal; local chat says the talk is tomorrow.'], ['Intended character', data.persona.intent]],
        output: [['Candidate reply', data.candidate_reply]],
        note: 'One possible response, not a gold standard or measured output. Interpretation, choice and expression share generation; nothing is persisted yet.',
      },
      {
        input: [['User evidence', proposal.evidence_quote], ['Existing fact', `${fact.fact_id}: ${fact.value} v${fact.version}`]],
        output: [['Proposed correction', `${fact.fact_id}: ${proposal.value}; expected version ${proposal.expected_version}`], ['Representation', 'Prepare a vector for the proposed new value']],
        note: 'The typed reviewer also has prior user messages and entities, but NOT the candidate reply. A valid source does not prove correct interpretation.',
      },
      {
        input: [['Pending', 'Candidate reply + correction + prepared vector']],
        output: [['Same transaction', `${correction}; assistant reply; matching index; ${data.run_id}: succeeded`]],
        note: 'Outcome preview assumes all guards pass. No separate early reply/fact write and no new summary.',
      },
      {
        input: [['Persisted state', `${data.run_id}: succeeded; location ${proposal.value} v${fact.version + 1}`]],
        output: [['Reply Alex sees', data.candidate_reply], ['Lineage', `${correction}; attributed to ${user.id}`]],
        note: 'The displayed wording is the same committed candidate. Public activity is incomplete metadata, not hidden reasoning.',
      },
    ];

    function at(sourceBeat) {
      const values = {};
      for (const [when, changes] of timeline) if (when <= sourceBeat) Object.assign(values, changes);
      return values;
    }
    function decorate(figure) {
      return {...figure, title: `${figure.title} - Fictional worked example`, props: {...figure.props,
        steps: figure.props.steps.map(step => ({...step,
          flow: step.flow.map(beat => ({...beat, show: {...beat.show,
            ...Object.fromEntries(Object.entries(at(beat.sourceBeat)).filter(([id]) => step.nodes.includes(id))),
          }})),
        })),
      }};
    }
    return {data, timeline, previews, at, decorate};
  }

  function render(root, example, chapter) {
    const panel = root.querySelector('[data-example]');
    panel.hidden = chapter == null;
    if (chapter == null || panel.dataset.chapter === String(chapter)) return;
    panel.dataset.chapter = String(chapter);
    root.querySelector('[data-example-caption]').textContent = example.data.caption;
    const preview = example.previews[chapter];
    for (const side of ['input', 'output']) {
      const target = root.querySelector(`[data-example-${side}]`);
      target.replaceChildren();
      for (const [label, value] of preview[side]) {
        const term = document.createElement('dt'), description = document.createElement('dd');
        term.textContent = label; description.textContent = value;
        target.append(term, description);
      }
    }
    root.querySelector('[data-example-note]').textContent = preview.note;
  }

  global.AdeJourneyExample = {create, render};
})(globalThis);
