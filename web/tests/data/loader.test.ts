import { readdir, readFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it, vi } from 'vitest';

import contextFixture from '../../../contracts/fixtures/synthetic-site/context.json';
import manifestContextOnlyFixture from '../../../contracts/fixtures/synthetic-site/manifest.context-only.json';
import manifestFixture from '../../../contracts/fixtures/synthetic-site/manifest.json';
import proposalFixture from '../../../contracts/fixtures/synthetic-site/proposal.json';
import {
  loadPackage,
  PackageValidationError,
  validateContext,
  validateManifest,
  validateProposal,
  type LoadingProgress,
  type PackageDocument,
  type PackageLoadError,
} from '../../src/data/loader';

const repositoryRoot = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  '..',
  '..',
);
const invalidFixtureRoot = join(
  repositoryRoot,
  'contracts',
  'fixtures',
  'invalid',
);
const publishedRoot = join(repositoryRoot, 'data', 'published');

async function readJson(path: string): Promise<unknown> {
  return JSON.parse(await readFile(path, 'utf8')) as unknown;
}

function documentFromName(name: string): PackageDocument {
  if (name.startsWith('manifest-')) return 'manifest';
  if (name.startsWith('proposal-')) return 'proposal';
  if (name.startsWith('context-')) return 'context';
  throw new Error(`Unknown fixture document: ${name}`);
}

function validateDocument(document: PackageDocument, value: unknown): unknown {
  if (document === 'manifest') return validateManifest(value);
  if (document === 'proposal') return validateProposal(value);
  return validateContext(value);
}

async function packageDirectories(root: string): Promise<string[]> {
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch (error) {
    if (error instanceof Error && 'code' in error && error.code === 'ENOENT') {
      return [];
    }
    throw error;
  }

  const directories: string[] = [];
  for (const entry of entries) {
    const path = join(root, entry.name);
    if (!entry.isDirectory()) continue;
    const children = await readdir(path);
    if (children.includes('manifest.json')) directories.push(path);
    directories.push(...(await packageDirectories(path)));
  }
  return directories;
}

describe('package validation', () => {
  it('accepts every synthetic fixture document', () => {
    expect(validateManifest(manifestFixture).projectId).toBe(
      'synthetic-civic-site',
    );
    const contextOnly = validateManifest(manifestContextOnlyFixture);
    expect(contextOnly.packageKind).toBe('context-only');
    expect('georeference' in contextOnly).toBe(false);
    expect(validateProposal(proposalFixture).features.length).toBeGreaterThan(
      0,
    );
    expect(validateContext(contextFixture).buildings.length).toBeGreaterThan(0);
  });

  it('reports the field path for invalid input', () => {
    const invalidManifest = { ...manifestFixture, title: '' };

    expect(() => validateManifest(invalidManifest)).toThrow(
      expect.objectContaining({
        issues: expect.arrayContaining([
          expect.objectContaining({ path: '/title' }),
        ]),
      }),
    );
  });

  it('rejects every invalid contract fixture', async () => {
    const names = (await readdir(invalidFixtureRoot)).filter((name) =>
      name.endsWith('.json'),
    );
    expect(names.length).toBeGreaterThan(0);

    for (const name of names) {
      const document = documentFromName(name);
      const value = await readJson(join(invalidFixtureRoot, name));

      try {
        validateDocument(document, value);
        expect.unreachable(`${name} should fail validation`);
      } catch (error) {
        expect(error, name).toBeInstanceOf(PackageValidationError);
        const validationError = error as PackageValidationError;
        expect(validationError.issues.length, name).toBeGreaterThan(0);
        expect(
          validationError.issues.every((issue) => issue.path.startsWith('/')),
          name,
        ).toBe(true);
      }
    }
  });

  it('accepts every published package', async () => {
    const directories = await packageDirectories(publishedRoot);
    for (const directory of directories) {
      validateManifest(await readJson(join(directory, 'manifest.json')));
      validateProposal(await readJson(join(directory, 'proposal.json')));
      validateContext(await readJson(join(directory, 'context.json')));
    }
  });
});

describe('package loading', () => {
  it('loads documents in order and reports progress', async () => {
    const fixtures: Record<PackageDocument, unknown> = {
      manifest: manifestFixture,
      proposal: proposalFixture,
      context: contextFixture,
    };
    const fetcher = vi.fn(async (input: string | URL | Request) => {
      const name = new URL(String(input)).pathname.split('/').at(-1);
      const document = name?.replace('.json', '') as PackageDocument;
      return new Response(JSON.stringify(fixtures[document]), {
        status: fixtures[document] ? 200 : 404,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    const progress: LoadingProgress[] = [];

    const result = await loadPackage('https://example.invalid/packages/demo/', {
      fetch: fetcher,
      onProgress: (event) => progress.push(event),
    });

    expect(result.manifest.projectId).toBe('synthetic-civic-site');
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(progress.map((event) => event.phase)).toEqual([
      'loading',
      'loaded',
      'loading',
      'loaded',
      'loading',
      'loaded',
      'complete',
    ]);
    expect(progress.at(-1)).toMatchObject({ completed: 3, total: 3 });
  });

  it('loads all three files for a context-only package', async () => {
    const fixtures: Record<PackageDocument, unknown> = {
      manifest: manifestContextOnlyFixture,
      proposal: { features: [] },
      context: contextFixture,
    };
    const fetcher = vi.fn(async (input: string | URL | Request) => {
      const name = new URL(String(input)).pathname.split('/').at(-1);
      const document = name?.replace('.json', '') as PackageDocument;
      return new Response(JSON.stringify(fixtures[document]), {
        status: fixtures[document] ? 200 : 404,
        headers: { 'Content-Type': 'application/json' },
      });
    });

    const result = await loadPackage('https://example.invalid/context-only', {
      fetch: fetcher,
    });

    expect(result.manifest.packageKind).toBe('context-only');
    expect(result.proposal.features).toEqual([]);
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(fetcher.mock.calls.map(([input]) => String(input))).toEqual([
      'https://example.invalid/context-only/manifest.json',
      'https://example.invalid/context-only/proposal.json',
      'https://example.invalid/context-only/context.json',
    ]);
  });
  it('names the URL when a document cannot load', async () => {
    const fetcher = vi.fn(async () => new Response(null, { status: 503 }));

    await expect(
      loadPackage('https://example.invalid/packages/demo', { fetch: fetcher }),
    ).rejects.toEqual(
      expect.objectContaining<Partial<PackageLoadError>>({
        name: 'PackageLoadError',
        url: 'https://example.invalid/packages/demo/manifest.json',
      }),
    );
  });
});
