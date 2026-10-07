// Guided presentation contracts, not ADE behavioral qualification.
const assert = require('node:assert/strict');
const test = require('node:test');
const {player} = require('./player-fixture.cjs');

const guided = (width = 736, reduced = false, inline = true) => player(width, reduced, inline, false, true);

test('default is a paused six-chapter guide, not the full map', () => {
  const app = guided();
  assert.equal(app.root.dataset.guide, 'true');
  assert.equal(app.root.dataset.playing, 'false');
  assert.equal(app.find('viewport').dataset.view, 'guided');
  assert.equal(app.root.querySelectorAll('[data-chapter-index]').length, 6);
  assert.equal(app.find('count').textContent, 'Chapter 1 of 6');
  assert.equal(app.find('previous').disabled, true);
  assert.equal(app.find('next').textContent, 'Forward');
  assert.equal(app.find('whole').hidden, true);
  assert.equal(app.find('alternatives').open, false);
  assert.equal(app.find('viewport').querySelectorAll('[data-node]').length, 6);
  assert.match(app.root.querySelector('.journey-foot').textContent, /deferred.*experimental\/proposed/);
  assert.equal(app.root.querySelectorAll('[data-module-details] dt').length, 31);
  app.dom.window.close();
});

test('all guide chapters and detailed tours expose positive support and data identities', () => {
  const app = guided(1920);
  const labels = () => [...app.find('viewport').querySelectorAll('.frame-title')].map(item => item.textContent);
  for (let chapter = 0; chapter < 6; chapter += 1) {
    app.root.querySelector(`[data-chapter-index="${chapter}"]`).click();
    const headers = labels().join(' ');
    assert.match(headers, /RUNTIME COORDINATION/);
    assert.doesNotMatch(headers, /NOT L1|NOT MODULES|SUPPORTING RUNTIME/);
    for (const id of ['accept', 'attempt', 'dispatch', 'outcome']) {
      const node = app.find('viewport').querySelector(`[data-node="${id}"]`);
      if (node) assert.equal(node.parentElement.querySelector('[data-group="runtime-coordination"]') != null, true);
    }
  }
  app.find('detail').click();
  for (let tour = 0; tour < 7; tour += 1) {
    app.select(tour);
    assert.match(labels().join(' '), /RUNTIME COORDINATION.*MODEL ACCESS.*PERSISTED OPERATIONAL RECORDS/);
    assert.doesNotMatch(labels().join(' '), /NOT L1|NOT ANOTHER L1|NOT L3|NOT PROCESSING MODULES/);
    app.find('whole').click();
    const count = JSON.parse(app.find('figure').textContent).props.steps[tour].flow.length;
    for (let beat = 0; beat < count; beat += 1) {
      assert.doesNotMatch(labels().join(' '), /NOT L1|NOT MODULES|SUPPORTING RUNTIME/);
      if (beat < count - 1) app.find('next').click();
    }
    app.find('whole').click();
  }
  app.dom.window.close();
});

test('wide acceptance detours pass below the worker instead of bracketing it', () => {
  const app = guided(1920);
  const figure = JSON.parse(app.find('figure').textContent);
  const model = app.dom.window.AdeFlowModel, guide = app.dom.window.AdeJourneyGuide;
  const example = app.dom.window.AdeJourneyExample.create(JSON.parse(app.find('example-data').textContent));
  const step = example.decorate(guide.build(figure)).props.steps[0];
  const plan = app.dom.window.AdeFlowLayout.layout(guide.layout(figure.props.layout, step.nodes), [step], false, 1920);
  const worker = plan.rects.attempt;
  const detours = ['accepted-source', 'save-accepted-run'];
  const curves = model.route(figure.props.edges, plan.rects)
    .map(curve => model.avoidCards(curve, plan.obstacles));
  for (const id of detours) {
    const curve = curves.find(item => item.id === id);
    assert.equal(curve.around, 'below');
    let passesWorker = false;
    for (let sample = 0; sample <= 200; sample += 1) {
      const point = model.pointAt(curve, sample / 200);
      assert.ok(point.x >= 0 && point.x <= plan.w && point.y >= 0 && point.y <= plan.h);
      if (point.x >= worker.x && point.x <= worker.x + worker.w) {
        passesWorker = true;
        assert.ok(point.y >= worker.y + worker.h + 6, `${id} must pass below the worker`);
      }
    }
    assert.ok(passesWorker);
  }
  const paths = detours.map(id => app.find('viewport').querySelector(`[data-edge="${id}"]`).getAttribute('d'));
  app.find('play').click(); app.advance(15000);
  assert.deepEqual(detours.map(id => app.find('viewport').querySelector(`[data-edge="${id}"]`).getAttribute('d')), paths);
  app.dom.window.close();
});

test('Forward and Back visit chapters in order and always stop playback', () => {
  const app = guided();
  const labels = ['Accept message', 'Assemble context', 'Generate candidate', 'Review updates', 'Validate and commit', 'Display reply'];
  for (let chapter = 0; chapter < labels.length; chapter += 1) {
    assert.equal(app.root.dataset.chapter, String(chapter));
    assert.match(app.find('chapter-title').textContent, new RegExp(labels[chapter]));
    assert.equal(app.root.dataset.playing, 'false');
    assert.equal(app.callbacks.size, 0);
    assert.equal(app.find('next').disabled, chapter === 5);
    if (chapter < 5) { app.find('play').click(); app.advance(300); app.find('next').click(); }
  }
  for (let chapter = 4; chapter >= 0; chapter -= 1) {
    app.find('previous').click();
    assert.equal(app.root.dataset.chapter, String(chapter));
    assert.equal(app.root.dataset.playing, 'false');
  }
  app.find('previous').click();
  assert.equal(app.root.dataset.chapter, '0');
  app.dom.window.close();
});

test('each chapter animates real transfers and stops before the next chapter', () => {
  const app = guided();
  for (let chapter = 0; chapter < 6; chapter += 1) {
    app.root.querySelector(`[data-chapter-index="${chapter}"]`).click();
    app.find('play').click(); app.advance(300);
    const before = app.find('viewport').querySelector('[data-packet]').getAttribute('transform');
    app.advance(300);
    assert.notEqual(app.find('viewport').querySelector('[data-packet]').getAttribute('transform'), before);
    app.find('play').click();
    const frozen = app.find('viewport').querySelector('[data-packet]').getAttribute('transform');
    app.advance(500);
    assert.equal(app.find('viewport').querySelector('[data-packet]').getAttribute('transform'), frozen);
    app.find('play').click(); app.advance(25000);
    assert.equal(app.root.dataset.chapter, String(chapter));
    assert.equal(app.root.dataset.playing, 'false');
    assert.equal(app.callbacks.size, 0);
    assert.equal(app.find('next').disabled, chapter === 5);
    app.find('replay').click();
    assert.equal(app.root.dataset.chapter, String(chapter));
    assert.equal(app.root.dataset.beat, '0');
  }
  app.dom.window.close();
});

test('chapters partition the current tour; every guided hop keeps exact source identity and order', () => {
  const app = guided();
  const figure = JSON.parse(app.find('figure').textContent);
  const guide = app.dom.window.AdeJourneyGuide;
  const projected = guide.build(figure);
  const edges = new Map(figure.props.edges.map(edge => [edge.id, edge]));
  let next = 0;
  guide.chapters.forEach((chapter, index) => {
    assert.equal(chapter.start, next);
    next = chapter.end + 1;
    const step = projected.props.steps[index];
    assert.ok(step.flow.length > 0);
    const actual = step.flow.map(beat => beat.sourceBeat);
    assert.deepEqual([...actual].sort((a, b) => a - b), actual);
    step.flow.forEach(beat => {
      assert.ok(beat.sourceBeat >= chapter.start && beat.sourceBeat <= chapter.end);
      const original = figure.props.steps[0].flow[beat.sourceBeat];
      const sourceHops = app.dom.window.AdeFlowModel.beatHops(original).map(hop => hop.edge);
      const values = Object.fromEntries(Object.entries(app.dom.window.AdeFlowModel.accumulated(figure.props.steps[0], beat.sourceBeat))
        .filter(([id]) => chapter.nodes.includes(id)));
      assert.equal(JSON.stringify(beat.show), JSON.stringify(values));
      beat.edges.forEach(hop => {
        assert.ok(sourceHops.includes(hop.edge));
        assert.ok(chapter.nodes.includes(edges.get(hop.edge).from));
        assert.ok(chapter.nodes.includes(edges.get(hop.edge).to));
        assert.ok(!edges.get(hop.edge).label.includes('EXPERIMENTAL'));
      });
    });
  });
  assert.equal(next, figure.props.steps[0].flow.length);
  app.dom.window.close();
});

test('hidden provider-return beats still update visible source-backed data cards', () => {
  const app = guided();
  app.root.querySelector('[data-chapter-index="3"]').click();
  assert.match(app.find('viewport').querySelector('[data-node="review"] .payload-tag').textContent, /TYPED INPUT/);
  app.find('play').click(); app.advance(2300); app.find('play').click();
  const proposal = [...app.find('viewport').querySelectorAll('[data-node="review"] .payload-text tspan')]
    .map(line => line.textContent).join(' ');
  assert.equal(proposal, 'correct f-location-demo -> Toronto');
  app.root.querySelector('[data-chapter-index="5"]').click();
  assert.match(app.find('viewport').querySelector('[data-node="runs"] .payload-tag').textContent, /SUCCEEDED/);
  app.dom.window.close();
});

test('guide preserves typed review exclusion, shared generation, and atomic commit qualifications', () => {
  const app = guided();
  app.root.querySelector('[data-chapter-index="2"]').click();
  assert.match(app.find('narration').textContent, /one generation call.*candidate.*not saved/);
  assert.ok(app.find('viewport').querySelector('[data-node="behavior"]'));
  assert.ok(app.find('viewport').querySelector('[data-group="guide-artifacts"]'));
  const figure = JSON.parse(app.find('figure').textContent);
  const ownership = app.dom.window.AdeJourneyGuide.layout(figure.props.layout, ['dispatch', 'behavior', 'candidate']);
  assert.ok(ownership.children.find(group => group.id === 'guide-artifacts').children.some(node => node.id === 'candidate'));
  assert.equal(ownership.children.find(group => group.id === 'runtime-coordination').children.some(node => node.id === 'candidate'), false);
  assert.match(app.find('viewport').querySelector('[data-node="behavior"] .node-sub').textContent, /CHAR-03 \+ CHAR-04.*Partial/);
  app.find('next').click();
  assert.match(app.find('narration').textContent, /does NOT receive the candidate reply/);
  assert.equal(app.find('viewport').querySelector('[data-node="candidate"]'), null);
  assert.equal(app.find('viewport').querySelector('[data-edge="reference-reply"]'), null);
  app.find('next').click();
  assert.match(app.find('narration').textContent, /together.*one part of that atomic transaction/);
  app.dom.window.close();
});

test('details opens at the source beat and can return to the same chapter, paused', () => {
  const app = guided();
  app.root.querySelector('[data-chapter-index="3"]').click();
  app.find('detail').click();
  assert.equal(app.root.dataset.guide, 'false');
  assert.equal(app.root.dataset.beat, '28');
  assert.equal(app.find('viewport').dataset.view, 'whole');
  assert.equal(app.find('viewport').querySelectorAll('[data-node]').length, 31);
  assert.equal(app.find('chapters').hidden, true);
  assert.equal(app.dom.window.getComputedStyle(app.find('chapters')).display, 'none');
  app.find('next').click(); app.find('detail').click();
  assert.equal(app.root.dataset.chapter, '3');
  assert.equal(app.root.dataset.guide, 'true');
  assert.equal(app.root.dataset.playing, 'false');
  app.select(4);
  assert.equal(app.root.dataset.guide, 'false');
  assert.match(app.find('chapter-title').textContent, /Experimental/);
  app.find('detail').click();
  assert.equal(app.root.dataset.chapter, '3');
  app.dom.window.close();
});

test('reduced-motion users can move between chapters at their own pace', () => {
  const app = guided(320, true);
  assert.equal(app.find('play').disabled, true);
  app.find('next').click();
  assert.equal(app.root.dataset.chapter, '1');
  app.find('previous').click();
  assert.equal(app.root.dataset.chapter, '0');
  app.find('replay').click();
  assert.equal(app.root.dataset.playing, 'false');
  assert.equal(app.callbacks.size, 0);
  app.dom.window.close();
});

test('only the current transfer group is emphasized, not every completed transfer', () => {
  const app = guided();
  app.find('play').click(); app.advance(2300);
  assert.ok(app.find('viewport').querySelector('[data-edge="submit"].completed-connection'));
  assert.equal(app.find('viewport').querySelectorAll('.active-connection').length, 1);
  app.dom.window.close();
});

for (const [width, inline] of [[736, true], [320, true], [1440, false], [375, false]]) {
  test(`guide fits ${width}px with 3-6 pieces and stable endpoints within each chapter`, () => {
    const app = guided(width, false, inline);
    for (let chapter = 0; chapter < 6; chapter += 1) {
      app.root.querySelector(`[data-chapter-index="${chapter}"]`).click();
      const svg = app.find('viewport').querySelector('svg');
      const size = svg.getAttribute('viewBox').split(' ').map(Number);
      assert.ok(size[2] <= width);
      assert.equal(Number(svg.getAttribute('width')), size[2]);
      const nodes = svg.querySelectorAll('[data-node]');
      assert.ok(nodes.length >= 3 && nodes.length <= 6);
      const surfaces = [...svg.querySelectorAll('.node-surface')].map(node => node.outerHTML).join('');
      app.find('play').click(); app.advance(5000); app.find('play').click();
      assert.equal([...app.find('viewport').querySelectorAll('.node-surface')].map(node => node.outerHTML).join(''), surfaces);
    }
    app.dom.window.close();
  });
}

test('compatible saved guide state restores paused; an older full-map default is ignored', () => {
  const app = guided();
  const restore = privateContent => app.dom.window.dispatchEvent(new app.dom.window.CustomEvent('openai:set_globals', {
    detail: {globals: {widgetState: {privateContent}}},
  }));
  restore({presentation: 2, tour: 4, beat: 1, whole: true});
  assert.equal(app.root.dataset.guide, 'true');
  assert.equal(app.root.dataset.chapter, '0');
  restore({presentation: 3, guide: true, chapter: 4, tour: 0, beat: 999, whole: true});
  assert.equal(app.root.dataset.chapter, '4');
  assert.equal(app.root.dataset.playing, 'false');
  assert.equal(app.root.dataset.beat, '2');
  app.dom.window.close();
});

test('manual choices save a compact, compatible chapter snapshot and restore paused', () => {
  const app = guided();
  let saved;
  app.dom.window.openai = {setWidgetState: value => { saved = value; return Promise.resolve(); }};
  app.find('next').click();
  assert.equal(saved.modelContent.view, 'guided');
  assert.equal(saved.modelContent.tour, 'Assemble context');
  assert.equal(saved.privateContent.presentation, 3);
  assert.equal(saved.privateContent.chapter, 1);
  assert.ok(JSON.stringify(saved).length < 16384);
  app.find('play').click();
  app.dom.window.dispatchEvent(new app.dom.window.CustomEvent('openai:set_globals', {detail: {globals: {widgetState: saved}}}));
  assert.equal(app.root.dataset.chapter, '1');
  assert.equal(app.root.dataset.playing, 'false');
  assert.equal(app.callbacks.size, 0);
  app.dom.window.close();
});

test('every guide route avoids unrelated cards and ownership headers at wide and narrow widths', () => {
  const app = guided();
  const figure = JSON.parse(app.find('figure').textContent);
  const guide = app.dom.window.AdeJourneyGuide, model = app.dom.window.AdeFlowModel;
  const fixture = JSON.parse(app.find('example-data').textContent);
  const projected = app.dom.window.AdeJourneyExample.create(fixture).decorate(guide.build(figure));
  for (const width of [320, 736, 1440]) {
    for (const step of projected.props.steps) {
      const group = guide.layout(figure.props.layout, step.nodes);
      const plan = app.dom.window.AdeFlowLayout.layout(group, [step], width < 600, width);
      for (const original of model.route(figure.props.edges, plan.rects)) {
        const curve = model.avoidCards(original, plan.obstacles);
        const others = Object.entries(plan.obstacles).filter(([id]) => id !== curve.from && id !== curve.to);
        for (let sample = 0; sample <= 200; sample += 1) {
          const point = model.pointAt(curve, sample / 200);
          for (const [id, rect] of others) assert.equal(point.x > rect.x && point.x < rect.x + rect.w
            && point.y > rect.y && point.y < rect.y + rect.h, false, `${step.label}: ${curve.id} crosses ${id}`);
        }
      }
    }
  }
  app.dom.window.close();
});
