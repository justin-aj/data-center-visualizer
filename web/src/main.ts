export const APP_TITLE = 'Data Center Visualizer';

export function mount(root: HTMLElement): void {
  const heading = document.createElement('h1');
  heading.textContent = APP_TITLE;

  const status = document.createElement('p');
  status.textContent = 'The 3D scene is being prepared.';

  root.replaceChildren(heading, status);
}

const root = document.querySelector<HTMLElement>('#app');
if (root) {
  mount(root);
}
