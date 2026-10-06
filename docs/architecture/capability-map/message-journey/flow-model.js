/* Edge routing adapted from Vectorize interfig, MIT. See THIRD_PARTY_NOTICES.md. */
(function (global) {
  'use strict';
  const centerX = rect => rect.x + rect.w / 2;
  const centerY = rect => rect.y + rect.h / 2;

  function route(edges, rects) {
    const picks = [];
    for (const edge of edges) {
      const a = rects[edge.from], b = rects[edge.to];
      if (!a || !b) continue;
      const stacked = a.x < b.x + b.w && b.x < a.x + a.w;
      const [sa, sb] = edge.around
        ? edge.around === 'above' ? ['t', 't'] : ['b', 'b']
        : stacked ? a.y < b.y ? ['b', 't'] : ['t', 'b']
          : a.x < b.x ? ['r', 'l'] : ['l', 'r'];
      picks.push({...edge, a, b, sa, sb});
    }
    const ends = new Map(), anchors = new Map();
    for (const pick of picks) {
      for (const start of [true, false]) {
        const key = `${start ? pick.from : pick.to}:${start ? pick.sa : pick.sb}`;
        if (!ends.has(key)) ends.set(key, []);
        ends.get(key).push({pick, start});
      }
    }
    for (const list of ends.values()) {
      const side = list[0].start ? list[0].pick.sa : list[0].pick.sb;
      const horizontal = side === 't' || side === 'b';
      const other = end => horizontal ? centerX(end.start ? end.pick.b : end.pick.a)
        : centerY(end.start ? end.pick.b : end.pick.a);
      list.sort((a, b) => other(a) - other(b));
      list.forEach((end, index) => {
        const rect = end.start ? end.pick.a : end.pick.b;
        const fraction = (index + 1) / (list.length + 1);
        const point = side === 'l' ? {x: rect.x, y: rect.y + rect.h * fraction}
          : side === 'r' ? {x: rect.x + rect.w, y: rect.y + rect.h * fraction}
            : side === 't' ? {x: rect.x + rect.w * fraction, y: rect.y}
              : {x: rect.x + rect.w * fraction, y: rect.y + rect.h};
        anchors.set(`${end.pick.id}:${end.start ? 's' : 'e'}`, point);
      });
    }
    return picks.map(pick => {
      const start = anchors.get(`${pick.id}:s`), end = anchors.get(`${pick.id}:e`);
      let first, second;
      if (pick.around) {
        const y = pick.around === 'above' ? Math.min(pick.a.y, pick.b.y) - 50
          : Math.max(pick.a.y + pick.a.h, pick.b.y + pick.b.h) + 50;
        first = {x: start.x, y}; second = {x: end.x, y};
      } else {
        const horizontal = pick.sa === 'l' || pick.sa === 'r';
        const distance = Math.abs(horizontal ? end.x - start.x : end.y - start.y) / 2;
        const sign = pick.sa === 'r' || pick.sa === 'b' ? 1 : -1;
        first = horizontal ? {x: start.x + sign * distance, y: start.y}
          : {x: start.x, y: start.y + sign * distance};
        second = horizontal ? {x: end.x - sign * distance, y: end.y}
          : {x: end.x, y: end.y - sign * distance};
      }
      return {
        ...pick, start, first, second, end,
        d: `M ${start.x} ${start.y} C ${first.x} ${first.y}, ${second.x} ${second.y}, ${end.x} ${end.y}`,
      };
    });
  }

  function pointAt(curve, fraction) {
    const t = Math.max(0, Math.min(1, fraction)), s = 1 - t;
    if (curve.polyline) {
      let distance = t * curve.length;
      for (let index = 1; index < curve.polyline.length; index += 1) {
        const a = curve.polyline[index - 1], b = curve.polyline[index];
        const length = Math.hypot(b.x - a.x, b.y - a.y);
        if (distance <= length || index === curve.polyline.length - 1) {
          const ratio = length ? Math.min(1, distance / length) : 0;
          return {x: a.x + (b.x - a.x) * ratio, y: a.y + (b.y - a.y) * ratio};
        }
        distance -= length;
      }
    }
    const coordinate = key => s ** 3 * curve.start[key] + 3 * s ** 2 * t * curve.first[key]
      + 3 * s * t ** 2 * curve.second[key] + t ** 3 * curve.end[key];
    return {x: coordinate('x'), y: coordinate('y')};
  }

  function inside(point, rect, padding = 0) {
    return point.x > rect.x - padding && point.x < rect.x + rect.w + padding
      && point.y > rect.y - padding && point.y < rect.y + rect.h + padding;
  }

  // Interfig's simple curves may cross cards. Only obstructed active transfers
  // use a Manhattan visibility grid, keeping packets out of unrelated labels.
  function avoidCards(curve, rects) {
    const obstacles = Object.values(rects);
    const intervening = Object.entries(rects).filter(([id]) => id !== curve.from && id !== curve.to).map(([, rect]) => rect);
    const obstructed = Array.from({length: 81}, (_, index) => pointAt(curve, index / 80))
      .some(point => intervening.some(rect => inside(point, rect, 6)));
    if (!obstructed) return curve;
    const offset = (point, side) => ({
      x: point.x + (side === 'l' ? -12 : side === 'r' ? 12 : 0),
      y: point.y + (side === 't' ? -12 : side === 'b' ? 12 : 0),
    });
    const start = offset(curve.start, curve.sa), end = offset(curve.end, curve.sb);
    const sorted = values => [...new Set(values)].sort((a, b) => a - b);
    const xs = sorted([start.x, end.x, ...obstacles.flatMap(rect => [rect.x - 12, rect.x + rect.w + 12])]);
    const ys = sorted([start.y, end.y, ...obstacles.flatMap(rect => [rect.y - 12, rect.y + rect.h + 12])]);
    const width = xs.length;
    const key = (x, y) => y * width + x;
    const point = identity => ({x: xs[identity % width], y: ys[Math.floor(identity / width)]});
    const begin = key(xs.indexOf(start.x), ys.indexOf(start.y)), finish = key(xs.indexOf(end.x), ys.indexOf(end.y));
    const costs = new Map([[begin, 0]]), previous = new Map(), open = new Set([begin]);
    const clear = (a, b) => !obstacles.some(rect => {
      if (a.x === b.x) return a.x > rect.x - 6 && a.x < rect.x + rect.w + 6
        && Math.max(a.y, b.y) > rect.y - 6 && Math.min(a.y, b.y) < rect.y + rect.h + 6;
      return a.y > rect.y - 6 && a.y < rect.y + rect.h + 6
        && Math.max(a.x, b.x) > rect.x - 6 && Math.min(a.x, b.x) < rect.x + rect.w + 6;
    });
    const estimate = identity => { const p = point(identity); return costs.get(identity) + Math.abs(p.x - end.x) + Math.abs(p.y - end.y); };
    while (open.size) {
      let current;
      for (const candidate of open) if (current == null || estimate(candidate) < estimate(current)) current = candidate;
      if (current === finish) break;
      open.delete(current);
      const x = current % width, y = Math.floor(current / width), a = point(current);
      for (const [nx, ny] of [[x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]]) {
        if (nx < 0 || nx >= width || ny < 0 || ny >= ys.length) continue;
        const neighbor = key(nx, ny), b = point(neighbor);
        if (!clear(a, b)) continue;
        const cost = costs.get(current) + Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
        if (cost < (costs.get(neighbor) ?? Infinity)) {
          costs.set(neighbor, cost); previous.set(neighbor, current); open.add(neighbor);
        }
      }
    }
    if (!costs.has(finish)) return curve;
    const chain = [finish];
    while (chain[0] !== begin) chain.unshift(previous.get(chain[0]));
    const points = [curve.start, ...chain.map(point), curve.end];
    const polyline = points.filter((p, index) => {
      const before = points[index - 1], after = points[index + 1];
      return !before || !after || !(before.x === p.x && p.x === after.x || before.y === p.y && p.y === after.y);
    });
    const length = polyline.slice(1).reduce((sum, p, index) => sum + Math.hypot(p.x - polyline[index].x, p.y - polyline[index].y), 0);
    return {...curve, polyline, length, d: polyline.map((p, index) => `${index ? 'L' : 'M'} ${p.x} ${p.y}`).join(' ')};
  }

  function beatHops(beat) {
    const values = beat.edges == null ? [] : Array.isArray(beat.edges) ? beat.edges : [beat.edges];
    return values.map(value => typeof value === 'string' ? {edge: value} : value);
  }

  function flatten(group) {
    return group.children.flatMap(child => child.children ? flatten(child) : [child]);
  }

  function wrap(text, capacity) {
    const lines = [''];
    for (const word of String(text).split(/\s+/)) {
      const last = lines.length - 1;
      if (lines[last] && lines[last].length + word.length + 1 > capacity) lines.push(word);
      else lines[last] += `${lines[last] ? ' ' : ''}${word}`;
    }
    return lines;
  }

  function project(group, wanted) {
    const children = group.children.flatMap(child => {
      if (!child.children) return wanted.has(child.id) ? [child] : [];
      const selected = project(child, wanted);
      return selected.children.length ? [selected] : [];
    });
    return {...group, children};
  }

  function accumulated(step, index) {
    return Object.assign({}, ...step.flow.slice(0, index + 1).map(beat => beat.show || {}));
  }

  function narration(step, index) {
    return step.flow.slice(0, index + 1).findLast(beat => beat.say)?.say || step.caption || '';
  }

  // Fixed maximum card sizes prevent payload arrival from moving packet endpoints.
  function cardSizes(steps) {
    const sizes = new Map();
    for (const beat of steps.flatMap(step => step.flow)) {
      for (const [id, content] of Object.entries(beat.show || {})) {
        const rows = Array.isArray(content) ? content : [{text: content}];
        const count = rows.reduce((total, row) => total + wrap(row.text, 29).length + 1, 0);
        sizes.set(id, Math.max(sizes.get(id) || 0, count * 16 + 18));
      }
    }
    return sizes;
  }

  function layout(group, steps, narrow = false, maximumWidth = Infinity) {
    const sizes = cardSizes(steps), rects = {}, frames = [], cards = [];
    function measure(item, available) {
      if (!item.children) {
        const width = Math.max(150, Math.min(Math.max(225, item.width || 225), available));
        const label = wrap(item.label, Math.floor((width - 28) / 7));
        const sub = wrap(item.sub || '', Math.floor((width - 28) / 6.3));
        const height = 25 + label.length * 18 + sub.length * 16 + (sizes.get(item.id) || 0) + 12
          + (item.shape === 'store' ? 18 : 0);
        return {item, w: width, h: height, label, sub};
      }
      const framed = Boolean(item.label);
      const direction = narrow ? 'column' : item.direction || 'column';
      const gap = Math.max(18, item.gap || 18), padding = framed ? 18 : 0;
      const inner = available - padding * 2;
      const children = item.children.map(child => measure(child, inner));
      const row = direction === 'row';
      const rows = [];
      for (const child of children) {
        let line = rows.at(-1);
        if (!line || !row || line.w + gap + child.w > inner) {
          line = {children: [], w: 0, h: 0}; rows.push(line);
        }
        line.w += child.w + (line.children.length ? gap : 0);
        line.h = Math.max(line.h, child.h); line.children.push(child);
      }
      const w = Math.max(0, ...rows.map(line => line.w)) + padding * 2;
      const title = framed ? wrap(item.label, Math.max(15, Math.min(70, Math.floor((w - padding * 2) / 6.8)))) : [];
      const heading = title.length ? title.length * 18 + 22 : 0;
      const h = rows.reduce((sum, line) => sum + line.h, 0)
        + gap * Math.max(0, rows.length - 1) + padding * 2 + heading;
      return {item, children, rows, w, h, direction, padding, heading, gap, title};
    }
    function place(plan, x, y) {
      if (!plan.children) {
        const rect = {x, y, w: plan.w, h: plan.h};
        rects[plan.item.id] = rect;
        cards.push({...plan, ...rect});
        return;
      }
      if (plan.item.label) frames.push({...plan, x, y});
      let dy = y + plan.padding + plan.heading;
      for (const row of plan.rows) {
        let dx = x + plan.padding;
        for (const child of row.children) {
          place(child, dx, dy); dx += child.w + plan.gap;
        }
        dy += row.h + plan.gap;
      }
    }
    const margin = Number.isFinite(maximumWidth) ? 14 : 62;
    const measured = measure(group, maximumWidth - margin * 2);
    place(measured, margin, 62);
    return {w: measured.w + margin * 2, h: measured.h + 124, rects, frames, cards};
  }

  global.AdeFlowModel = {route, pointAt, avoidCards, beatHops, flatten, wrap, project, accumulated, narration, layout};
})(globalThis);
