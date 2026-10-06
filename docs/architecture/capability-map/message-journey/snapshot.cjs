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
  '--foreground': '#172e46', '--muted-foreground': '#52667e', '--border': '#b9cce0',
  '--card': '#ffffff', '--background': '#f8fbff', '--journey-active': '#1364d6',
};

async function snapshot(name, width, beat, whole) {
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
  for (let index = 0; index < beat; index += 1) root.querySelector('[data-next]').click();
  if (whole) root.querySelector('[data-whole]').click();
  const svg = root.querySelector('svg');
  svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  svg.id = 'ade-moving-message';
  let css = fs.readFileSync(path.join(__dirname, 'player.css'), 'utf8');
  for (const [token, value] of Object.entries(palette)) css = css.replaceAll(`var(${token})`, value);
  css = css.replaceAll('color-mix(in srgb, #1364d6 8%, #ffffff)', '#eef5ff')
    .replaceAll('color-mix(in srgb, #1364d6 18%, transparent)', '#c9def9')
    .replaceAll('color-mix(in srgb, #f8fbff 90%, transparent)', '#f8fbff');
  const style = dom.window.document.createElementNS('http://www.w3.org/2000/svg', 'style');
  style.textContent = css; svg.prepend(style);
  const serialized = svg.outerHTML;
  fs.writeFileSync(path.join(output, `${name}.svg`), serialized);
  await sharp(Buffer.from(serialized)).flatten({background: '#f8fbff'}).png().toFile(path.join(output, `${name}.png`));
  console.log(`${name}: ${svg.getAttribute('viewBox')}`);
  dom.window.close();
}

async function main() {
  await snapshot('send-desktop', 1440, 1, false);
  await snapshot('send-mobile', 375, 1, false);
  await snapshot('atomic-commit', 1440, 37, false);
  await snapshot('whole-architecture', 1440, 37, true);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
