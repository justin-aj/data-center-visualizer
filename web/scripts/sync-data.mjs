import { cp, mkdir, readdir, rm } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repositoryRoot = resolve(webRoot, '..');

const copies = [
  {
    label: 'published packages',
    source: join(repositoryRoot, 'data', 'published'),
    destination: join(webRoot, 'public', 'data'),
  },
  {
    label: 'contract fixtures',
    source: join(repositoryRoot, 'contracts', 'fixtures'),
    destination: join(webRoot, 'public', 'fixtures'),
  },
];

async function copyDirectoryContents({ label, source, destination }) {
  await rm(destination, { recursive: true, force: true });
  await mkdir(destination, { recursive: true });

  let entries;
  try {
    entries = await readdir(source, { withFileTypes: true });
  } catch (error) {
    if (error && error.code === 'ENOENT') {
      console.log(`sync-data: no ${label} found`);
      return;
    }
    throw error;
  }

  for (const entry of entries) {
    await cp(join(source, entry.name), join(destination, entry.name), {
      recursive: true,
      force: true,
    });
  }

  console.log(`sync-data: copied ${entries.length} ${label} item(s)`);
}

for (const copy of copies) {
  await copyDirectoryContents(copy);
}
