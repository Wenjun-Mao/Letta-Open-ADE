(function () {
  'use strict';
  const root = document.getElementById('ade-moving-message');
  const figure = JSON.parse(root.querySelector('[data-figure]').textContent);
  const steps = figure.props.steps, model = globalThis.AdeFlowModel;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const state = {tour: 0, beat: 0, playing: false, whole: true, rate: 1, elapsed: 0};
  const view = globalThis.AdeFlowView.create(root, figure);
  const tours = root.querySelector('[data-tours]');
  const play = root.querySelector('[data-play]');
  const previous = root.querySelector('[data-previous]');
  const next = root.querySelector('[data-next]');
  const replay = root.querySelector('[data-replay]');
  const mode = root.querySelector('[data-whole]');
  const speed = root.querySelector('[data-speed]');
  const count = root.querySelector('[data-count]');
  const progress = root.querySelector('[data-progress]');
  const caption = root.querySelector('[data-caption]');
  const narration = root.querySelector('[data-narration]');
  const fullscreen = root.querySelector('[data-fullscreen]');
  let frame = 0, lastTime = null;
  const tourButtons = steps.map((step, index) => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'btn journey-tour';
    button.dataset.tourIndex = String(index);
    button.textContent = step.label.replace(/^\d+ - /, '');
    button.setAttribute('aria-label', step.label);
    const line = document.createElement('span');
    line.className = 'tour-progress'; line.setAttribute('aria-hidden', 'true'); button.appendChild(line);
    button.addEventListener('click', () => { state.tour = index; jump(0); });
    tours.appendChild(button); return button;
  });
  const moduleDetails = root.querySelector('[data-module-details]');
  model.flatten(figure.props.layout).forEach(node => {
    const label = document.createElement('dt'), description = document.createElement('dd');
    label.textContent = node.label; description.textContent = node.sub;
    moduleDetails.append(label, description);
  });

  function restore(saved) {
    const selected = saved?.privateContent;
    if (selected?.presentation !== 2 || !Number.isInteger(selected.tour) || !steps[selected.tour]) return false;
    state.tour = selected.tour;
    state.beat = Number.isInteger(selected.beat)
      ? Math.max(0, Math.min(steps[state.tour].flow.length - 1, selected.beat)) : 0;
    state.whole = typeof selected.whole === 'boolean' ? selected.whole : true;
    state.playing = false; state.elapsed = 0;
    return true;
  }
  function save() {
    if (!window.openai?.setWidgetState) return;
    window.openai.setWidgetState({
      modelContent: {tour: steps[state.tour].label, step: state.beat + 1},
      privateContent: {presentation: 2, tour: state.tour, beat: state.beat, whole: state.whole},
    }).catch(() => {});
  }

  function paint() {
    const selected = steps[state.tour];
    tourButtons.forEach((button, index) => button.setAttribute('aria-pressed', String(index === state.tour)));
    caption.textContent = selected.caption;
    narration.textContent = model.narration(selected, state.beat);
    count.textContent = `Step ${state.beat + 1} of ${selected.flow.length}`;
    progress.setAttribute('aria-valuemax', selected.flow.length);
    progress.setAttribute('aria-valuenow', state.beat + 1);
    progress.firstElementChild.style.width = `${(state.beat + 1) / selected.flow.length * 100}%`;
    play.textContent = reduced.matches ? 'Motion reduced' : state.playing ? 'Pause' : 'Play';
    play.disabled = reduced.matches;
    play.setAttribute('aria-pressed', String(state.playing));
    mode.setAttribute('aria-pressed', String(state.whole));
    mode.textContent = state.whole ? 'Follow this step' : 'Whole architecture';
    previous.disabled = state.beat === 0;
    next.disabled = state.beat === selected.flow.length - 1;
    root.dataset.tour = String(state.tour);
    root.dataset.beat = String(state.beat);
    root.dataset.playing = String(state.playing);
    view.render(state);
    updateProgress();
    view.position(state.playing || state.elapsed ? Math.min(1, state.elapsed / ((selected.flow[state.beat].ms || figure.props.speed) * 0.8)) : 0.5);
  }
  function stopFrame() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0; lastTime = null;
  }
  function updateProgress(fraction = Math.min(1, state.elapsed / (steps[state.tour].flow[state.beat].ms || figure.props.speed))) {
    tourButtons.forEach((button, index) => {
      button.lastElementChild.style.transform = `scaleX(${index === state.tour ? (state.beat + fraction) / steps[state.tour].flow.length : 0})`;
    });
  }
  function tick(time) {
    if (!state.playing || reduced.matches) { stopFrame(); return; }
    if (lastTime != null) state.elapsed += Math.min(200, time - lastTime) * state.rate;
    lastTime = time;
    const duration = steps[state.tour].flow[state.beat].ms || figure.props.speed;
    updateProgress(Math.min(1, state.elapsed / duration));
    view.position(Math.min(1, state.elapsed / (duration * 0.8)));
    if (state.elapsed >= duration) {
      if (state.beat === steps[state.tour].flow.length - 1) {
        state.playing = false; state.elapsed = duration; stopFrame(); paint(); updateProgress(1); save(); return;
      }
      state.beat += 1; state.elapsed = 0; paint();
    }
    frame = requestAnimationFrame(tick);
  }
  function startFrame() {
    stopFrame();
    if (state.playing && !reduced.matches) frame = requestAnimationFrame(tick);
  }
  function jump(beat) {
    state.beat = beat; state.elapsed = 0; state.playing = false;
    stopFrame(); paint(); save();
  }
  play.addEventListener('click', () => {
    if (reduced.matches) return;
    state.playing = !state.playing;
    if (state.playing && state.beat === steps[state.tour].flow.length - 1) {
      state.beat = 0; state.elapsed = 0;
    }
    const elapsed = state.elapsed;
    paint();
    view.position(state.playing || elapsed ? Math.min(1, elapsed / ((steps[state.tour].flow[state.beat].ms || figure.props.speed) * 0.8)) : 0.5);
    startFrame(); save();
  });
  previous.addEventListener('click', () => jump(Math.max(0, state.beat - 1)));
  next.addEventListener('click', () => jump(Math.min(steps[state.tour].flow.length - 1, state.beat + 1)));
  replay.addEventListener('click', () => {
    state.beat = 0; state.elapsed = 0; state.playing = !reduced.matches;
    paint(); startFrame(); save();
  });
  mode.addEventListener('click', () => {
    state.whole = !state.whole;
    paint();
    view.position(state.playing || state.elapsed ? Math.min(1, state.elapsed / ((steps[state.tour].flow[state.beat].ms || figure.props.speed) * 0.8)) : 0.5);
    save();
  });
  speed.addEventListener('click', () => {
    state.rate = state.rate === 1 ? 2 : 1;
    speed.textContent = `${state.rate}x`;
    speed.setAttribute('aria-label', `Playback speed ${state.rate}x`);
  });
  reduced.addEventListener('change', () => {
    if (reduced.matches) { state.playing = false; stopFrame(); }
    paint();
  });
  fullscreen.hidden = !root.hasAttribute('data-standalone') || !root.requestFullscreen;
  fullscreen.addEventListener('click', async () => {
    try {
      if (document.fullscreenElement === root) await document.exitFullscreen();
      else await root.requestFullscreen();
    } catch {
      narration.textContent = 'Full screen is unavailable here; the chart remains playable.';
    }
  });
  document.addEventListener('fullscreenchange', () => {
    fullscreen.textContent = document.fullscreenElement === root ? 'Exit full screen' : 'Full screen';
    fullscreen.setAttribute('aria-label', fullscreen.textContent);
    paint();
  });
  window.addEventListener('openai:set_globals', event => {
    if (!restore(event.detail?.globals?.widgetState)) return;
    stopFrame(); paint();
  });
  restore(window.openai?.widgetState);
  paint();
  let width = root.querySelector('[data-viewport]').clientWidth;
  const observer = new ResizeObserver(() => {
    const updated = root.querySelector('[data-viewport]').clientWidth;
    if (updated === width) return;
    width = updated; paint();
    view.position(state.playing || state.elapsed ? Math.min(1, state.elapsed / ((steps[state.tour].flow[state.beat].ms || figure.props.speed) * 0.8)) : 0.5);
  });
  observer.observe(root.querySelector('[data-viewport]'));
  window.addEventListener('pagehide', () => { stopFrame(); observer.disconnect(); }, {once: true});
})();
