import Ajv2020, {
  type ErrorObject,
  type ValidateFunction,
} from 'ajv/dist/2020.js';

import contextSchema from '../../../contracts/context-scene.schema.json';
import packageSchema from '../../../contracts/proposal-package.schema.json';
import type { ContextScene, LoadedPackage, Manifest, Proposal } from './types';

const PACKAGE_SCHEMA_ID =
  'https://lotlens.org/contracts/proposal-package.schema.json';
const CONTEXT_SCHEMA_ID =
  'https://lotlens.org/contracts/context-scene.schema.json';
const DOCUMENT_COUNT = 3;

export type PackageDocument = 'manifest' | 'proposal' | 'context';
export type LoadingPhase = 'loading' | 'loaded' | 'complete';

export interface LoadingProgress {
  phase: LoadingPhase;
  document: PackageDocument | null;
  completed: number;
  total: typeof DOCUMENT_COUNT;
  url: string | null;
}

export interface ValidationIssue {
  path: string;
  message: string;
  keyword: string;
}

export interface LoadPackageOptions {
  fetch?: typeof globalThis.fetch;
  onProgress?: (progress: LoadingProgress) => void;
}

export class PackageValidationError extends Error {
  readonly document: PackageDocument;
  readonly issues: ValidationIssue[];

  constructor(document: PackageDocument, issues: ValidationIssue[]) {
    super(
      `Invalid ${document}.json: ${issues
        .map((issue) => `${issue.path} ${issue.message}`)
        .join('; ')}`,
    );
    this.name = 'PackageValidationError';
    this.document = document;
    this.issues = issues;
  }
}

export class PackageLoadError extends Error {
  readonly url: string;

  constructor(url: string, message: string, cause?: unknown) {
    super(`${message}: ${url}`, { cause });
    this.name = 'PackageLoadError';
    this.url = url;
  }
}

function isIsoDate(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const date = new Date(`${value}T00:00:00.000Z`);
  return !Number.isNaN(date.valueOf()) && date.toISOString().startsWith(value);
}

function isUri(value: string): boolean {
  try {
    const parsed = new URL(value);
    return parsed.protocol.length > 1;
  } catch {
    return false;
  }
}

const ajv = new Ajv2020({
  allErrors: true,
  allowUnionTypes: true,
  strict: true,
  strictTuples: false,
  strictTypes: false,
});
ajv.addFormat('date', isIsoDate);
ajv.addFormat('uri', isUri);
ajv.addSchema(packageSchema);
ajv.addSchema(contextSchema);

const manifestValidator = ajv.compile({
  $ref: `${PACKAGE_SCHEMA_ID}#/$defs/manifest`,
});
const proposalValidator = ajv.compile({
  $ref: `${PACKAGE_SCHEMA_ID}#/$defs/proposal`,
});
const contextValidator = ajv.compile({ $ref: CONTEXT_SCHEMA_ID });

function escapePointerPart(part: string): string {
  return part.replaceAll('~', '~0').replaceAll('/', '~1');
}

function issuePath(error: ErrorObject): string {
  if (error.keyword === 'required') {
    const missingProperty = error.params['missingProperty'];
    if (typeof missingProperty === 'string') {
      return `${error.instancePath}/${escapePointerPart(missingProperty)}`;
    }
  }
  return error.instancePath || '/';
}

function validationIssues(
  errors: ErrorObject[] | null | undefined,
): ValidationIssue[] {
  return (errors ?? []).map((error) => ({
    path: issuePath(error),
    message: error.message ?? 'does not match the contract',
    keyword: error.keyword,
  }));
}

function validate<T>(
  document: PackageDocument,
  validator: ValidateFunction,
  value: unknown,
): T {
  if (validator(value)) return value as T;
  throw new PackageValidationError(
    document,
    validationIssues(validator.errors),
  );
}

export function validateManifest(value: unknown): Manifest {
  return validate<Manifest>('manifest', manifestValidator, value);
}

export function validateProposal(value: unknown): Proposal {
  return validate<Proposal>('proposal', proposalValidator, value);
}

export function validateContext(value: unknown): ContextScene {
  return validate<ContextScene>('context', contextValidator, value);
}

function documentUrl(baseUrl: string, document: PackageDocument): string {
  return `${baseUrl.replace(/\/+$/, '')}/${document}.json`;
}

async function fetchJson(
  url: string,
  fetcher: typeof globalThis.fetch,
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetcher(url);
  } catch (error) {
    throw new PackageLoadError(url, 'Could not fetch package document', error);
  }

  if (!response.ok) {
    throw new PackageLoadError(
      url,
      `Package document returned HTTP ${response.status}`,
    );
  }

  try {
    return (await response.json()) as unknown;
  } catch (error) {
    throw new PackageLoadError(
      url,
      'Package document is not valid JSON',
      error,
    );
  }
}

export async function loadPackage(
  baseUrl: string,
  options: LoadPackageOptions = {},
): Promise<LoadedPackage> {
  const fetcher = options.fetch ?? globalThis.fetch;
  if (!fetcher) {
    throw new PackageLoadError(baseUrl, 'No fetch function is available');
  }

  const documents: PackageDocument[] = ['manifest', 'proposal', 'context'];
  const loaded: Partial<LoadedPackage> = {};

  for (const [index, document] of documents.entries()) {
    const url = documentUrl(baseUrl, document);
    options.onProgress?.({
      phase: 'loading',
      document,
      completed: index,
      total: DOCUMENT_COUNT,
      url,
    });

    const value = await fetchJson(url, fetcher);
    if (document === 'manifest') loaded.manifest = validateManifest(value);
    if (document === 'proposal') loaded.proposal = validateProposal(value);
    if (document === 'context') loaded.context = validateContext(value);

    options.onProgress?.({
      phase: 'loaded',
      document,
      completed: index + 1,
      total: DOCUMENT_COUNT,
      url,
    });
  }

  options.onProgress?.({
    phase: 'complete',
    document: null,
    completed: DOCUMENT_COUNT,
    total: DOCUMENT_COUNT,
    url: null,
  });

  return loaded as LoadedPackage;
}
