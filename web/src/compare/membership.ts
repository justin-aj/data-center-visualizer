import type { Object3D } from 'three';

import type { Proposal } from '../data/types';

export const CONTEXT_LAYER = 0;
export const CURRENT_LAYER = 1;
export const PROPOSED_LAYER = 2;

export interface FeatureMembership {
  current: Set<string>;
  proposed: Set<string>;
}

export function proposalMembership(proposal: Proposal): FeatureMembership {
  const replaced = new Set(
    proposal.features.flatMap((feature) => feature.replaces),
  );
  const modifiedReplaced = new Set(
    proposal.features
      .filter((feature) => feature.state === 'modified')
      .flatMap((feature) => feature.replaces),
  );
  const current = new Set<string>();
  const proposed = new Set<string>();

  for (const feature of proposal.features) {
    if (
      feature.state === 'existing' ||
      feature.state === 'removed' ||
      modifiedReplaced.has(feature.id)
    ) {
      current.add(feature.id);
    }
    if (
      feature.state === 'proposed' ||
      feature.state === 'modified' ||
      (feature.state === 'existing' && !replaced.has(feature.id))
    ) {
      proposed.add(feature.id);
    }
  }
  return { current, proposed };
}

export function applyComparisonLayers(
  root: Object3D,
  membership: FeatureMembership,
): void {
  root.traverse((object) => {
    const featureId = object.userData['featureId'];
    if (typeof featureId !== 'string') return;
    object.layers.disableAll();
    if (membership.current.has(featureId)) object.layers.enable(CURRENT_LAYER);
    if (membership.proposed.has(featureId))
      object.layers.enable(PROPOSED_LAYER);
  });
}
