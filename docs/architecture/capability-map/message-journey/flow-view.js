/* SVG/DOM presentation adapted from interfig. See THIRD_PARTY_NOTICES.md. */
(function (global) {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const model = global.AdeFlowModel, layout = global.AdeFlowLayout;

  function element(tag, attributes = {}, text) {
    const node = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    if (text != null) node.textContent = text;
    return node;
  }

  function textLines(parent, lines, x, y, className, height = 16, centered = false) {
    const text = element('text', {x, y, class: className, 'text-anchor': centered ? 'middle' : 'start'});
    lines.forEach((line, index) => text.appendChild(element('tspan', {x, dy: index ? height : 0}, line)));
    parent.appendChild(text);
  }

  function drawCard(card, content, active, current) {
    const {x, y, w, h, item} = card;
    const group = element('g', {
      'data-node': item.id,
      class: `flow-node${active ? ' is-active' : ''}${current ? ' is-current' : ''}${item.sub.includes('[Deferred]') ? ' is-deferred' : ''}`,
    });
    group.appendChild(element('title', {}, `${item.label}. ${item.sub}`));
    if (item.shape === 'store') {
      group.appendChild(element('path', {
        d: `M ${x} ${y + 12} C ${x} ${y - 4}, ${x + w} ${y - 4}, ${x + w} ${y + 12} L ${x + w} ${y + h - 12} C ${x + w} ${y + h + 4}, ${x} ${y + h + 4}, ${x} ${y + h - 12} Z`,
        class: 'node-surface',
      }));
      group.appendChild(element('ellipse', {cx: x + w / 2, cy: y + 12, rx: w / 2, ry: 12, class: 'store-rim'}));
    } else group.appendChild(element('rect', {x, y, width: w, height: h, rx: 10, class: 'node-surface'}));
    const labelY = y + (item.shape === 'store' ? 40 : 25);
    textLines(group, card.label, x + w / 2, labelY, 'node-label', 18, true);
    textLines(group, card.sub, x + w / 2, labelY + card.label.length * 18 + 2, 'node-sub', 16, true);
    if (card.payload) {
      const insetY = y + card.payloadY;
      const inset = element('g', {class: `payload${content == null ? ' is-empty' : ' is-filled'}`, 'data-payload': item.id});
      inset.appendChild(element('rect', {x: x + 10, y: insetY, width: w - 20, height: card.payload, rx: 6, class: 'payload-surface'}));
      let lineY = insetY + 20;
      for (const row of layout.rows(content, w - 20)) {
        if (row.tag) {
          const tagWidth = Math.min(w - 40, row.tag.length * 6.6 + 10);
          inset.appendChild(element('rect', {x: x + 18, y: lineY - 12, width: tagWidth, height: 16, rx: 4, class: 'payload-badge'}));
          textLines(inset, [row.tag], x + 23, lineY, 'payload-tag'); lineY += 18;
        }
        textLines(inset, row.lines, x + 18, lineY, `payload-text${row.mono ? ' is-mono' : ''}`);
        lineY += row.lines.length * 16;
        if (row.metadata.length) {
          textLines(inset, row.metadata, x + 18, lineY, 'payload-meta'); lineY += row.metadata.length * 16;
        }
        lineY += 5;
      }
      group.appendChild(inset);
    }
    return group;
  }

  function edgeLabel(curve, label, plan, taken) {
    const lines = model.wrap(label, 34), w = Math.min(258, Math.max(...lines.map(line => line.length)) * 6.7 + 16);
    const h = lines.length * 16 + 6;
    for (const fraction of [0.5, 0.3, 0.7, 0.2, 0.8]) {
      const p = model.pointAt(curve, fraction), box = {x: p.x - w / 2, y: p.y - h / 2, w, h};
      if (box.x < 4 || box.y < 4 || box.x + w > plan.w - 4 || box.y + h > plan.h - 4) continue;
      const overlap = other => box.x < other.x + other.w && box.x + w > other.x && box.y < other.y + other.h && box.y + h > other.y;
      if ([...Object.values(plan.obstacles), ...taken].some(overlap)) continue;
      taken.push(box);
      const group = element('g', {class: 'edge-label', 'data-edge-label': curve.id});
      group.appendChild(element('rect', {x: box.x, y: box.y, width: w, height: h, rx: 9}));
      textLines(group, lines, p.x, box.y + 15, 'edge-label-text', 16, true);
      return group;
    }
    return null;
  }

  function create(root, figure) {
    const viewport = root.querySelector('[data-viewport]');
    const standalone = root.hasAttribute('data-standalone'), data = figure.props;
    if (standalone) viewport.tabIndex = 0;
    const nodes = new Map(model.flatten(data.layout).map(node => [node.id, node]));
    const edgeMap = new Map(data.edges.map(edge => [edge.id, edge]));
    let packets = [], curves = new Map(), cacheKey = '', plan, routes;

    function render(state) {
      const step = data.steps[state.tour], beat = step.flow[state.beat];
      const hops = model.beatHops(beat), activeEdges = hops.map(hop => edgeMap.get(hop.edge));
      const wanted = new Set([...(beat.light || []), ...activeEdges.flatMap(edge => [edge.from, edge.to])]);
      const key = `${state.whole}:${state.whole ? '' : [...wanted].sort().join(',')}:${viewport.clientWidth}`;
      if (key !== cacheKey) {
        const projection = state.whole ? data.layout : model.project(data.layout, wanted);
        const unbounded = standalone && state.whole;
        plan = layout.layout(projection, data.steps, !unbounded && viewport.clientWidth < 600,
          unbounded ? Infinity : Math.max(296, viewport.clientWidth));
        // All ports and fallback routes are stable across beats, including quiet edges.
        routes = model.route(data.edges, plan.rects).map(curve => model.avoidCards(curve, plan.obstacles));
        cacheKey = key;
      }
      const scale = standalone && state.whole ? Math.max(0.75, Math.min(1, viewport.clientWidth / plan.w)) : 1;
      const svg = element('svg', {
        viewBox: `0 0 ${plan.w} ${plan.h}`, width: plan.w * scale, height: plan.h * scale,
        class: 'journey-drawing', role: 'img', 'aria-label': `${step.label}, step ${state.beat + 1}`,
      });
      svg.appendChild(element('title', {}, `${figure.title} - ${step.label}`));
      svg.appendChild(element('desc', {}, model.narration(step, state.beat)));
      const defs = element('defs');
      for (const [id, className] of [['journey-arrow', 'active-arrow'], ['journey-trail-arrow', 'trail-arrow']]) {
        const marker = element('marker', {id, markerWidth: 5, markerHeight: 5, refX: 9, refY: 5, viewBox: '0 0 10 10', orient: 'auto'});
        marker.appendChild(element('path', {d: 'M 0 1 L 9 5 L 0 9 Z', class: className})); defs.appendChild(marker);
      }
      svg.appendChild(defs);
      for (const frame of plan.frames) {
        const group = element('g', {'data-group': frame.item.id});
        group.appendChild(element('rect', {x: frame.x, y: frame.y, width: frame.w, height: frame.h, rx: 14,
          class: `ownership-frame${frame.item.label.includes('[Deferred]') ? ' deferred-frame' : ''}`}));
        textLines(group, frame.title, frame.x + 18, frame.y + 29, 'frame-title', 18); svg.appendChild(group);
      }
      const trail = new Set(step.flow.slice(0, state.beat + 1).flatMap(item => model.beatHops(item).map(hop => hop.edge)));
      const lit = new Set([...wanted, ...Object.keys(model.accumulated(step, state.beat)), ...(step.nodes || [])]);
      for (const id of trail) { const edge = edgeMap.get(id); lit.add(edge.from).add(edge.to); }
      const visible = routes.filter(curve => state.whole ? !curve.quiet || trail.has(curve.id) : hops.some(hop => hop.edge === curve.id));
      curves = new Map(visible.map(curve => [curve.id, curve]));
      for (const curve of visible) {
        const active = trail.has(curve.id);
        svg.appendChild(element('path', {d: curve.d,
          class: `connection ${active ? 'active-connection' : 'trail-connection'}`,
          'marker-end': `url(#${active ? 'journey-arrow' : 'journey-trail-arrow'})`, 'data-edge': curve.id}));
      }
      const shown = model.accumulated(step, state.beat);
      for (const card of plan.cards) svg.appendChild(drawCard(card, shown[card.item.id], lit.has(card.item.id), wanted.has(card.item.id)));
      const taken = [];
      for (const hop of hops) {
        const curve = curves.get(hop.edge);
        if (!curve) continue;
        const label = edgeLabel(curve, edgeMap.get(hop.edge).label, plan, taken);
        if (label) svg.appendChild(label);
      }
      packets = hops.map(hop => {
        const packet = element('g', {'data-packet': hop.edge, class: 'message-packet'});
        packet.appendChild(element('circle', {r: 10, class: 'packet-halo'}));
        packet.appendChild(element('circle', {r: 4.5, class: 'packet-core'}));
        let chip, chipWidth, chipHeight;
        if (hop.data != null) {
          chip = element('g', {class: 'packet-data', 'data-packet-data': hop.edge});
          const lines = model.wrap(hop.data, 26), w = Math.max(...lines.map(line => line.length)) * 6.7 + 16;
          chipWidth = w; chipHeight = lines.length * 16 + 8;
          chip.appendChild(element('rect', {x: -w / 2, y: -lines.length * 16 - 18, width: w, height: lines.length * 16 + 8, rx: 6}));
          textLines(chip, lines, 0, -lines.length * 16 - 3, 'edge-label-text', 16, true);
          packet.appendChild(chip);
        }
        svg.appendChild(packet); return {packet, hop, chip, chipWidth, chipHeight};
      });
      viewport.replaceChildren(svg); viewport.dataset.view = state.whole ? 'whole' : 'message';
      root.querySelector('[data-connections]').textContent = activeEdges.map(edge =>
        `${nodes.get(edge.from).label} -> ${nodes.get(edge.to).label}: ${edge.label}`).join(' | ') || 'No transfer in this step';
      position(state.playing ? 0 : 0.5);
      return {width: plan.w, height: plan.h};
    }

    function position(fraction) {
      const eased = fraction < 0.5 ? 2 * fraction * fraction : 1 - (-2 * fraction + 2) ** 2 / 2;
      for (const {packet, hop, chip, chipWidth, chipHeight} of packets) {
        const curve = curves.get(hop.edge);
        if (!curve) continue;
        const point = model.pointAt(curve, hop.back ? 1 - eased : eased);
        packet.setAttribute('transform', `translate(${point.x} ${point.y})`);
        if (chip) {
          const x = Math.max(chipWidth / 2 + 4, Math.min(plan.w - chipWidth / 2 - 4, point.x));
          const box = {x: x - chipWidth / 2, y: point.y - chipHeight - 10, w: chipWidth, h: chipHeight};
          const obstructed = Object.values(plan.obstacles).some(rect => box.x < rect.x + rect.w
            && box.x + box.w > rect.x && box.y < rect.y + rect.h && box.y + box.h > rect.y);
          chip.setAttribute('transform', `translate(${x - point.x} 0)`);
          chip.style.opacity = fraction > 0.12 && fraction < 0.88 && box.y >= 0 && !obstructed ? '1' : '0';
        }
      }
    }
    return {render, position};
  }
  global.AdeFlowView = {create};
})(globalThis);
