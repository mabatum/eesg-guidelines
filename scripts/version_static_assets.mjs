// Keep returning readers' navigation, search and styles in sync with each build.
// GitHub Pages caches stable resource URLs for ten minutes; content hashes let
// an updated page request the matching resources without disabling caching.
import {createHash} from 'node:crypto';
import {readFileSync, readdirSync, writeFileSync} from 'node:fs';
import {join, relative, sep} from 'node:path';

const root = 'docs-html';

function* files(directory) {
  for (const entry of readdirSync(directory, {withFileTypes: true})) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) yield* files(path);
    else if (entry.isFile()) yield path;
  }
}

const versions = new Map();
for (const path of files(root)) {
  const name = relative(root, path).split(sep).join('/');
  if (name === 'toc.js' || /^_assets\/(script|style)\/.+\.(js|css)$/.test(name)) {
    versions.set(name, createHash('sha256').update(readFileSync(path)).digest('hex').slice(0, 12));
  }
}

// Replace both HTML attributes and resource URLs in Diplodoc's page payload.
// Preserve relative prefixes so nested clinical pages use the same resources.
const resource = /(_assets\/(?:script|style)\/[^"'<>?]+?\.(?:css|js)|toc\.js)(?:\?v=[a-f0-9]+)?(?=["'])/g;
let pages = 0;
for (const path of files(root)) {
  if (!path.endsWith('.html')) continue;
  const html = readFileSync(path, 'utf8');
  const versioned = html.replace(resource, (url, name) => {
    const hash = versions.get(name);
    if (!hash) throw new Error(`Missing built resource: ${name} (${path})`);
    return `${name}?v=${hash}`;
  });
  if (versioned !== html) writeFileSync(path, versioned);
  pages += 1;
}
console.log(`Versioned ${versions.size} resources across ${pages} pages.`);
