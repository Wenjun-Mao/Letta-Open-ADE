// Offline DOM-contract checks, not a substitute for browser layout/accessibility QA.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

class Element {
  constructor(tag, document) {
    this.tagName = tag;
    this.document = document;
    this.children = [];
    this.parent = null;
    this.attributes = {};
    this.dataset = {};
    this.style = {};
    this.className = '';
    this.value = '';
    this.events = {};
    this.classList = {
      toggle: (name, yes) => {
        const classes = new Set(this.className.split(' ').filter(Boolean));
        if (yes) classes.add(name); else classes.delete(name);
        this.className = [...classes].join(' ');
      },
    };
  }
  set textContent(value) { this.value = String(value); this.children = []; }
  get textContent() { return this.value + this.children.map(child => child.textContent).join(''); }
  appendChild(child) { child.parent = this; this.children.push(child); return child; }
  replaceChildren(...children) { this.children = []; this.value = ''; children.forEach(child => this.appendChild(child)); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key]; }
  addEventListener(event, callback) { this.events[event] = callback; }
  click() { this.events.click?.(); }
  scrollIntoView() {}
  matches(selector) { return selector.startsWith('.') && this.className.split(' ').includes(selector.slice(1)); }
  closest(selectors) {
    for (let node = this; node; node = node.parent) {
      if (selectors.split(',').some(selector => node.matches(selector))) return node;
    }
    return null;
  }
  getBoundingClientRect() { return this.bounds || {left: 0, top: 0, right: 1600, bottom: 2000, width: 1600, height: 2000}; }
}

function loadMap(width) {
  const html = fs.readFileSync(path.join(__dirname, 'ade-capability-map.html'), 'utf8');
  const data = JSON.parse(html.match(/<script type="application\/json" id="inventory-data">([\s\S]*?)<\/script>/)[1]);
  const code = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(match => match[1]).join('\n');
  const document = {
    createElement: tag => new Element(tag, document),
    createElementNS: (_, tag) => new Element(tag, document),
    createTextNode: value => { const element = new Element('#text', document); element.textContent = value; return element; },
    all: () => {
      const result = [];
      const visit = node => { result.push(node); node.children.forEach(visit); };
      visit(document.body);
      return result;
    },
    getElementById: id => document.all().find(node => node.id === id || node.attributes.id === id),
    querySelectorAll: selector => document.all().filter(node => node.matches(selector)),
  };
  document.body = new Element('body', document);
  function element(id, className, parent = document.body) {
    const node = document.createElement('section');
    node.id = id;
    node.className = className;
    parent.appendChild(node);
    return node;
  }
  const drawing = element('drawing', 'drawing');
  for (const [id, className] of [['character', 'domain character'], ['memory', 'domain memory'], ['interface', 'domain interface'], ['external-tools', 'domain external'], ['support', 'support'], ['adjacent', 'adjacent'], ['connections', 'connections']]) element(id, className, drawing);
  for (const id of ['details', 'flow-controls', 'flow-note', 'mobile-links', 'footer']) element(id, '');
  element('inventory-data', '').textContent = JSON.stringify(data);
  const context = vm.createContext({
    document,
    window: {innerWidth: width, matchMedia: () => ({matches: false})},
    requestAnimationFrame: callback => callback(),
    ResizeObserver: class { constructor(callback) { this.callback = callback; } observe() { this.callback(); } },
  });
  new vm.Script(code, {filename: 'ade-capability-map.html'}).runInContext(context);
  return {document, data, model: context.AdeFlowModel};
}

for (const width of [1600, 375]) {
  test(`map controls and all node details at ${width}px (simulated DOM)`, () => {
    const {document, data} = loadMap(width);
    const pieces = [...data.entries, ...data.records];
    assert.equal(document.querySelectorAll('.node').length, pieces.length);
    assert.equal(new Set(document.querySelectorAll('.node').map(node => node.id)).size, pieces.length);
    for (const flow of data.flows) {
      document.querySelectorAll('.flow-button').find(button => button.dataset.flow === flow.id).click();
      assert.equal(document.body.dataset.flow, flow.id);
      const controls = document.querySelectorAll('.flow-button');
      assert.equal(controls.filter(button => button.getAttribute('aria-pressed') === 'true').length, 1);
      const links = document.getElementById('mobile-links').children[1];
      assert.equal(links.children.length, flow.edges.length);
      const expected = new Set(flow.edges.flatMap(edge => edge.slice(0, 2)));
      const actual = new Set(document.querySelectorAll('.node').filter(node => node.matches('.on-path')).map(node => node.id));
      assert.deepEqual(actual, expected);
      const paths = document.getElementById('connections').children.filter(node => node.dataset.edge);
      assert.equal(paths.length, width <= 760 ? 0 : flow.edges.length);
      for (const piece of pieces) {
        const button = document.getElementById(piece.id);
        button.click();
        assert.equal(button.getAttribute('aria-pressed'), 'true');
        const content = document.getElementById('details').textContent;
        assert.ok(content.includes(piece.name));
        assert.ok(content.includes(piece.status ? piece.gap : piece.authority));
        assert.equal(document.querySelectorAll('.selected').length, 1);
      }
      const endpointButton = links.children[0].children[0];
      endpointButton.click();
      assert.equal(document.getElementById(flow.edges[0][0]).getAttribute('aria-pressed'), 'true');
    }
  });
}

test('connected map names positive identities and uses the shared routes for every flow', () => {
  const {document, data, model} = loadMap(1600);
  const bounds = (left, top, width, height) => ({left, top, width, height, right: left + width, bottom: top + height});
  document.getElementById('drawing').bounds = bounds(0, 0, 900, 2500);
  document.querySelectorAll('.node').forEach((node, index) => {
    node.bounds = bounds(40 + index % 4 * 210, 70 + Math.floor(index / 4) * 200, 160, 130);
  });
  const headings = document.querySelectorAll('.routing-heading');
  headings.forEach(item => { item.bounds = bounds(20, 20, 860, 20); });
  assert.match(document.getElementById('support').textContent, /Platform support.*Runtime Coordination/);
  assert.doesNotMatch(document.getElementById('support').textContent, /outside L1-L3/);
  document.getElementById('SUP-01').click();
  assert.match(document.getElementById('details').textContent, /Platform support \/ Runtime Coordination/);
  document.getElementById('REC-RUNS').click();
  assert.match(document.getElementById('details').textContent, /Persisted record \/ ADE PostgreSQL/);

  const rect = element => { const b = element.getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height}; };
  const rects = Object.fromEntries([...data.entries, ...data.records].map(item => [item.id, rect(document.getElementById(item.id))]));
  const obstacles = {...rects, ...Object.fromEntries(headings.map((item, index) => [`@heading:${index}`, {...rect(item), text: true}]))};
  for (const flow of data.flows) {
    document.querySelectorAll('.flow-button').find(item => item.dataset.flow === flow.id).click();
    const edges = flow.edges.map(([from, to, label]) => ({id: `${from}:${to}`, from, to, label}));
    const paths = document.getElementById('connections').children.filter(item => item.dataset.edge);
    for (const original of model.route(edges, rects)) {
      const curve = model.avoidCards(original, obstacles);
      assert.equal(paths.find(item => item.dataset.edge === curve.id).getAttribute('d'), curve.d);
      for (let sample = 0; sample <= 200; sample += 1) {
        const p = model.pointAt(curve, sample / 200);
        for (const [id, obstacle] of Object.entries(obstacles)) {
          if (id === curve.from || id === curve.to) continue;
          assert.equal(p.x > obstacle.x && p.x < obstacle.x + obstacle.w && p.y > obstacle.y && p.y < obstacle.y + obstacle.h,
            false, `${flow.id}: ${curve.id} crosses ${id}`);
        }
      }
    }
  }
});
