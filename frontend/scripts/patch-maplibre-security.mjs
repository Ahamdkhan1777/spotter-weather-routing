// Backport upstream 1da69f3 (GHSA-jrc7-96c5-q579) without migrating MapLibre APIs.
// https://github.com/maplibre/maplibre-gl-js/commit/1da69f3cd913a39fa948708e01478663bf48bc27
// Keep the version pinned: unexpected package contents must fail installation/build.
import { createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'

const root = new URL('../node_modules/maplibre-gl/', import.meta.url)
const metadata = JSON.parse(await readFile(new URL('package.json', root), 'utf8'))
if (metadata.version !== '5.24.0') throw new Error('Review the MapLibre security backport before changing its pinned version.')

const files = [
  ['src/util/dom.ts', '185a0ae3e1f09e40d3cfa2b40fa863be7b814526cea45479e89e38545c932364',
    'for (const {name, value} of elem.attributes)', 'for (const {name, value} of Array.from(elem.attributes))'],
  ['dist/maplibre-gl.js', '45a9b07a9189ce56054c620a947ccf41e291e58c95e9b61533b740aaa65ee5cb',
    'for(const{name:t,value:i}of e.attributes)', 'for(const{name:t,value:i}of Array.from(e.attributes))'],
  ['dist/maplibre-gl-csp.js', 'a1f1847bac64aa00acbf80fbb79b2c5af24d8eecaaa5e2ad14080fab81f1de95',
    'for(const{name:t,value:i}of e.attributes)', 'for(const{name:t,value:i}of Array.from(e.attributes))'],
  ['dist/maplibre-gl-dev.js', '57cd72f2ceb1d724e8f9153aff0726844728e2eeaa8ced2f040b2c44b038a138',
    'for (const { name, value } of elem.attributes)', 'for (const { name, value } of Array.from(elem.attributes))'],
  ['dist/maplibre-gl-csp-dev.js', '803295fc514e56b9752e928b9bbbd1cff09c2c9f8705bf6257d001c3c157d4dd',
    'for (const { name, value } of elem.attributes)', 'for (const { name, value } of Array.from(elem.attributes))'],
]
const digest = text => createHash('sha256').update(text).digest('hex')
const pending = []
for (const [name, hash, before, after] of files) {
  const path = new URL(name, root)
  const text = await readFile(path, 'utf8')
  if (digest(text) === hash && text.split(before).length === 2) {
    pending.push([path, text.replace(before, after)])
  } else if (text.split(after).length !== 2 || digest(text.replace(after, before)) !== hash) {
    throw new Error(`Unexpected MapLibre contents in ${name}; refusing to apply an unverified security backport.`)
  }
}
// Validate every target before changing any file; repeat invocations are safe.
for (const [path, text] of pending) await writeFile(path, text, 'utf8')
console.log(`MapLibre 5.24.0 attribution security backport verified (${pending.length} files patched).`)
