import { describe, expect, it } from 'vitest';

import { APP_TITLE, mount } from '../src/main';

describe('web app', () => {
  it('mounts an accessible title and status', () => {
    const root = document.createElement('main');

    mount(root);

    expect(root.querySelector('h1')?.textContent).toBe(APP_TITLE);
    expect(root.textContent).toContain('3D scene');
  });
});
