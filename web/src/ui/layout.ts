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
