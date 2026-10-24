import { moveToViewpoint } from './camera/viewpoints';
import {
  applyComparisonLayers,
  proposalMembership,
} from './compare/membership';
import { renderComparison } from './compare/renderer';
import { loadPackage } from './data/loader';
import { CONTEXT_LOSS_MESSAGE, watchContextLoss } from './export/context-loss';
import { downloadBlob, overlayLines, renderPng } from './export/png';
import { buildContextLayers, FLAT_GROUND_NOTE } from './scene/context';
import { buildProposalFeatures } from './scene/proposal';
import { createRenderCore } from './scene/renderer';
import { changeMode, defaultAppState, type ComparisonMode } from './state';
import { createApproximateBanner } from './ui/banner';
import { createCategoryControls } from './ui/categories';

export const APP_TITLE = 'Data Center Visualizer';

export function mount(root: HTMLElement): void {
  const heading = document.createElement('h1');
  heading.textContent = APP_TITLE;
  const status = document.createElement('p');
  status.textContent = 'The 3D scene is being prepared.';
  root.replaceChildren(heading, status);
}

export async function startApp(root: HTMLElement): Promise<void> {
  document.body.style.cssText = 'margin:0;font-family:system-ui,sans-serif';
  root.style.cssText = 'height:100vh;display:grid;grid-template-rows:auto 1fr';
  const header = document.createElement('header');
  header.style.cssText = 'padding:.6rem 1rem;background:#f7f3ea;color:#1e2a31';
  const title = document.createElement('h1');
  title.textContent = APP_TITLE;
  title.style.margin = '0';
  const status = document.createElement('p');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  status.textContent = 'Loading manifest…';
  const controls = document.createElement('div');
  const sceneHost = document.createElement('section');
  sceneHost.setAttribute('aria-label', '3D comparison');
  sceneHost.style.cssText = 'position:relative;min-height:0';
  header.append(title, status, controls);
  root.replaceChildren(header, sceneHost);

  const loaded = await loadPackage('/fixtures/synthetic-site', {
    onProgress: (progress) => {
      status.textContent =
        progress.phase === 'complete'
          ? 'Scene ready.'
          : `${progress.phase} ${progress.document ?? 'package'}…`;
    },
  });
  const core = createRenderCore(sceneHost);
  const oldGround = core.scene.getObjectByName('Flat demonstration ground');
  if (oldGround) oldGround.visible = false;
  const context = buildContextLayers(
    loaded.context,
    loaded.manifest.contextRadiusM,
  );
  const proposal = buildProposalFeatures(loaded.proposal, 'full');
  applyComparisonLayers(proposal.group, proposalMembership(loaded.proposal));
  core.scene.add(context.group, proposal.group);
  core.controls.maxDistance = loaded.manifest.contextRadiusM * 2;
  const firstViewpoint = loaded.manifest.viewpoints[0];
  if (!firstViewpoint) throw new Error('The package has no viewpoint.');
  await moveToViewpoint(core.camera, firstViewpoint, [], {
    reducedMotion: true,
  });

  let state = structuredClone(defaultAppState);
  const draw = (): void => {
    renderComparison(
      core.renderer,
      core.scene,
      core.camera,
      state.mode,
      sceneHost.clientWidth,
      sceneHost.clientHeight,
    );
  };
  core.controls.addEventListener('change', draw);

  const modeGroup = document.createElement('fieldset');
  const modeLegend = document.createElement('legend');
  modeLegend.textContent = 'View';
  modeGroup.append(modeLegend);
  for (const mode of ['current', 'proposed', 'split'] as const) {
    const label = document.createElement('label');
    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'comparison-mode';
    radio.value = mode;
    radio.checked = mode === state.mode;
    radio.addEventListener('change', () => {
      state = changeMode(state, mode as ComparisonMode);
      status.textContent = `${mode} view.`;
      draw();
    });
    label.append(radio, ` ${mode} `);
    modeGroup.append(label);
  }

  const exportSummary = document.createElement('output');
  exportSummary.dataset['testid'] = 'export-summary';
  const exportButton = document.createElement('button');
  exportButton.type = 'button';
  exportButton.textContent = 'Download PNG';
  exportButton.addEventListener('click', () => {
    const overlay = {
      title: loaded.manifest.title,
      version: loaded.manifest.packageVersion,
      date: state.date,
      mode: state.mode,
      viewpoint: loaded.manifest.viewpoints[0]?.kind ?? 'aerial',
      legend: FLAT_GROUND_NOTE,
      attribution: loaded.manifest.attribution,
      confidence: loaded.manifest.georeference.approximate
        ? 'Approximate placement'
        : 'Reviewed placement',
      url: window.location.href,
    };
    exportSummary.value = overlayLines(overlay).join(' | ');
    void renderPng(core.renderer, core.scene, core.camera, {
      width: 1_200,
      height: 800,
      overlay,
    })
      .then((blob) => downloadBlob(blob, 'data-center-visualizer.png'))
      .catch((error: unknown) => {
        status.textContent =
          error instanceof Error ? error.message : 'PNG export failed.';
      });
  });
  controls.append(
    modeGroup,
    createCategoryControls(proposal.group),
    exportButton,
    exportSummary,
  );
  sceneHost.append(
    createApproximateBanner(loaded.manifest.georeference.approximate),
  );
  watchContextLoss(core.renderer.domElement, (message) => {
    status.textContent = message;
  });
  status.dataset['contextLossMessage'] = CONTEXT_LOSS_MESSAGE;
  draw();
}

const root = document.querySelector<HTMLElement>('#app');
if (root) void startApp(root);
