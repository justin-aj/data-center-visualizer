import { moveToViewpoint } from './camera/viewpoints';
import {
  applyComparisonLayers,
  proposalMembership,
} from './compare/membership';
import { renderComparison } from './compare/renderer';
import { packagePath } from './config';
import {
  loadPackage,
  PackageLoadError,
  validateManifest,
  validateProposal,
} from './data/loader';
import type { ContextScene, LoadedPackage } from './data/types';
import { isContextOnlyManifest } from './data/types';
import { CONTEXT_LOSS_MESSAGE, watchContextLoss } from './export/context-loss';
import { downloadBlob, overlayLines, renderPng } from './export/png';
import {
  createContextInventoryTable,
  createInventoryTable,
} from './inventory/table';
import { buildContextLayers, FLAT_GROUND_NOTE } from './scene/context';
import { buildProposalFeatures } from './scene/proposal';
import { createRenderCore } from './scene/renderer';
import { changeMode, defaultAppState, type ComparisonMode } from './state';
import { createApproximateBanner } from './ui/banner';
import { createCategoryControls } from './ui/categories';
import {
  contextMissingMessage,
  createNoWebGlFallback,
  webGlAvailable,
} from './ui/fallback';
import { bindSceneKeyboard } from './ui/keyboard';
import { installAppLayout } from './ui/layout';

export const APP_TITLE = 'Data Center Visualizer';

export function mount(root: HTMLElement): void {
  const heading = document.createElement('h1');
  heading.textContent = APP_TITLE;
  const status = document.createElement('p');
  status.textContent = 'The 3D scene is being prepared.';
  root.replaceChildren(heading, status);
}

export async function startApp(root: HTMLElement): Promise<void> {
  installAppLayout();
  document.body.style.cssText = 'margin:0;font-family:system-ui,sans-serif';
  root.style.cssText =
    'height:100vh;display:grid;grid-template-rows:auto 1fr auto';
  const header = document.createElement('header');
  header.className = 'app-header';
  header.style.cssText = 'padding:.6rem 1rem;background:#f7f3ea;color:#1e2a31';
  const title = document.createElement('h1');
  title.textContent = APP_TITLE;
  title.style.margin = '0';
  const status = document.createElement('p');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  status.textContent = 'Loading manifest…';
  const controls = document.createElement('div');
  controls.className = 'app-controls';
  const sceneHost = document.createElement('section');
  sceneHost.className = 'scene-shell';
  sceneHost.setAttribute('aria-label', '3D comparison');
  sceneHost.style.cssText = 'position:relative;min-height:0';
  header.append(title, status, controls);
  root.replaceChildren(header, sceneHost);

  const activePackagePath = packagePath();
  const emptyContext: ContextScene = {
    ground: { elevationM: null },
    buildings: [],
    roads: [],
    railways: [],
    water: [],
    openSpace: [],
  };
  let loaded: LoadedPackage;
  try {
    loaded = await loadPackage(activePackagePath, {
      onProgress: (progress) => {
        status.textContent =
          progress.phase === 'complete'
            ? 'Scene ready.'
            : `${progress.phase} ${progress.document ?? 'package'}…`;
      },
    });
  } catch (error) {
    if (
      !(error instanceof PackageLoadError) ||
      !error.url.endsWith('/context.json')
    ) {
      status.textContent =
        error instanceof Error ? error.message : 'Package unavailable.';
      throw error;
    }
    const [manifestResponse, proposalResponse] = await Promise.all([
      fetch(`${activePackagePath}/manifest.json`),
      fetch(`${activePackagePath}/proposal.json`),
    ]);
    loaded = {
      manifest: validateManifest(await manifestResponse.json()),
      proposal: validateProposal(await proposalResponse.json()),
      context: emptyContext,
    };
    status.textContent = 'Neighborhood context unavailable. Proposal loaded.';
    sceneHost.append(contextMissingMessage());
  }

  if (!webGlAvailable()) {
    sceneHost.replaceChildren(
      createNoWebGlFallback(loaded.manifest, loaded.proposal, loaded.context),
    );
    status.textContent = '3D graphics unavailable. Static scene loaded.';
    return;
  }

  const contextOnly = isContextOnlyManifest(loaded.manifest);
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
    const baseOverlay = {
      title: loaded.manifest.title,
      version: loaded.manifest.packageVersion,
      date: state.date,
      viewpoint: loaded.manifest.viewpoints[0]?.kind ?? 'aerial',
      legend: FLAT_GROUND_NOTE,
      attribution: loaded.manifest.attribution,
      url: window.location.href,
    };
    const overlay = isContextOnlyManifest(loaded.manifest)
      ? { ...baseOverlay, packageKind: 'context-only' as const }
      : {
          ...baseOverlay,
          packageKind: 'proposal' as const,
          mode: state.mode,
          confidence: loaded.manifest.georeference.approximate
            ? 'Approximate placement'
            : 'Reviewed placement',
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
  if (!contextOnly) {
    controls.append(modeGroup, createCategoryControls(proposal.group));
    if (!isContextOnlyManifest(loaded.manifest)) {
      sceneHost.append(
        createApproximateBanner(loaded.manifest.georeference.approximate),
      );
    }
  }
  controls.append(exportButton, exportSummary);
  watchContextLoss(core.renderer.domElement, (message) => {
    status.textContent = message;
  });
  status.dataset['contextLossMessage'] = CONTEXT_LOSS_MESSAGE;

  const inventoryWrap = document.createElement('section');
  inventoryWrap.className = 'inventory-wrap';
  inventoryWrap.tabIndex = 0;
  inventoryWrap.setAttribute('aria-label', 'Scene inventory');
  inventoryWrap.append(
    contextOnly
      ? createContextInventoryTable(loaded.context, loaded.manifest)
      : createInventoryTable(loaded.proposal, loaded.manifest),
  );
  root.append(inventoryWrap);

  let viewpointIndex = 0;
  bindSceneKeyboard({
    orbit: (horizontal, vertical) => {
      core.camera.position.x += horizontal * 8;
      core.camera.position.y = Math.max(
        2,
        core.camera.position.y - vertical * 8,
      );
      core.controls.update();
      draw();
    },
    zoom: (direction) => {
      const factor = direction > 0 ? 1.12 : 0.88;
      core.camera.position
        .sub(core.controls.target)
        .multiplyScalar(factor)
        .add(core.controls.target);
      core.controls.update();
      draw();
    },
    nextViewpoint: () => {
      viewpointIndex = (viewpointIndex + 1) % loaded.manifest.viewpoints.length;
      const viewpoint = loaded.manifest.viewpoints[viewpointIndex];
      if (viewpoint)
        void moveToViewpoint(core.camera, viewpoint, [], {
          reducedMotion: true,
        }).then(draw);
    },
    previousViewpoint: () => {
      viewpointIndex =
        (viewpointIndex - 1 + loaded.manifest.viewpoints.length) %
        loaded.manifest.viewpoints.length;
      const viewpoint = loaded.manifest.viewpoints[viewpointIndex];
      if (viewpoint)
        void moveToViewpoint(core.camera, viewpoint, [], {
          reducedMotion: true,
        }).then(draw);
    },
  });
  draw();
  if (contextOnly)
    status.textContent = 'Context-only scene ready. No proposal is shown.';
}

const root = document.querySelector<HTMLElement>('#app');
if (root) void startApp(root);
