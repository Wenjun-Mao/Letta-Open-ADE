// Offline DOM/playback contracts; not a browser pixel or assistive-technology audit.
const assert = require('node:assert/strict');
const test = require('node:test');
const {player} = require('./player-fixture.cjs');

for (const width of [736, 320]) {
  test(`inline drawing reflows without scaling text or horizontal overflow at ${width}px`, () => {
    const app = player(width, false, true);
    for (let tour = 0; tour < 7; tour += 1) {
      app.select(tour);
      if (app.find('viewport').dataset.view !== 'whole') app.find('whole').click();
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
    assert.equal(app.root.querySelectorAll('[data-tour-index]').length, 7);
    assert.equal(app.root.dataset.playing, 'false');
    for (let index = 0; index < 7; index += 1) {
      app.select(index);
      assert.equal(app.root.dataset.beat, '0');
      assert.equal(app.root.dataset.playing, 'false');
      if (app.find('viewport').dataset.view !== 'whole') app.find('whole').click();
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
  const frozenProgress = app.root.querySelector('[data-tour-index="0"] .tour-progress').style.transform;
  app.advance(500);
  assert.equal(app.find('viewport').querySelector('[data-packet]').getAttribute('transform'), frozen);
  assert.equal(app.root.querySelector('[data-tour-index="0"] .tour-progress').style.transform, frozenProgress);
  app.find('replay').click();
  assert.equal(app.root.dataset.beat, '0');
  assert.equal(app.root.dataset.playing, 'true');
  assert.equal(app.root.dataset.tour, '0');
  app.dom.window.close();
});

test('unrelated host globals and old preview state do not stall playback', () => {
  const app = player(736, false, true);
  app.find('next').click(); app.find('play').click(); app.advance(300);
  for (const widgetState of [undefined, {privateContent: {tour: 4, beat: 1, whole: false}}]) {
    app.dom.window.dispatchEvent(new app.dom.window.CustomEvent('openai:set_globals', {detail: {globals: {widgetState}}}));
    assert.equal(app.root.dataset.playing, 'true');
    assert.equal(app.find('viewport').dataset.view, 'whole');
    const before = app.find('viewport').querySelector('[data-packet]').getAttribute('transform');
    app.advance(200);
    assert.notEqual(app.find('viewport').querySelector('[data-packet]').getAttribute('transform'), before);
  }
  app.dom.window.dispatchEvent(new app.dom.window.CustomEvent('openai:set_globals', {detail: {globals: {
    widgetState: {privateContent: {presentation: 3, guide: false, chapter: 0, tour: 4, beat: 1, whole: false}},
  }}}));
  assert.equal(app.root.dataset.tour, '4');
  assert.equal(app.root.dataset.beat, '1');
  assert.equal(app.root.dataset.playing, 'false');
  assert.equal(app.find('viewport').dataset.view, 'message');
  app.dom.window.close();
});

test('detailed map keeps full geometry and bottom playback; previous transfers are subdued', () => {
  const app = player(1440);
  assert.equal(app.find('viewport').dataset.view, 'whole');
  assert.equal(app.find('viewport').querySelectorAll('[data-node]').length, 31);
  const first = app.find('viewport').querySelector('svg').getAttribute('viewBox');
  const rect = () => app.find('viewport').querySelector('[data-node="chat"] .node-surface').outerHTML;
  const chat = rect();
  assert.ok(app.find('viewport').compareDocumentPosition(app.root.querySelector('.journey-playback')) & app.dom.window.Node.DOCUMENT_POSITION_FOLLOWING);
  assert.ok(app.find('viewport').querySelector('[data-node="chat"] .payload.is-empty'));
  app.find('next').click();
  assert.equal(app.find('viewport').querySelector('svg').getAttribute('viewBox'), first);
  assert.equal(rect(), chat);
  assert.ok(app.find('viewport').querySelector('[data-node="chat"] .payload.is-filled'));
  assert.ok(app.find('viewport').querySelector('[data-packet-data="submit"]'));
  assert.ok(app.find('viewport').querySelector('[data-edge="submit"].active-connection'));
  app.find('next').click();
  assert.equal(rect(), chat);
  assert.ok(app.find('viewport').querySelector('[data-edge="submit"].completed-connection'));
  app.select(4);
  assert.equal(app.find('viewport').querySelector('svg').getAttribute('viewBox'), first);
  assert.equal(app.find('viewport').querySelector('[data-node="chat"] .payload-text').textContent, '-');
  app.dom.window.close();
});

test('subtitle preserves every status; qualified payload metadata is displayed', () => {
  const app = player();
  assert.match(app.find('viewport').querySelector('[data-node="selection"] .node-sub').textContent, /Experimental.*Proposed/);
  assert.equal(app.root.querySelectorAll('[data-module-details] dt').length, 31);
  assert.match(app.root.querySelector('[data-module-details]').textContent, /Not persisted or delivered yet/);
  for (let index = 0; index < 23; index += 1) app.find('next').click();
  assert.match(app.find('viewport').querySelector('[data-node="delivery"] .payload-meta').textContent, /Summary if present/);
  app.dom.window.close();
});

test('fullscreen is unavailable in inline preview without changing playback', () => {
  const app = player(736, false, true);
  assert.equal(app.find('fullscreen').hidden, true);
  app.find('next').click(); app.find('play').click(); app.advance(300);
  assert.equal(app.root.dataset.playing, 'true');
  app.dom.window.close();
});

test('native fullscreen enters and exits without restarting the selected beat', () => {
  const app = player(1440, false, false, true);
  assert.equal(app.find('fullscreen').hidden, false);
  app.select(2); app.find('next').click();
  app.find('fullscreen').click();
  assert.equal(app.dom.window.document.fullscreenElement, app.root);
  assert.equal(app.find('fullscreen').textContent, 'Exit full screen');
  assert.equal(app.root.dataset.beat, '1');
  app.find('fullscreen').click();
  assert.equal(app.dom.window.document.fullscreenElement, null);
  assert.equal(app.root.dataset.tour, '2');
  assert.equal(app.root.dataset.beat, '1');
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
  assert.match(routed.d, / Q /);
  assert.equal(JSON.stringify(model.pointAt(routed, 0)), JSON.stringify(curve.start));
  assert.equal(JSON.stringify(model.pointAt(routed, 1)), JSON.stringify(curve.end));
  for (let index = 0; index <= 100; index += 1) {
    const point = model.pointAt(routed, index / 100);
    const block = rects.middle;
    assert.equal(point.x > block.x && point.x < block.x + block.w && point.y > block.y && point.y < block.y + block.h, false);
  }
  app.dom.window.close();
});

test('connection routing also protects visible group headings', () => {
  const app = player();
  const model = app.dom.window.AdeFlowModel;
  const rects = {a: {x: 50, y: 20, w: 100, h: 60}, b: {x: 350, y: 20, w: 100, h: 60}};
  const title = {x: 220, y: 42, w: 100, h: 16, text: true};
  const [curve] = model.route([{id: 'one', from: 'a', to: 'b'}], rects);
  const protectedCurve = model.avoidCards(curve, {...rects, '@heading:group': title});
  for (let index = 0; index <= 200; index += 1) {
    const point = model.pointAt(protectedCurve, index / 200);
    assert.equal(point.x > title.x && point.x < title.x + title.w && point.y > title.y && point.y < title.y + title.h, false);
  }
  app.dom.window.close();
});

test('whole-map routes avoid unrelated cards and headings across the reviewed specification', () => {
  const app = player(1440);
  const figure = JSON.parse(app.find('figure').textContent);
  const model = app.dom.window.AdeFlowModel;
  const plan = app.dom.window.AdeFlowLayout.layout(figure.props.layout, figure.props.steps);
  for (const original of model.route(figure.props.edges, plan.rects)) {
    const curve = model.avoidCards(original, plan.obstacles);
    const others = Object.entries(plan.obstacles).filter(([id]) => id !== curve.from && id !== curve.to);
    for (let index = 0; index <= 300; index += 1) {
      const point = model.pointAt(curve, index / 300);
      for (const [id, rect] of others) {
        assert.equal(point.x > rect.x && point.x < rect.x + rect.w && point.y > rect.y && point.y < rect.y + rect.h,
          false, `${curve.id} crosses ${id}`);
      }
    }
  }
  app.dom.window.close();
});
