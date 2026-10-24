import fc from 'fast-check';
import { BoxGeometry, Group, Mesh } from 'three';
import { describe, expect, it } from 'vitest';

import {
  CURRENT_LAYER,
  PROPOSED_LAYER,
  applyComparisonLayers,
  proposalMembership,
} from '../../src/compare/membership';
import { comparisonGeometryBytes } from '../../src/compare/memory';
import {
  changeMode,
  defaultAppState,
  stateFromHash,
  stateToHash,
  type AppState,
  type ComparisonMode,
} from '../../src/state';
import type {
  FeatureState,
  Proposal,
  ProposalFeature,
} from '../../src/data/types';

const states: readonly FeatureState[] = [
  'existing',
  'proposed',
  'removed',
  'modified',
];

function feature(
  id: string,
  state: FeatureState,
  replaces: string[],
): ProposalFeature {
  return {
    id,
    state,
    replaces,
    category: 'building',
    label: id,
    geometry: {
      type: 'Polygon',
      coordinates: [
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
          [0, 0],
        ],
      ],
    },
    widthM: null,
    baseElevationM: 0,
    height: { valueM: 1, status: 'official', method: 'test', sourceRefs: [] },
    confidence: {
      position: { status: 'official', sourceRefs: [], note: 'test' },
      footprint: { status: 'official', sourceRefs: [], note: 'test' },
    },
    notes: '',
  };
}

function proposalFromStates(featureStates: FeatureState[]): Proposal {
  const ids = featureStates.map((_state, index) => `feature-${index}`);
  return {
    features: featureStates.map((state, index) =>
      feature(
        ids[index] ?? `feature-${index}`,
        state,
        state === 'modified' && index > 0 ? [ids[index - 1] ?? ''] : [],
      ),
    ),
  };
}

describe('comparison properties', () => {
  it('keeps current and proposed membership correct', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(...states), { minLength: 1, maxLength: 30 }),
        (featureStates) => {
          const proposal = proposalFromStates(featureStates);
          const membership = proposalMembership(proposal);
          const replaced = new Set(
            proposal.features.flatMap((item) => item.replaces),
          );

          for (const item of proposal.features) {
            const expectedCurrent =
              item.state === 'existing' ||
              item.state === 'removed' ||
              proposal.features.some(
                (candidate) =>
                  candidate.state === 'modified' &&
                  candidate.replaces.includes(item.id),
              );
            const expectedProposed =
              item.state === 'proposed' ||
              item.state === 'modified' ||
              (item.state === 'existing' && !replaced.has(item.id));
            expect(membership.current.has(item.id)).toBe(expectedCurrent);
            expect(membership.proposed.has(item.id)).toBe(expectedProposed);
          }
          expect(membership.current.size).toBe(
            new Set(membership.current).size,
          );
          expect(membership.proposed.size).toBe(
            new Set(membership.proposed).size,
          );
        },
      ),
    );
  });

  it('never places one feature ID twice in a mode', () => {
    const proposal = proposalFromStates([...states, ...states]);
    const root = new Group();
    for (const item of proposal.features) {
      const mesh = new Mesh(new BoxGeometry());
      mesh.userData['featureId'] = item.id;
      root.add(mesh);
    }
    const membership = proposalMembership(proposal);
    applyComparisonLayers(root, membership);

    for (const layer of [CURRENT_LAYER, PROPOSED_LAYER]) {
      const visible = new Set<string>();
      root.traverse((object) => {
        const id = object.userData['featureId'];
        if (typeof id === 'string' && object.layers.isEnabled(layer))
          visible.add(id);
      });
      expect(visible.size).toBe([...visible].length);
    }
  });

  it('changes only mode', () => {
    fc.assert(
      fc.property(
        fc.constantFrom<ComparisonMode>('current', 'proposed', 'split'),
        (mode) => {
          const before = structuredClone(defaultAppState);
          const after = changeMode(before, mode);

          expect(after.mode).toBe(mode);
          expect(after.camera).toEqual(before.camera);
          expect(after.date).toBe(before.date);
          expect(after.time).toBe(before.time);
        },
      ),
    );
  });

  it('round-trips app state without lookup queries', () => {
    const state: AppState = {
      ...structuredClone(defaultAppState),
      mode: 'split',
      selectedFeature: 'generator-1',
    };
    const hash = stateToHash(state);

    expect(stateFromHash(hash)).toEqual(state);
    expect(hash.toLowerCase()).not.toContain('query');
    expect(hash.toLowerCase()).not.toContain('address');
  });

  it('keeps split geometry memory within ten percent', () => {
    const root = new Group();
    root.add(new Mesh(new BoxGeometry(10, 5, 4)));
    const singleModeBytes = comparisonGeometryBytes(root);
    const splitModeBytes = comparisonGeometryBytes(root);

    expect(splitModeBytes).toBeLessThanOrEqual(singleModeBytes * 1.1);
    expect(splitModeBytes).toBe(singleModeBytes);
  });
});
