// Offline DOM/playback contracts; not a browser pixel or assistive-technology audit.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const test = require('node:test');
const webRequire = createRequire(path.join(__dirname, '../../../../apps/ade-web/package.json'));
const {JSDOM} = webRequire('jsdom');
const html = fs.readFileSync(path.join(__dirname, 'ade-message-journey.html'), 'utf8');

function player(width = 900, reducedMotion = false, inline = false) {
  let time = 0, nextId = 1;
  const callbacks = new Map(), mediaListeners = [];
  const media = {matches: reducedMotion, addEventListener: (_, callback) => mediaListeners.push(callback)};
  const source = inline ? html.replace('id="ade-moving-message" data-standalone', 'id="ade-moving-message"') : html;
  const dom = new JSDOM(source, {
    runScripts: 'dangerously',
    beforeParse(window) {
      Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', {get: () => width});
      window.matchMedia = () => media;
      window.ResizeObserver = class { observe() {} disconnect() {} };
      window.requestAnimationFrame = callback => { const id = nextId++; callbacks.set(id, callback); return id; };
      window.cancelAnimationFrame = id => callbacks.delete(id);
    },
  });
  const root = dom.window.document.getElementById('ade-moving-message');
  const find = name => root.querySelector(`[data-${name}]`);
  function advance(milliseconds) {
    for (let i = 0; i < milliseconds; i += 50) {
      time += 50;
      const pending = [...callbacks.values()]; callbacks.clear();
      pending.forEach(callback => callback(time));
    }
  }
  function select(index) {
    find('tour').value = String(index);
    find('tour').dispatchEvent(new dom.window.Event('change'));
  }
  return {dom, root, find, advance, select, media, mediaListeners, callbacks};
}

for (const width of [736, 320]) {
  test(`inline drawing reflows without scaling text or horizontal overflow at ${width}px`, () => {
    const app = player(width, false, true);
    for (let tour = 0; tour < 7; tour += 1) {
      app.select(tour);
      app.find('whole').click();
      assert.equal(app.find('viewport').querySelectorAll('[data-node]').length, 31);
      const checkWidth = () => {
        const size = app.find('viewport').querySelector('svg').getAttribute('viewBox').split(' ').map(Number);
        assert.ok(size[2] <= width, `drawing width ${size[2]} exceeds ${width}`);
      };
      checkWidth();
      app.find('whole').click();
      do {
        checkWidth();
        if (app.find('next').disabled) break;
        app.find('next').click();
      } while (true);
    }
    app.dom.window.close();
  });
}

for (const width of [1440, 375]) {
  test(`all tours, both views and manual steps at ${width}px`, () => {
    const app = player(width);
    assert.equal(app.find('tour').options.length, 7);
    assert.equal(app.root.dataset.playing, 'false');
    for (let index = 0; index < 7; index += 1) {
      app.select(index);
      assert.equal(app.root.dataset.beat, '0');
      assert.equal(app.root.dataset.playing, 'false');
      app.find('whole').click();
      assert.equal(app.find('viewport').querySelectorAll('[data-node]').length, 31);
      assert.ok(app.find('viewport').querySelector('[data-group="external-tools"]'));
      app.find('whole').click();
      while (!app.find('next').disabled) {
        app.find('next').click();
        const paths = app.find('viewport').querySelectorAll('[data-edge]');
        assert.ok([...paths].every(node => !/undefined|NaN/.test(node.getAttribute('d'))));
        if (index === 6) assert.equal(paths.length, 0);
      }
      app.find('previous').click();
      assert.equal(app.find('next').disabled, false);
    }
    app.dom.window.close();
  });
}

test('Play moves a packet, Pause freezes it, Replay restarts without changing tour', () => {
  const app = player();
  app.find('next').click();
  app.find('play').click();
  app.advance(300);
  const initial = app.find('viewport').querySelector('[data-packet]').getAttribute('transform');
  app.advance(500);
  const moved = app.find('viewport').querySelector('[data-packet]').getAttribute('transform');
  assert.notEqual(moved, initial);
  app.find('play').click();
  const frozen = app.find('viewport').querySelector('[data-packet]').getAttribute('transform');
  app.advance(500);
  assert.equal(app.find('viewport').querySelector('[data-packet]').getAttribute('transform'), frozen);
  app.find('replay').click();
  assert.equal(app.root.dataset.beat, '0');
  assert.equal(app.root.dataset.playing, 'true');
  assert.equal(app.root.dataset.tour, '0');
  app.dom.window.close();
});

test('playback stops instead of entering the next experimental branch', () => {
  const app = player();
  app.select(3);
  app.find('replay').click();
  app.advance(25000);
  assert.equal(app.root.dataset.tour, '3');
  assert.equal(app.root.dataset.playing, 'false');
  assert.equal(app.find('next').disabled, true);
  assert.equal(app.callbacks.size, 0);
  app.dom.window.close();
});

test('reduced motion preserves manual navigation and disables moving playback', () => {
  const app = player(375, true);
  assert.equal(app.find('play').disabled, true);
  app.find('next').click();
  assert.equal(app.root.dataset.beat, '1');
  app.find('replay').click();
  assert.equal(app.root.dataset.playing, 'false');
  assert.equal(app.callbacks.size, 0);
  app.dom.window.close();
});

test('routing has directed endpoints, deterministic ports and exact cubic endpoint positions', () => {
  const app = player();
  const model = app.dom.window.AdeFlowModel;
  const [curve] = model.route([{id: 'one', from: 'a', to: 'b'}], {
    a: {x: 0, y: 0, w: 100, h: 50}, b: {x: 200, y: 0, w: 100, h: 50},
  });
  assert.equal(JSON.stringify(model.pointAt(curve, 0)), JSON.stringify(curve.start));
  assert.equal(JSON.stringify(model.pointAt(curve, 1)), JSON.stringify(curve.end));
  assert.equal(curve.start.x, 100);
  assert.equal(curve.end.x, 200);
  app.dom.window.close();
});

test('obstructed packet routes avoid intervening cards without changing endpoint identity', () => {
  const app = player();
  const model = app.dom.window.AdeFlowModel;
  const rects = {
    a: {x: 50, y: 20, w: 100, h: 60}, b: {x: 350, y: 20, w: 100, h: 60},
    middle: {x: 220, y: 0, w: 100, h: 100},
  };
  const [curve] = model.route([{id: 'one', from: 'a', to: 'b'}], rects);
  const routed = model.avoidCards(curve, rects);
  assert.ok(routed.polyline);
  assert.equal(JSON.stringify(model.pointAt(routed, 0)), JSON.stringify(curve.start));
  assert.equal(JSON.stringify(model.pointAt(routed, 1)), JSON.stringify(curve.end));
  for (let index = 0; index <= 100; index += 1) {
    const point = model.pointAt(routed, index / 100);
    const block = rects.middle;
    assert.equal(point.x > block.x && point.x < block.x + block.w && point.y > block.y && point.y < block.y + block.h, false);
  }
  app.dom.window.close();
});
