export const DEFAULT_PACKAGE = '/data/lowell-markley/0.1.0';

export function packagePath(search = window.location.search): string {
  const parameters = new URLSearchParams(search);
  if (parameters.get('fixture') === 'synthetic-site') {
    return '/fixtures/synthetic-site';
  }
  const requested = parameters.get('package');
  if (!requested) return DEFAULT_PACKAGE;
  if (!/^[a-z0-9-]+\/\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?$/i.test(requested)) {
    return DEFAULT_PACKAGE;
  }
  return `/data/${requested}`;
}
