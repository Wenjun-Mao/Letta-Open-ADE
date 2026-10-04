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
  getBoundingClientRect() { return {left: 0, top: 0, right: 1600, bottom: 2000, width: 1600, height: 2000}; }
}

function loadMap(width) {
  const html = fs.readFileSync(path.join(__dirname, 'ade-capability-map.html'), 'utf8');
  const data = JSON.parse(html.match(/<script type="application\/json" id="inventory-data">([\s\S]*?)<\/script>/)[1]);
  const code = html.match(/<script>([\s\S]*?)<\/script>/)[1];
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
  return {document, data};
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
