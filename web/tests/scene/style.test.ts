import { describe, expect, it } from 'vitest';

import { contrastRatio, sceneStyle } from '../../src/scene/style';

describe('scene style', () => {
  it.each([
    ['main text', sceneStyle.uiText, sceneStyle.uiSurface],
    ['proposal badge', sceneStyle.badgeText, sceneStyle.proposal],
    ['focus ring', sceneStyle.focus, sceneStyle.uiSurface],
    ['building outline', sceneStyle.contextOutline, sceneStyle.ground],
  ])('%s has WCAG AA contrast', (_name, foreground, background) => {
    expect(contrastRatio(foreground, background)).toBeGreaterThanOrEqual(4.5);
  });

  it('rejects malformed color tokens', () => {
    expect(() => contrastRatio('#fff', sceneStyle.ground)).toThrow(
      'six-digit hex color',
    );
  });
});
