import { describe, expect, it } from 'vitest';

import contextFixture from '../../../contracts/fixtures/synthetic-site/context.json';
import manifestFixture from '../../../contracts/fixtures/synthetic-site/manifest.json';
import proposalFixture from '../../../contracts/fixtures/synthetic-site/proposal.json';
import { validateViewpointPlacement } from '../../src/camera/place';
import {
  validateContext,
  validateManifest,
  validateProposal,
} from '../../src/data/loader';

const manifest = validateManifest(manifestFixture);
const context = validateContext(contextFixture);
const proposal = validateProposal(proposalFixture);

describe('ground viewpoint placement', () => {
  it('allows a point in a published road corridor', () => {
    const result = validateViewpointPlacement(
      [0, -95],
      manifest,
      context,
      proposal,
    );

    expect(result).toEqual({
      valid: true,
      reason: 'valid',
      explanation: 'Public ground viewpoint ready.',
      position: [0, -95, 1.6],
    });
  });

  it('allows public open space', () => {
    const result = validateViewpointPlacement(
      [-400, 400],
      manifest,
      context,
      proposal,
    );

    expect(result.valid).toBe(true);
    expect(result.position).toEqual([-400, 400, 1.6]);
  });

  it('rejects private open space with an explanation', () => {
    const result = validateViewpointPlacement(
      [550, 100],
      manifest,
      context,
      proposal,
    );

    expect(result.reason).toBe('private-ground');
    expect(result.explanation).toContain('not marked for public access');
  });

  it('rejects points beyond the scene radius', () => {
    const result = validateViewpointPlacement(
      [1_201, 0],
      manifest,
      context,
      proposal,
    );

    expect(result.reason).toBe('out-of-radius');
    expect(result.position).toBeNull();
  });

  it('rejects points inside context footprints', () => {
    const result = validateViewpointPlacement(
      [-405, -165],
      manifest,
      context,
      proposal,
    );

    expect(result.reason).toBe('inside-footprint');
    expect(result.explanation).toContain('outside every modeled footprint');
  });

  it('rejects unlisted ground', () => {
    const result = validateViewpointPlacement(
      [0, 200],
      manifest,
      context,
      proposal,
    );

    expect(result.reason).toBe('not-public-ground');
  });
});
