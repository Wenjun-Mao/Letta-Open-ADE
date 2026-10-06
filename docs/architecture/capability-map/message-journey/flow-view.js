(function (global) {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const model = global.AdeFlowModel;

  function element(tag, attributes = {}, text) {
    const node = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    if (text != null) node.textContent = text;
    return node;
  }

  function textLines(parent, lines, x, y, className, height = 16) {
    const text = element('text', {x, y, class: className});
    lines.forEach((line, index) => text.appendChild(element('tspan', {x, dy: index ? height : 0}, line)));
    parent.appendChild(text);
  }

  function create(root, figure) {
    const viewport = root.querySelector('[data-viewport]');
    const standalone = root.hasAttribute('data-standalone');
    if (standalone) viewport.tabIndex = 0;
    const data = figure.props;
    const nodes = new Map(model.flatten(data.layout).map(node => [node.id, node]));
    const edgeMap = new Map(data.edges.map(edge => [edge.id, edge]));
    let packets = [], curves = new Map(), follow = false, bounds;

    function render(state) {
      const step = data.steps[state.tour], beat = step.flow[state.beat];
      const hops = model.beatHops(beat), activeEdges = hops.map(hop => edgeMap.get(hop.edge));
      const wanted = new Set([...(beat.light || []), ...activeEdges.flatMap(edge => [edge.from, edge.to])]);
      const projection = state.whole ? data.layout : model.project(data.layout, wanted);
      const narrow = viewport.clientWidth < 600 && !(standalone && state.whole);
      const maximumWidth = standalone && state.whole ? Infinity : Math.max(296, viewport.clientWidth);
      const plan = model.layout(projection, data.steps, narrow, maximumWidth);
      bounds = plan; follow = standalone && state.playing && !state.whole;
      const svg = element('svg', {
        viewBox: `0 0 ${plan.w} ${plan.h}`, width: plan.w, height: plan.h,
        class: 'journey-drawing', role: 'img', 'aria-label': `${step.label}, step ${state.beat + 1}`,
      });
      svg.appendChild(element('title', {}, `${figure.title} - ${step.label}`));
      svg.appendChild(element('desc', {}, model.narration(step, state.beat)));
      const defs = element('defs');
      for (const [id, className] of [['journey-arrow', 'active-arrow'], ['journey-trail-arrow', 'trail-arrow']]) {
        const marker = element('marker', {id, markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: 'auto'});
        marker.appendChild(element('path', {d: 'M 0 0 L 8 4 L 0 8 Z', class: className}));
        defs.appendChild(marker);
      }
      svg.appendChild(defs);
      for (const frame of plan.frames) {
        const group = element('g', {'data-group': frame.item.id});
        group.appendChild(element('rect', {
          x: frame.x, y: frame.y, width: frame.w, height: frame.h, rx: 14,
          class: `ownership-frame ${frame.item.label.startsWith('L1') ? 'domain-frame' : ''}`,
        }));
        textLines(group, frame.title, frame.x + 18, frame.y + 32, 'frame-title', 18);
        svg.appendChild(group);
      }
      const trail = new Set(step.flow.slice(0, state.beat).flatMap(item => model.beatHops(item).map(hop => hop.edge)));
      const visible = state.whole ? data.edges.filter(edge => !edge.quiet || trail.has(edge.id) || hops.some(hop => hop.edge === edge.id)) : activeEdges;
      const activeIds = new Set(hops.map(hop => hop.edge));
      const routed = model.route(visible, plan.rects).map(curve => activeIds.has(curve.id) ? model.avoidCards(curve, plan.rects) : curve);
      curves = new Map(routed.map(curve => [curve.id, curve]));
      for (const curve of routed) {
        const active = hops.some(hop => hop.edge === curve.id);
        svg.appendChild(element('path', {
          d: curve.d, class: active ? 'connection active-connection' : 'connection trail-connection',
          'marker-end': `url(#${active ? 'journey-arrow' : 'journey-trail-arrow'})`,
          'data-edge': curve.id,
        }));
      }
      const shown = model.accumulated(step, state.beat);
      for (const card of plan.cards) {
        const active = wanted.has(card.item.id);
        const deferred = card.item.sub.includes('[Deferred]');
        const group = element('g', {
          'data-node': card.item.id, class: `flow-node${active ? ' is-active' : ''}${deferred ? ' is-deferred' : ''}`,
        });
        group.appendChild(element('title', {}, `${card.item.label}. ${card.item.sub}`));
        if (card.item.shape === 'store') {
          const {x, y, w, h} = card;
          group.appendChild(element('path', {
            d: `M ${x} ${y + 12} C ${x} ${y - 4}, ${x + w} ${y - 4}, ${x + w} ${y + 12} L ${x + w} ${y + h - 12} C ${x + w} ${y + h + 4}, ${x} ${y + h + 4}, ${x} ${y + h - 12} Z`,
            class: 'node-surface',
          }));
          group.appendChild(element('path', {
            d: `M ${x} ${y + 12} C ${x} ${y + 28}, ${x + w} ${y + 28}, ${x + w} ${y + 12}`,
            class: 'store-rim',
          }));
        } else group.appendChild(element('rect', {
          x: card.x, y: card.y, width: card.w, height: card.h, rx: 10, class: 'node-surface',
        }));
        let y = card.y + (card.item.shape === 'store' ? 42 : 28);
        textLines(group, card.label, card.x + 14, y, 'node-label', 18);
        y += card.label.length * 18 + 6;
        textLines(group, card.sub, card.x + 14, y, 'node-sub', 16);
        y += card.sub.length * 16 + 10;
        if (shown[card.item.id] != null) {
          const rows = Array.isArray(shown[card.item.id]) ? shown[card.item.id] : [{text: shown[card.item.id]}];
          for (const row of rows) {
            if (row.tag) {
              textLines(group, [row.tag], card.x + 14, y, 'payload-tag'); y += 16;
            }
            const lines = model.wrap(row.text, 29);
            textLines(group, lines, card.x + 14, y, 'payload-text');
            y += lines.length * 16;
          }
        }
        svg.appendChild(group);
      }
      packets = hops.map(hop => {
        const packet = element('g', {'data-packet': hop.edge, class: 'message-packet'});
        packet.appendChild(element('circle', {r: 9, class: 'packet-halo'}));
        packet.appendChild(element('circle', {r: 4, class: 'packet-core'}));
        svg.appendChild(packet);
        return {packet, hop};
      });
      viewport.replaceChildren(svg);
      viewport.dataset.view = state.whole ? 'whole' : 'message';
      root.querySelector('[data-connections]').textContent = activeEdges.map(edge => {
        const label = nodes.get(edge.from).label, target = nodes.get(edge.to).label;
        return `${label} -> ${target}: ${edge.label}`;
      }).join(' | ') || 'No transfer in this step';
      position(state.playing ? 0 : 0.5);
      return {width: plan.w, height: plan.h};
    }

    function position(fraction) {
      const eased = fraction < 0.5 ? 2 * fraction * fraction : 1 - (-2 * fraction + 2) ** 2 / 2;
      const positions = [];
      for (const {packet, hop} of packets) {
        const curve = curves.get(hop.edge);
        if (!curve) continue;
        const point = model.pointAt(curve, hop.back ? 1 - eased : eased);
        packet.setAttribute('transform', `translate(${point.x} ${point.y})`);
        positions.push(point);
      }
      if (follow && positions.length && viewport.clientHeight > 0) {
        const center = positions.reduce((sum, point) => ({x: sum.x + point.x / positions.length, y: sum.y + point.y / positions.length}), {x: 0, y: 0});
        viewport.scrollTop = Math.max(0, Math.min(bounds.h - viewport.clientHeight, center.y - viewport.clientHeight / 2));
        viewport.scrollLeft = Math.max(0, Math.min(bounds.w - viewport.clientWidth, center.x - viewport.clientWidth / 2));
      }
    }
    return {render, position};
  }
  global.AdeFlowView = {create};
})(globalThis);
