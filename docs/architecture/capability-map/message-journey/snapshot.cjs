// Native SVG raster snapshots for layout review, not browser-engine verification.
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const webRequire = createRequire(path.join(__dirname, '../../../../apps/ade-web/package.json'));
const {JSDOM} = webRequire('jsdom');
const sharp = webRequire('sharp');
const output = path.resolve(process.argv[2] || path.join(__dirname, '.preview'));
fs.mkdirSync(output, {recursive: true});
const palette = {
  '--foreground': '#111418', '--muted-foreground': '#596575', '--border': '#ccd5e1',
  '--card': '#ffffff', '--background': '#ffffff', '--journey-active': '#0074d9',
  '--journey-surface': '#f5f7fa', '--journey-on-active': '#ffffff',
};

async function snapshot(name, width, beat, whole, chapter, guideBeat, tour = 0) {
  const dom = new JSDOM(fs.readFileSync(path.join(__dirname, 'ade-message-journey.html'), 'utf8'), {
    runScripts: 'dangerously',
    beforeParse(window) {
      Object.defineProperty(window.HTMLElement.prototype, 'clientWidth', {get: () => width});
      window.matchMedia = () => ({matches: false, addEventListener() {}});
      window.ResizeObserver = class { observe() {} disconnect() {} };
      window.requestAnimationFrame = () => 1;
      window.cancelAnimationFrame = () => {};
    },
  });
  const root = dom.window.document.getElementById('ade-moving-message');
  if (chapter == null) {
    root.querySelector(`[data-tour-index="${tour}"]`).click();
    const figure = JSON.parse(root.querySelector('[data-figure]').textContent);
    const last = Math.min(beat, figure.props.steps[tour].flow.length - 1);
    for (let index = 0; index < last; index += 1) root.querySelector('[data-next]').click();
    if ((root.querySelector('[data-viewport]').dataset.view === 'whole') !== whole) root.querySelector('[data-whole]').click();
  } else {
    root.querySelector(`[data-chapter-index="${chapter}"]`).click();
    if (guideBeat != null) dom.window.dispatchEvent(new dom.window.CustomEvent('openai:set_globals', {
      detail: {globals: {widgetState: {privateContent: {
        presentation: 3, guide: true, chapter, tour: 0, beat: guideBeat, whole: false,
      }}}},
    }));
  }
  const svg = root.querySelector('.journey-drawing');
  const dimensions = svg.getAttribute('viewBox').split(' ').map(Number);
  svg.setAttribute('width', dimensions[2]); svg.setAttribute('height', dimensions[3]);
  svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  svg.id = 'ade-moving-message';
  let css = fs.readFileSync(path.join(__dirname, 'player.css'), 'utf8');
  for (const [token, value] of Object.entries(palette)) css = css.replaceAll(`var(${token})`, value);
  css = css.replaceAll('color-mix(in srgb, #0074d9 8%, #ffffff)', '#eaf4fc')
    .replaceAll('color-mix(in srgb, #0074d9 15%, #ffffff)', '#d9eafb')
    .replaceAll('color-mix(in srgb, #0074d9 18%, transparent)', '#c9def9')
    .replaceAll('color-mix(in srgb, #0074d9 35%, transparent)', '#aaccec');
  const style = dom.window.document.createElementNS('http://www.w3.org/2000/svg', 'style');
  style.textContent = css; svg.prepend(style);
  const serialized = svg.outerHTML;
  fs.writeFileSync(path.join(output, `${name}.svg`), serialized);
  await sharp(Buffer.from(serialized)).flatten({background: '#ffffff'}).png().toFile(path.join(output, `${name}.png`));
  console.log(`${name}: ${svg.getAttribute('viewBox')}`);
  dom.window.close();
}

async function main() {
  await snapshot('send-desktop', 1440, 1, false);
  await snapshot('send-mobile', 375, 1, false);
  await snapshot('atomic-commit', 1440, 37, false);
  await snapshot('whole-architecture', 1440, 23, true);
  await snapshot('whole-send', 1440, 1, true);
  for (let tour = 0; tour < 7; tour += 1) await snapshot(`detail-flow-${tour + 1}`, 1920, 999, true, undefined, undefined, tour);
  await snapshot('acceptance-wide', 1920, 0, false, 0, 999);
  await snapshot('capture-message-wide', 1920, 0, false, 0, 1);
  await snapshot('capture-message-mobile', 320, 0, false, 0, 1);
  await snapshot('save-message-and-run', 1440, 0, false, 0, 2);
  for (let chapter = 0; chapter < 6; chapter += 1) {
    await snapshot(`guide-${chapter + 1}`, 1440, 0, false, chapter);
    await snapshot(`example-complete-${chapter + 1}`, 1440, 0, false, chapter, 999);
  }
  await snapshot('guide-mobile', 320, 0, false, 3);
  await snapshot('example-complete-mobile', 320, 0, false, 3, 999);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
