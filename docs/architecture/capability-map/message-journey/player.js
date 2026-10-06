(function () {
  'use strict';
  const root = document.getElementById('ade-moving-message');
  const figure = JSON.parse(root.querySelector('[data-figure]').textContent);
  const steps = figure.props.steps, model = globalThis.AdeFlowModel;
  const guide = globalThis.AdeJourneyGuide;
  const guidedFigure = guide.build(figure);
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const state = {guide: true, chapter: 0, tour: 0, beat: 0, playing: false, whole: true, rate: 1, elapsed: 0};
  const view = globalThis.AdeFlowView.create(root, figure);
  const guidedView = globalThis.AdeFlowView.create(root, guidedFigure);
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
  const detail = root.querySelector('[data-detail]');
  const chapterTitle = root.querySelector('[data-chapter-title]');
  const chapters = root.querySelector('[data-chapters]');
  let frame = 0, lastTime = null;
  const selected = () => state.guide ? guidedFigure.props.steps[state.chapter] : steps[state.tour];
  const currentView = () => state.guide ? guidedView : view;
  const fraction = () => state.playing || state.elapsed
    ? Math.min(1, state.elapsed / ((selected().flow[state.beat].ms || figure.props.speed) * 0.8)) : 0.5;
  const chapterButtons = guide.chapters.map((chapter, index) => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'btn journey-tour';
    button.dataset.chapterIndex = String(index);
    button.textContent = chapter.label;
    const line = document.createElement('span');
    line.className = 'tour-progress'; line.setAttribute('aria-hidden', 'true'); button.appendChild(line);
    button.addEventListener('click', () => { state.chapter = index; jump(0); });
    chapters.appendChild(button); return button;
  });
  const tourButtons = steps.map((step, index) => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'btn journey-tour';
    button.dataset.tourIndex = String(index);
    button.textContent = step.label.replace(/^\d+ - /, '');
    button.setAttribute('aria-label', step.label);
    const line = document.createElement('span');
    line.className = 'tour-progress'; line.setAttribute('aria-hidden', 'true'); button.appendChild(line);
    button.addEventListener('click', () => { state.guide = false; state.tour = index; jump(0); });
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
    if (selected?.presentation !== 3 || typeof selected.guide !== 'boolean'
      || !Number.isInteger(selected.tour) || !steps[selected.tour]
      || !Number.isInteger(selected.chapter) || !guide.chapters[selected.chapter]) return false;
    state.guide = selected.guide; state.chapter = selected.chapter;
    state.tour = selected.tour;
    const flow = state.guide ? guidedFigure.props.steps[state.chapter].flow : steps[state.tour].flow;
    state.beat = Number.isInteger(selected.beat)
      ? Math.max(0, Math.min(flow.length - 1, selected.beat)) : 0;
    state.whole = typeof selected.whole === 'boolean' ? selected.whole : true;
    state.playing = false; state.elapsed = 0;
    return true;
  }
  function save() {
    if (!window.openai?.setWidgetState) return;
    window.openai.setWidgetState({
      modelContent: {view: state.guide ? 'guided' : 'detailed',
        tour: selected().label, step: state.guide ? state.chapter + 1 : state.beat + 1},
      privateContent: {presentation: 3, guide: state.guide, chapter: state.chapter,
        tour: state.tour, beat: state.beat, whole: state.whole},
    }).catch(() => {});
  }

  function paint() {
    const step = selected();
    tourButtons.forEach((button, index) => button.setAttribute('aria-pressed', String(index === state.tour)));
    chapterButtons.forEach((button, index) => button.setAttribute('aria-pressed', String(index === state.chapter)));
    caption.textContent = step.caption;
    narration.textContent = state.guide ? guide.chapters[state.chapter].say : model.narration(step, state.beat);
    chapterTitle.textContent = state.guide ? `${state.chapter + 1}. ${step.label}` : step.label.replace(/^\d+ - /, '');
    root.querySelector('[data-view-scope]').textContent = state.guide
      ? 'Guided view: selected transfers. Provider mechanics and full atomic writes remain in the detailed map.' : '';
    count.textContent = state.guide ? `Chapter ${state.chapter + 1} of ${guide.chapters.length}` : `Step ${state.beat + 1} of ${step.flow.length}`;
    const total = state.guide ? guide.chapters.length : step.flow.length;
    const current = state.guide ? state.chapter + 1 : state.beat + 1;
    progress.setAttribute('aria-label', state.guide ? 'Reading chapter' : 'Tour step');
    progress.setAttribute('aria-valuemax', total);
    progress.setAttribute('aria-valuenow', current);
    progress.firstElementChild.style.width = `${current / total * 100}%`;
    play.textContent = reduced.matches ? 'Motion reduced' : state.playing ? 'Pause' : state.guide ? 'Play chapter' : 'Play';
    play.disabled = reduced.matches;
    play.setAttribute('aria-label', state.playing ? 'Pause playback'
      : state.guide ? 'Play this chapter; stop at its end' : 'Play this flow; stop at its end');
    play.setAttribute('aria-pressed', String(state.playing));
    mode.setAttribute('aria-pressed', String(state.whole));
    mode.textContent = state.whole ? 'Follow this step' : 'Whole architecture';
    mode.hidden = state.guide; chapters.hidden = !state.guide;
    root.querySelector('[data-alternatives]').hidden = false;
    detail.textContent = state.guide ? 'Show detailed map' : 'Guided journey';
    previous.setAttribute('aria-label', state.guide ? 'Back one chapter' : 'Back one detailed step');
    next.setAttribute('aria-label', state.guide ? 'Forward one chapter' : 'Forward one detailed step');
    replay.textContent = state.guide ? 'Replay chapter' : 'Replay';
    previous.disabled = current === 1;
    next.disabled = current === total;
    root.dataset.guide = String(state.guide);
    root.dataset.chapter = String(state.chapter);
    root.dataset.tour = String(state.tour);
    root.dataset.beat = String(state.beat);
    root.dataset.playing = String(state.playing);
    currentView().render({...state, tour: state.guide ? state.chapter : state.tour, whole: !state.guide && state.whole});
    updateProgress();
    currentView().position(fraction());
  }
  function stopFrame() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0; lastTime = null;
  }
  function updateProgress(fraction = Math.min(1, state.elapsed / (selected().flow[state.beat].ms || figure.props.speed))) {
    chapterButtons.forEach((button, index) => {
      button.lastElementChild.style.transform = `scaleX(${state.guide && index === state.chapter ? (state.beat + fraction) / selected().flow.length : 0})`;
    });
    tourButtons.forEach((button, index) => {
      button.lastElementChild.style.transform = `scaleX(${!state.guide && index === state.tour ? (state.beat + fraction) / steps[state.tour].flow.length : 0})`;
    });
  }
  function tick(time) {
    if (!state.playing || reduced.matches) { stopFrame(); return; }
    if (lastTime != null) state.elapsed += Math.min(200, time - lastTime) * state.rate;
    lastTime = time;
    const duration = selected().flow[state.beat].ms || figure.props.speed;
    updateProgress(Math.min(1, state.elapsed / duration));
    currentView().position(Math.min(1, state.elapsed / (duration * 0.8)));
    if (state.elapsed >= duration) {
      if (state.beat === selected().flow.length - 1) {
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
    if (state.playing && state.beat === selected().flow.length - 1) {
      state.beat = 0; state.elapsed = 0;
    }
    paint();
    startFrame(); save();
  });
  function move(direction) {
    if (state.guide) {
      state.chapter = Math.max(0, Math.min(guide.chapters.length - 1, state.chapter + direction));
      jump(0);
    } else jump(Math.max(0, Math.min(selected().flow.length - 1, state.beat + direction)));
  }
  previous.addEventListener('click', () => move(-1));
  next.addEventListener('click', () => move(1));
  replay.addEventListener('click', () => {
    state.beat = 0; state.elapsed = 0; state.playing = !reduced.matches;
    paint(); startFrame(); save();
  });
  mode.addEventListener('click', () => {
    state.whole = !state.whole;
    paint(); save();
  });
  detail.addEventListener('click', () => {
    if (state.guide) {
      const sourceBeat = selected().flow[state.beat].sourceBeat;
      state.guide = false; state.tour = 0; state.whole = true; jump(sourceBeat);
    } else {
      if (state.tour === 0) state.chapter = guide.chapters.findIndex(chapter => state.beat <= chapter.end);
      state.guide = true; state.tour = 0; jump(0);
    }
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
  });
  observer.observe(root.querySelector('[data-viewport]'));
  window.addEventListener('pagehide', () => { stopFrame(); observer.disconnect(); }, {once: true});
})();
