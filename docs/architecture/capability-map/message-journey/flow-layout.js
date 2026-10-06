/* Presentation sizing follows interfig's fixed, maximum-content card approach. */
(function (global) {
  'use strict';
  const model = global.AdeFlowModel;

  function subtitle(item) {
    const identity = (item.sub || '').match(/^(?:L3 - )?(?:[A-Z]+-[A-Z0-9]+)(?: \+ [A-Z]+-[A-Z0-9]+)?/);
    const statuses = [...(item.sub || '').matchAll(/\[([^\]]+)\]/g)].map(match => match[1]);
    return [identity?.[0], statuses.join(' / ')].filter(Boolean).join(' | ');
  }

  function rows(content, width) {
    const values = Array.isArray(content) ? content : [{text: content ?? '-', muted: content == null}];
    const capacity = Math.max(14, Math.floor((width - 20) / 6.7));
    return values.map(row => ({...row, lines: model.wrap(row.text, capacity),
      metadata: row.meta == null ? [] : model.wrap(row.meta, capacity),
    }));
  }

  function payloadHeight(content, width) {
    return rows(content, width).reduce((sum, row) => sum + (row.tag ? 18 : 0)
      + (row.lines.length + row.metadata.length) * 16 + 5, 12);
  }

  function layout(group, steps, narrow = false, maximumWidth = Infinity) {
    const contents = new Map();
    for (const beat of steps.flatMap(step => step.flow)) {
      for (const [id, content] of Object.entries(beat.show || {})) {
        if (!contents.has(id)) contents.set(id, []);
        contents.get(id).push(content);
      }
    }
    const rects = {}, frames = [], cards = [];
    function measure(item, available) {
      if (!item.children) {
        const w = Math.max(148, Math.min(item.shape === 'store' ? 220 : 195, available));
        const label = model.wrap(item.label, Math.floor((w - 24) / 7));
        const sub = model.wrap(subtitle(item), Math.floor((w - 24) / 6.4));
        const payload = contents.has(item.id) ? Math.max((item.lines || 1) * 16 + 12,
          ...contents.get(item.id).map(content => payloadHeight(content, w - 20))) : 0;
        const top = item.shape === 'store' ? 36 : 22;
        const payloadY = top + label.length * 18 + sub.length * 16 + 10;
        const h = payloadY + payload + (payload ? 12 : 4);
        return {item, w, h, label, sub, payload, payloadY};
      }
      const framed = Boolean(item.label), padding = framed ? 18 : 0;
      const direction = narrow ? 'column' : item.direction || 'column';
      const gap = item.id === 'ownership' ? 36 : Math.max(18, item.gap || 22);
      const inner = available - padding * 2;
      const children = item.children.map(child => measure(child, inner));
      const lines = [];
      for (const child of children) {
        let line = lines.at(-1);
        if (!line || direction !== 'row' || line.w + gap + child.w > inner) {
          line = {children: [], w: 0, h: 0}; lines.push(line);
        }
        line.w += child.w + (line.children.length ? gap : 0);
        line.h = Math.max(line.h, child.h); line.children.push(child);
      }
      const w = Math.max(0, ...lines.map(line => line.w)) + padding * 2;
      const title = framed ? model.wrap(item.label.toUpperCase(), Math.max(16,
        Math.floor((w - padding * 2) / 6.8))) : [];
      const heading = title.length ? title.length * 18 + 12 : 0;
      const h = lines.reduce((sum, line) => sum + line.h, 0)
        + gap * Math.max(0, lines.length - 1) + padding * 2 + heading;
      return {item, children, lines, w, h, padding, heading, gap, title};
    }
    function place(plan, x, y) {
      if (!plan.children) {
        const rect = {x, y, w: plan.w, h: plan.h};
        rects[plan.item.id] = rect; cards.push({...plan, ...rect}); return;
      }
      if (plan.item.label) frames.push({...plan, x, y});
      let dy = y + plan.padding + plan.heading;
      for (const line of plan.lines) {
        let dx = x + plan.padding;
        for (const child of line.children) {
          place(child, dx, dy); dx += child.w + plan.gap;
        }
        dy += line.h + plan.gap;
      }
    }
    const margin = Number.isFinite(maximumWidth) ? 14 : 58;
    const measured = measure(group, maximumWidth - margin * 2);
    place(measured, margin, 58);
    const headings = Object.fromEntries(frames.map(frame => [`@heading:${frame.item.id}`, {
      x: frame.x + 18, y: frame.y + 18,
      w: Math.min(frame.w - 36, Math.max(...frame.title.map(line => line.length)) * 6.8),
      h: 14 + (frame.title.length - 1) * 18, text: true,
    }]));
    return {w: measured.w + margin * 2, h: measured.h + 116, rects, frames, cards, obstacles: {...rects, ...headings}};
  }
  global.AdeFlowLayout = {layout, rows, subtitle};
})(globalThis);
