import type { Object3D } from 'three';

import type { FeatureCategory } from '../data/types';

export const featureCategories: readonly FeatureCategory[] = [
  'building',
  'generator',
  'cooling',
  'electrical',
  'retaining_wall',
  'fence',
  'paving',
  'vegetation_screen',
  'other',
];

function categoryLabel(category: FeatureCategory): string {
  return category.replaceAll('_', ' ');
}

export function setCategoryVisibility(
  root: Object3D,
  category: FeatureCategory,
  visible: boolean,
): void {
  root.traverse((object) => {
    if (object.userData['category'] === category) object.visible = visible;
  });
}

export function createCategoryControls(
  sceneRoot: Object3D,
  initiallyVisible: readonly FeatureCategory[] = featureCategories,
): HTMLFieldSetElement {
  const visible = new Set(initiallyVisible);
  const fieldset = document.createElement('fieldset');
  const legend = document.createElement('legend');
  legend.textContent = 'Visible categories';
  const liveRegion = document.createElement('p');
  liveRegion.setAttribute('aria-live', 'polite');
  liveRegion.setAttribute('role', 'status');
  liveRegion.style.cssText = [
    'position:absolute',
    'width:1px',
    'height:1px',
    'padding:0',
    'margin:-1px',
    'overflow:hidden',
    'clip:rect(0,0,0,0)',
    'white-space:nowrap',
    'border:0',
  ].join(';');
  fieldset.append(legend, liveRegion);

  for (const category of featureCategories) {
    const label = document.createElement('label');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = 'visible-category';
    checkbox.value = category;
    checkbox.checked = visible.has(category);
    checkbox.addEventListener('change', () => {
      setCategoryVisibility(sceneRoot, category, checkbox.checked);
      const state = checkbox.checked ? 'shown' : 'hidden';
      liveRegion.textContent = `${categoryLabel(category)} ${state}.`;
    });
    label.append(checkbox, ` ${categoryLabel(category)}`);
    fieldset.append(label);
  }

  return fieldset;
}
