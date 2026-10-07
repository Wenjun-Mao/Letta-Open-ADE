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
      const aligned = a.y < b.y + b.h && b.y < a.y + a.h;
      const gapLeft = Math.min(a.x + a.w, b.x + b.w), gapRight = Math.max(a.x, b.x);
      const skipsCard = !stacked && aligned && Object.entries(rects).some(([id, rect]) =>
        id !== edge.from && id !== edge.to && rect.x < gapRight && rect.x + rect.w > gapLeft
        && rect.y < Math.min(a.y + a.h, b.y + b.h) && rect.y + rect.h > Math.max(a.y, b.y));
      // Horizontal bypasses share the lower side; direct links and authored return loops keep their ports.
      const around = edge.around || (skipsCard ? 'below' : undefined);
      const [sa, sb] = around
        ? around === 'above' ? ['t', 't'] : ['b', 'b']
        : stacked ? a.y < b.y ? ['b', 't'] : ['t', 'b']
          : a.x < b.x ? ['r', 'l'] : ['l', 'r'];
      picks.push({...edge, around, a, b, sa, sb});
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
    if (t === 0) return {...curve.start};
    if (t === 1) return {...curve.end};
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

  function roundedPath(points) {
    const samples = [points[0]], commands = [`M ${points[0].x} ${points[0].y}`];
    for (let index = 1; index < points.length - 1; index += 1) {
      const before = points[index - 1], corner = points[index], after = points[index + 1];
      const incoming = Math.hypot(corner.x - before.x, corner.y - before.y);
      const outgoing = Math.hypot(after.x - corner.x, after.y - corner.y);
      const radius = Math.min(8, incoming / 2, outgoing / 2);
      const enter = {x: corner.x + (before.x - corner.x) * radius / incoming,
        y: corner.y + (before.y - corner.y) * radius / incoming};
      const leave = {x: corner.x + (after.x - corner.x) * radius / outgoing,
        y: corner.y + (after.y - corner.y) * radius / outgoing};
      commands.push(`L ${enter.x} ${enter.y} Q ${corner.x} ${corner.y} ${leave.x} ${leave.y}`);
      samples.push(enter);
      for (let part = 1; part <= 12; part += 1) {
        const t = part / 12, s = 1 - t;
        samples.push({x: s * s * enter.x + 2 * s * t * corner.x + t * t * leave.x,
          y: s * s * enter.y + 2 * s * t * corner.y + t * t * leave.y});
      }
    }
    samples.push(points.at(-1)); commands.push(`L ${points.at(-1).x} ${points.at(-1).y}`);
    const length = samples.slice(1).reduce((sum, point, index) => sum + Math.hypot(point.x - samples[index].x, point.y - samples[index].y), 0);
    return {polyline: samples, length, d: commands.join(' ')};
  }

  // Interfig's simple curves may cross cards. Only obstructed active transfers
  // use a rounded visibility-grid route, keeping packets out of unrelated labels.
  function avoidCards(curve, rects) {
    const obstacles = Object.values(rects);
    const clearance = rect => rect.text ? 1 : 6;
    const intervening = Object.entries(rects).filter(([id]) => id !== curve.from && id !== curve.to).map(([, rect]) => rect);
    const obstructed = Array.from({length: 81}, (_, index) => pointAt(curve, index / 80))
      .some(point => intervening.some(rect => inside(point, rect, clearance(rect))));
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
      const padding = clearance(rect);
      if (a.x === b.x) return a.x > rect.x - padding && a.x < rect.x + rect.w + padding
        && Math.max(a.y, b.y) > rect.y - padding && Math.min(a.y, b.y) < rect.y + rect.h + padding;
      return a.y > rect.y - padding && a.y < rect.y + rect.h + padding
        && Math.max(a.x, b.x) > rect.x - padding && Math.min(a.x, b.x) < rect.x + rect.w + padding;
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
    return {...curve, ...roundedPath(polyline)};
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

  global.AdeFlowModel = {route, pointAt, avoidCards, beatHops, flatten, wrap, project, accumulated, narration};
})(globalThis);
