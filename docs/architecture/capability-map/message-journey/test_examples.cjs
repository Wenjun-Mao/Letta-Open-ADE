// Fictional teaching values are not provider evidence or behavior qualification.
const assert = require('node:assert/strict');
const test = require('node:test');
const {player} = require('./player-fixture.cjs');
const guided = (width = 736, reduced = false) => player(width, reduced, true, false, true);

function payload(app, id) {
  return [...app.find('viewport').querySelectorAll(`[data-node="${id}"] .payload-text tspan`)]
    .map(line => line.textContent).join(' ');
}
function fixture(app) {
  const data = JSON.parse(app.find('example-data').textContent);
  return {data, example: app.dom.window.AdeJourneyExample.create(data)};
}

test('every chapter has a concrete example while paused, without adding architecture nodes', () => {
  const app = guided();
  const {data} = fixture(app);
  const markers = [data.current_user.id, data.existing_fact.value, data.candidate_reply,
    data.existing_fact.fact_id, 'Ottawa (v1) -> Toronto (v2)', data.candidate_reply];
  for (let chapter = 0; chapter < 6; chapter += 1) {
    app.root.querySelector(`[data-chapter-index="${chapter}"]`).click();
    assert.equal(app.find('example').hidden, false);
    assert.match(app.find('example-caption').textContent, /Fictional.*Not a live trace.*API JSON/);
    assert.ok(app.find('example-output').textContent.includes(markers[chapter]));
    assert.equal(app.root.dataset.playing, 'false');
    assert.equal(app.callbacks.size, 0);
    assert.ok(app.find('viewport').querySelectorAll('[data-node]').length <= 6);
  }
  app.dom.window.close();
});

test('example decorating changes only illustrative show values, never edges, order, timing or source bindings', () => {
  const app = guided();
  const {example} = fixture(app);
  const original = JSON.parse(app.find('figure').textContent);
  const before = JSON.stringify(original);
  const guide = app.dom.window.AdeJourneyGuide.build(original);
  const decorated = example.decorate(guide);
  assert.equal(JSON.stringify(original), before);
  assert.equal(JSON.stringify(decorated.props.layout), JSON.stringify(guide.props.layout));
  assert.equal(JSON.stringify(decorated.props.edges), JSON.stringify(guide.props.edges));
  decorated.props.steps.forEach((step, index) => {
    assert.equal(step.label, guide.props.steps[index].label);
    assert.equal(JSON.stringify(step.nodes), JSON.stringify(guide.props.steps[index].nodes));
    step.flow.forEach((beat, beatIndex) => {
      const {show, ...rest} = beat;
      const {show: sourceShow, ...sourceRest} = guide.props.steps[index].flow[beatIndex];
      assert.equal(JSON.stringify(rest), JSON.stringify(sourceRest));
      assert.ok(Object.keys(show).every(id => step.nodes.includes(id)));
      assert.ok(sourceShow);
    });
  });
  app.dom.window.close();
});

test('the authored value timeline is fenced to the actual source transfer identities', () => {
  const app = guided();
  const {example} = fixture(app);
  const source = JSON.parse(app.find('figure').textContent).props.steps[0].flow;
  const model = app.dom.window.AdeFlowModel;
  const anchors = {1: 'submit', 4: 'accepted-source', 5: 'save-user', 7: 'claim-run', 9: 'bound-definition',
    16: 'eligible-scope', 20: 'fact-search-data', 22: 'fact-results', 23: 'delivered-request',
    24: 'generation-input', 27: 'candidate-reply', 28: 'typed-review-input', 30: 'review-response',
    31: 'index-input', 33: 'fact-embedding-response', 34: 'proposed-changes', 36: 'pending-reply',
    37: 'commit-dialogue', 38: 'committed-outcome', 39: 'refresh-ui', 40: 'lineage-state', 41: 'activity-state'};
  for (const [when] of example.timeline) assert.ok(model.beatHops(source[when]).some(hop => hop.edge === anchors[when]));
  app.dom.window.close();
});

test('pending reply, proposal, vector, atomic commit and UI visibility cannot appear early', () => {
  const app = guided();
  const {data, example} = fixture(app);
  assert.equal(example.at(26).candidate, undefined);
  assert.equal(example.at(27).candidate[0].text, data.candidate_reply);
  assert.equal(example.at(29).review[0].tag, 'TYPED INPUT');
  assert.equal(example.at(30).review[0].tag, 'PROPOSED');
  assert.equal(example.at(32).embedding[0].tag, 'FACT DOCUMENT');
  assert.equal(example.at(33).embedding[0].tag, 'VECTOR READY');
  assert.equal(example.at(36).commit[0].tag, 'PENDING');
  assert.equal(example.at(36).facts, undefined);
  assert.equal(example.at(6).runs[0].tag, 'QUEUED');
  assert.equal(example.at(7).runs[0].tag, 'RUNNING');
  assert.equal(example.at(36).runs[0].tag, 'RUNNING');
  assert.match(example.at(36).candidate[0].meta, /Not saved or displayed/);
  const success = example.at(37);
  assert.equal(success.commit[0].tag, 'ATOMIC SUCCESS');
  assert.match(success.candidate[0].meta, /Same text saved at commit/);
  assert.match(success.facts[0].text, /Toronto v2/);
  assert.equal(success.dialogue[0].text, data.candidate_reply);
  assert.equal(success.runs[0].tag, 'SUCCEEDED');
  assert.equal(example.at(38).chat[0].text, data.current_user.content);
  assert.equal(example.at(39).chat[0].text, data.candidate_reply);
  assert.equal(example.at(39).chat[0].tag, 'DISPLAYED');
  assert.equal(example.at(41).summaries, undefined);
  app.dom.window.close();
});

test('actual displayed cards use the same current message, proposal and committed candidate across chapters', () => {
  const app = guided();
  const {data} = fixture(app);
  assert.equal(payload(app, 'chat'), data.current_user.content);
  app.root.querySelector('[data-chapter-index="2"]').click();
  app.find('play').click(); app.advance(5000);
  assert.equal(payload(app, 'candidate'), data.candidate_reply);
  assert.equal(app.root.dataset.playing, 'false');
  app.find('next').click();
  assert.match(app.find('example-note').textContent, /NOT the candidate reply/);
  assert.equal(app.find('viewport').querySelector('[data-node="candidate"]'), null);
  app.find('play').click(); app.advance(25000);
  assert.match(payload(app, 'review'), /correct f-location-demo -> Toronto/);
  app.find('next').click(); app.find('play').click(); app.advance(10000);
  assert.equal(payload(app, 'dialogue'), data.candidate_reply);
  app.find('next').click();
  assert.equal(payload(app, 'chat'), data.candidate_reply);
  assert.match(payload(app, 'facts'), /Toronto v2/);
  app.find('play').click(); app.advance(10000);
  assert.equal(payload(app, 'chat'), data.candidate_reply);
  assert.match(payload(app, 'lineage'), /Ottawa \(v1\) -> Toronto \(v2\)/);
  app.dom.window.close();
});

test('detailed and experimental paths do not inherit the fictional guide values or previews', () => {
  const app = guided();
  const {data} = fixture(app);
  app.find('detail').click();
  assert.equal(app.find('example').hidden, true);
  assert.ok(!payload(app, 'chat').includes(data.current_user.content));
  app.select(3);
  assert.equal(app.find('example').hidden, true);
  assert.match(app.find('chapter-title').textContent, /Experimental/);
  app.find('detail').click();
  assert.equal(app.find('example').hidden, false);
  assert.equal(app.root.dataset.playing, 'false');
  app.dom.window.close();
});

for (const width of [320, 736]) {
  test(`concrete data cards fit within their measured insets at ${width}px`, () => {
    const app = guided(width);
    const {example} = fixture(app);
    const figure = JSON.parse(app.find('figure').textContent);
    const guide = app.dom.window.AdeJourneyGuide, layout = app.dom.window.AdeFlowLayout;
    const decorated = example.decorate(guide.build(figure));
    for (const step of decorated.props.steps) {
      const plan = layout.layout(guide.layout(figure.props.layout, step.nodes), [step], width < 600, width);
      assert.ok(plan.w <= width);
      for (const card of plan.cards) {
        for (const beat of step.flow) {
          const content = beat.show[card.item.id];
          if (content == null) continue;
          let height = 12;
          for (const row of layout.rows(content, card.w - 20)) {
            height += (row.tag ? 18 : 0) + (row.lines.length + row.metadata.length) * 16 + 5;
            assert.ok(row.lines.every(line => line.length * 6.7 <= card.w - 36));
          }
          assert.ok(height <= card.payload);
          assert.ok(card.payloadY + card.payload <= card.h);
        }
      }
    }
    app.dom.window.close();
  });
}

test('reduced-motion manual steps change previews without running any animation', () => {
  const app = guided(320, true);
  const input = app.find('example-input').textContent;
  app.find('next').click();
  assert.notEqual(app.find('example-input').textContent, input);
  assert.match(app.find('example-output').textContent, /Conversation input/);
  assert.equal(app.callbacks.size, 0);
  app.find('previous').click();
  assert.equal(app.find('example-input').textContent, input);
  app.dom.window.close();
});

test('example previews insert data as text, not executable markup', () => {
  const app = guided();
  const {data} = fixture(app);
  data.current_user.content = '<img src=x onerror=alert(1)>';
  const example = app.dom.window.AdeJourneyExample.create(data);
  app.find('example').dataset.chapter = '';
  app.dom.window.AdeJourneyExample.render(app.root, example, 0);
  assert.equal(app.find('example-input').querySelector('img'), null);
  assert.ok(app.find('example-input').textContent.includes(data.current_user.content));
  app.dom.window.close();
});
