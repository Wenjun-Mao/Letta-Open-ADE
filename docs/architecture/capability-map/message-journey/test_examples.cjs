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

test('every chapter begins with the current action example while paused, without adding architecture nodes', () => {
  const app = guided();
  const {data} = fixture(app);
  const markers = ['Acceptance input', 'Rowan, version v3', data.current_user.id,
    'Typed review input', 'Finalization input', data.candidate_reply];
  for (let chapter = 0; chapter < 6; chapter += 1) {
    app.root.querySelector(`[data-chapter-index="${chapter}"]`).click();
    assert.equal(app.find('example').hidden, false);
    assert.match(app.find('example-caption').textContent, /Fictional.*Not a live trace.*API JSON/);
    assert.ok(app.find('example-output').textContent.includes(markers[chapter]));
    assert.match(app.find('action-count').textContent, /^Action 1 of /);
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
  assert.match(app.find('example-note').textContent, /does NOT receive the candidate reply/);
  assert.equal(app.find('viewport').querySelector('[data-node="candidate"]'), null);
  app.find('play').click(); app.advance(25000);
  assert.match(payload(app, 'review'), /Correct fact ID: f-location-demo -> Toronto/);
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

test('reduced-motion manual actions update the example and pause within the same chapter', () => {
  const app = guided(320, true);
  const input = app.find('example-input').textContent;
  app.find('action-next').click();
  assert.notEqual(app.find('example-input').textContent, input);
  assert.match(app.find('example-output').textContent, /Message ID.*u-demo.*Run ID.*r-demo/);
  assert.equal(app.root.dataset.chapter, '0');
  assert.equal(app.root.dataset.beat, '1');
  assert.equal(app.root.dataset.playing, 'false');
  assert.equal(app.callbacks.size, 0);
  app.find('action-previous').click();
  assert.equal(app.find('example-input').textContent, input);
  app.dom.window.close();
});

test('example previews insert data as text, not executable markup', () => {
  const app = guided();
  const {data} = fixture(app);
  data.current_user.content = '<img src=x onerror=alert(1)>';
  const example = app.dom.window.AdeJourneyExample.create(data);
  app.find('example').dataset.action = '';
  const figure = app.dom.window.AdeJourneyGuide.build(JSON.parse(app.find('figure').textContent));
  app.dom.window.AdeJourneyExample.render(app.root, example, 0, figure.props.steps[0].flow[0]);
  assert.equal(app.find('example-input').querySelector('img'), null);
  assert.ok(app.find('example-input').textContent.includes(data.current_user.content));
  app.dom.window.close();
});

test('every guided transfer has a source-bound example and can be inspected without playback', () => {
  const app = guided();
  const {example} = fixture(app);
  const original = JSON.parse(app.find('figure').textContent);
  const guide = app.dom.window.AdeJourneyGuide.build(original);
  const visited = new Set();
  guide.props.steps.forEach((step, chapter) => {
    app.root.querySelector(`[data-chapter-index="${chapter}"]`).click();
    step.flow.forEach((beat, index) => {
      const lesson = example.forBeat(beat);
      visited.add(app.dom.window.AdeFlowModel.beatHops(beat)[0].edge);
      assert.equal(app.find('example-action').textContent, lesson.action);
      assert.equal(app.find('example-action').getAttribute('aria-live'), 'polite');
      assert.equal(app.find('example').dataset.action, `${chapter}:${beat.sourceBeat}`);
      assert.equal(app.find('action-count').textContent, `Action ${index + 1} of ${step.flow.length}`);
      assert.equal(app.find('action-previous').disabled, index === 0);
      assert.equal(app.find('action-next').disabled, index === step.flow.length - 1);
      assert.ok(lesson.input.length && lesson.output.length && lesson.note);
      assert.equal(app.root.dataset.playing, 'false');
      app.find('action-next').click();
      assert.equal(app.root.dataset.chapter, String(chapter));
      assert.equal(app.callbacks.size, 0);
    });
  });
  assert.deepEqual([...visited].sort(), Object.keys(example.lessons).sort());
  app.dom.window.close();
});

test('capture explains message and processing-job identity without claiming an early database write', () => {
  const app = guided();
  app.find('action-next').click();
  assert.match(app.find('example-action').textContent, /Capture the exact message/);
  assert.match(app.find('example-output').textContent, /Message ID \(this text, not its author\)u-demo/);
  assert.match(app.find('example-output').textContent, /Run ID \(processing job for this turn\)r-demo/);
  assert.match(app.find('example-identifiers').textContent, /not Alex.*One run can have several worker attempts/);
  assert.match(payload(app, 'capture'), /Message ID: u-demo/);
  const metadata = app.find('viewport').querySelector('[data-node="capture"] .payload-meta').textContent;
  assert.match(metadata, /Speaker: Alex \(user\).*Run ID: r-demo/);
  assert.match(app.find('connections').textContent, /capture original user message \+ link to this run/);
  assert.match(app.find('example-note').textContent, /next grouped arrows.*saving.*together.*not separate service calls/);
  assert.equal(payload(app, 'dialogue'), '-');
  app.find('action-next').click();
  assert.match(app.find('example-output').textContent, /Saved message.*Saved processing job/);
  assert.match(app.find('example-note').textContent, /one database transaction.*location remains Ottawa/);
  app.dom.window.close();
});

test('action navigation interrupts playback, keeps grouped atomic transfers, and saves the exact action', () => {
  const app = guided();
  let saved;
  app.dom.window.openai = {setWidgetState: value => { saved = value; return Promise.resolve(); }};
  app.find('play').click(); app.advance(2300);
  app.find('action-next').click();
  assert.equal(app.root.dataset.playing, 'false');
  assert.equal(app.callbacks.size, 0);
  assert.equal(saved.modelContent.action, 3);
  assert.equal(saved.privateContent.beat, 2);
  assert.equal(app.find('viewport').querySelectorAll('.active-connection').length, 2);
  const {example} = fixture(app);
  assert.throws(() => example.forBeat({edges: 'save-user'}), /Missing or mismatched/);
  assert.throws(() => example.forBeat({edges: 'new-unreviewed-transfer'}), /Missing or mismatched/);
  app.dom.window.close();
});

test('action examples distinguish pending candidate, proposal and committed success', () => {
  const app = guided();
  app.root.querySelector('[data-chapter-index="2"]').click();
  assert.ok(!app.find('example-output').textContent.includes(fixture(app).data.candidate_reply));
  app.find('action-next').click();
  assert.match(app.find('example-output').textContent, /Candidate reply/);
  assert.match(app.find('example-note').textContent, /not saved or shown/);
  app.find('next').click(); app.find('action-next').click(); app.find('action-next').click();
  assert.match(app.find('example-output').textContent, /Pending changeOttawa \(v1\) -> Toronto \(v2\)/);
  assert.match(app.find('example-note').textContent, /proposal, not committed memory/);
  app.find('next').click();
  assert.ok(!app.find('example-output').textContent.includes('Saved assistant reply'));
  app.find('action-next').click();
  assert.match(app.find('example-output').textContent, /Saved assistant reply.*Saved fact change.*Saved job outcome/);
  assert.match(app.find('example-note').textContent, /assumes all guards pass.*same atomic transaction/);
  app.dom.window.close();
});
