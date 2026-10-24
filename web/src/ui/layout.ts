import { OVERLAY_CSS } from './overlay';

export function installAppLayout(): void {
  if (document.querySelector('[data-app-layout]')) return;
  const style = document.createElement('style');
  style.dataset['appLayout'] = 'true';
  style.textContent = `
    * { box-sizing: border-box; }
    body { background: #dce7ef; color: #1e2a31; }
    button, input { font: inherit; }
    button, label { min-height: 2.5rem; }
    :focus-visible { outline: 3px solid #174f78; outline-offset: 3px; }
    #app { min-width: 320px; }
    .app-header { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
    .app-header h1 { font-size: clamp(1.1rem, 3vw, 1.8rem); }
    .app-controls { display: flex; gap: .7rem; align-items: center; flex-wrap: wrap; }
    .app-controls fieldset { display: flex; gap: .4rem; margin: 0; }
    .scene-shell { min-height: 55vh; }
    .inventory-wrap { max-height: 28vh; overflow: auto; background: #f7f3ea; }
    table { width: 100%; border-collapse: collapse; font-size: .85rem; }
    caption { text-align: left; font-weight: 700; padding: .5rem; }
    th, td { padding: .4rem; border: 1px solid #6b625b; text-align: left; }
    .app-header h1 { letter-spacing: -.01em; }
    .app-tagline { margin: .1rem 0 0; font-size: .8rem; color: #f5c7a9; }
    .app-header p[role=status] { margin-left: auto !important; }
    .app-header p[role=status] { margin: 0; padding: .3rem .8rem; border-radius: 999px;
      background: rgba(255,255,255,.12); font-size: .85rem; }
    .app-header button { border: 0; border-radius: 999px; padding: .4rem 1rem;
      background: #e8743b; color: #fff; font-weight: 600; cursor: pointer; }
    .app-header button:hover { background: #d4622b; }
    .app-header .how-link { color: #fff; font-weight: 600; text-decoration: none; padding: .4rem .9rem;
      border-radius: 999px; box-shadow: 0 0 0 2px rgba(255,255,255,.45) inset; }
    .app-header .how-link:hover { background: rgba(255,255,255,.12); }
    .app-header .focus-button { background: #fff; color: #b4532a; box-shadow: 0 0 0 2px #f07a3f inset; }
    .app-header .focus-button:hover { background: #fff1e8; }
    .inventory-wrap { padding: .4rem 1rem 1rem; }
    th { background: #ece6d9; }
    th, td { border-color: #d8d0c2 !important; }
    ${OVERLAY_CSS}
    @media (max-width: 600px) {
      #app { grid-template-rows: 1fr auto auto !important; }
      .app-header { order: 2; padding: .5rem !important; max-height: 36vh; overflow: auto; }
      .scene-shell { order: 1; min-height: 50vh; }
      .inventory-wrap { order: 3; max-height: 24vh; }
      .app-controls, .app-controls fieldset { display: grid; grid-template-columns: 1fr 1fr; }
    }
  `;
  document.head.append(style);
}
