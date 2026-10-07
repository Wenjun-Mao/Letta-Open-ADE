/* Reading chapters project the existing specification; they are not runtime stages. */
(function (global) {
  'use strict';
  const chapters = [
    {
      label: 'Accept message', start: 0, end: 7,
      nodes: ['chat', 'accept', 'capture', 'dialogue', 'runs', 'attempt'],
      say: 'ADE accepts your text, saves the original user message and pending run together, then a worker claims the run. The receipt is a run ID, not an assistant reply. The persona was authored and bound before this turn.',
    },
    {
      label: 'Assemble context', start: 8, end: 23,
      nodes: ['binding', 'attempt', 'scope', 'search', 'delivery', 'dispatch'],
      say: 'ADE reads the existing persona binding, local dialogue, any summary and subject facts, searches scoped facts, and fits the actual conversation request. This typed-policy example needs no new summary and does not retrieve historical exchanges.',
    },
    {
      label: 'Generate candidate', start: 24, end: 27,
      nodes: ['dispatch', 'behavior', 'candidate'],
      say: 'The character interprets, chooses and expresses a response in one generation call using the supplied persona and context. The result is only a candidate: it is not saved or shown to you yet. Character quality remains partial.',
    },
    {
      label: 'Review updates', start: 28, end: 35,
      nodes: ['attempt', 'review', 'embedding', 'commit'],
      say: 'One typed reviewer proposes factual changes using the current user message, up to eight prior user messages, facts and entities. It does NOT receive the candidate reply. This example prepares vectors for value-bearing changes before finalization; source validity is not semantic proof.',
    },
    {
      label: 'Validate and commit', start: 36, end: 38,
      nodes: ['candidate', 'commit', 'dialogue', 'outcome'],
      say: 'ADE rechecks cancellation, lease, versions and sources, then commits the assistant reply, permitted fact changes, representations and terminal success together. The dialogue arrow is one part of that atomic transaction, not a separate early write. No new summary is saved here.',
    },
    {
      label: 'Display reply', start: 39, end: 41,
      nodes: ['outcome', 'chat', 'facts', 'lineage', 'runs', 'activity'],
      say: 'The UI reloads the persisted reply, facts and lineage after success. Retained activity is incomplete metadata, not hidden reasoning or a full packet trace; some activity can appear earlier. The candidate was not streamed directly.',
    },
  ];

  function build(figure) {
    const model = global.AdeFlowModel;
    const edges = new Map(figure.props.edges.map(edge => [edge.id, edge]));
    const source = figure.props.steps[0];
    const steps = chapters.map(chapter => {
      const visible = new Set(chapter.nodes);
      const flow = source.flow.flatMap((beat, index) => {
        if (index < chapter.start || index > chapter.end) return [];
        const hops = model.beatHops(beat).filter(hop => {
          const edge = edges.get(hop.edge);
          return visible.has(edge.from) && visible.has(edge.to);
        });
        // Omitted provider mechanics remain inspectable in the detailed source tour.
        if (!hops.length) return [];
        return [{...beat, edges: hops,
          light: (beat.light || []).filter(id => visible.has(id)),
          show: Object.fromEntries(Object.entries(model.accumulated(source, index)).filter(([id]) => visible.has(id))),
          sourceBeat: index,
        }];
      });
      return {label: chapter.label, caption: source.caption, nodes: chapter.nodes, flow};
    });
    return {...figure, props: {...figure.props, steps}};
  }

  function layout(source, identities) {
    const entries = new Map();
    function walk(item, parents = []) {
      if (item.children) item.children.forEach(child => walk(child, [...parents, item]));
      else entries.set(item.id, {item, parents});
    }
    walk(source);
    const groups = new Map();
    for (const id of identities) {
      const {item, parents} = entries.get(id);
      const domain = parents.find(parent => parent.label?.startsWith('L1 - '));
      const subsystem = parents.find(parent => parent.label?.startsWith('L2 - '));
      const support = parents.find(parent => ['runtime-coordination', 'model-access'].includes(parent.id));
      const artifact = item.sub.includes('[Artifact]');
      const key = item.shape === 'store' ? 'guide-records' : artifact ? 'guide-artifacts' : subsystem?.id || support.id;
      const label = item.shape === 'store' ? 'Persisted records / ADE PostgreSQL'
        : artifact ? 'Transient outputs'
          : subsystem ? `${domain.label} / ${subsystem.label}` : support.label;
      // One combined ownership header replaces nested frames, not the underlying hierarchy.
      if (!groups.has(key)) groups.set(key, {id: key, label, direction: 'row', gap: 22, children: []});
      groups.get(key).children.push(item);
    }
    return {id: 'guided-reading', direction: 'row', gap: 28, children: [...groups.values()]};
  }

  global.AdeJourneyGuide = {chapters, build, layout};
})(globalThis);
