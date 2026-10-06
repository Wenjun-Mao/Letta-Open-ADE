// Deterministic DOM/clock fixture; it does not emulate a browser layout engine.
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const webRequire = createRequire(path.join(__dirname, '../../../../apps/ade-web/package.json'));
const {JSDOM} = webRequire('jsdom');
const html = fs.readFileSync(path.join(__dirname, 'ade-message-journey.html'), 'utf8');

function player(width = 900, reducedMotion = false, inline = false, fullscreenEnabled = false, guided = false) {
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
      if (fullscreenEnabled) {
        window.HTMLElement.prototype.requestFullscreen = function () {
          window.document.fullscreenElement = this;
          window.document.dispatchEvent(new window.Event('fullscreenchange'));
          return Promise.resolve();
        };
        window.document.exitFullscreen = () => {
          window.document.fullscreenElement = null;
          window.document.dispatchEvent(new window.Event('fullscreenchange'));
          return Promise.resolve();
        };
      }
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
  function select(index) { root.querySelector(`[data-tour-index="${index}"]`).click(); }
  if (!guided) select(0);
  return {dom, root, find, advance, select, media, mediaListeners, callbacks};
}

module.exports = {player};
