import { sceneStyle } from '../scene/style';

export const APPROXIMATE_BANNER_TEXT =
  'Approximate placement — this scene is not survey-accurate.';

export function createApproximateBanner(approximate: boolean): HTMLDivElement {
  const banner = document.createElement('div');
  banner.setAttribute('role', 'status');
  banner.setAttribute('aria-live', 'polite');
  banner.textContent = approximate ? APPROXIMATE_BANNER_TEXT : '';
  banner.hidden = !approximate;
  banner.style.cssText = [
    'position:absolute',
    'inset:1rem auto auto 50%',
    'transform:translateX(-50%)',
    'z-index:20',
    'max-width:min(34rem,calc(100% - 2rem))',
    'padding:0.65rem 0.9rem',
    'border:2px solid currentColor',
    'border-radius:0.35rem',
    `background:${sceneStyle.uiSurface}`,
    `color:${sceneStyle.uiText}`,
    'font:700 0.9rem/1.3 system-ui,sans-serif',
    'text-align:center',
  ].join(';');
  return banner;
}
