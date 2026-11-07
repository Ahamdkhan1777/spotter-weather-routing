import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, mkdir, copyFile, readFile, writeFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, dirname, basename, resolve } from 'node:path'
import { spawnSync } from 'node:child_process'

const targets = ['src/util/dom.ts', 'dist/maplibre-gl.js', 'dist/maplibre-gl-csp.js',
  'dist/maplibre-gl-dev.js', 'dist/maplibre-gl-csp-dev.js']

async function removeFixture(directory, temporaryRoot) {
  if (dirname(directory) !== temporaryRoot || !basename(directory).startsWith('spotter-map-security-')) {
    throw new Error('Refusing cleanup outside the temporary security-test directory.')
  }
  await rm(directory, { recursive: true, force: true })
}

async function fixture(run) {
  const temporaryRoot = resolve(tmpdir())
  const directory = await mkdtemp(join(temporaryRoot, 'spotter-map-security-'))
  try {
    const script = join(directory, 'scripts', 'patch-maplibre-security.mjs')
    const packageRoot = join(directory, 'node_modules', 'maplibre-gl')
    await mkdir(dirname(script), { recursive: true })
    await copyFile(new URL('./patch-maplibre-security.mjs', import.meta.url), script)
    for (const file of ['package.json', ...targets]) {
      await mkdir(dirname(join(packageRoot, file)), { recursive: true })
      await copyFile(new URL(`../node_modules/maplibre-gl/${file}`, import.meta.url), join(packageRoot, file))
    }
    const invoke = () => spawnSync(process.execPath, [script], { encoding: 'utf8' })
    await run(packageRoot, invoke)
  } finally { await removeFixture(directory, temporaryRoot) }
}

test('the verified backport is idempotent', async () => {
  await fixture(async (root, invoke) => {
    assert.equal(invoke().status, 0)
    const before = await Promise.all(targets.map(file => readFile(join(root, file), 'utf8')))
    const result = invoke()
    assert.equal(result.status, 0, result.stderr)
    assert.match(result.stdout, /0 files patched/)
    assert.deepEqual(await Promise.all(targets.map(file => readFile(join(root, file), 'utf8'))), before)
  })
})

test('unexpected package versions require explicit review', async () => {
  await fixture(async (root, invoke) => {
    await writeFile(join(root, 'package.json'), JSON.stringify({ version: '6.4.1' }))
    const result = invoke()
    assert.notEqual(result.status, 0)
    assert.match(result.stderr, /Review the MapLibre security backport/)
  })
})

test('unexpected contents fail before any other target is patched', async () => {
  await fixture(async (root, invoke) => {
    const source = join(root, targets[0])
    const sourceText = await readFile(source, 'utf8')
    await writeFile(source, sourceText.replace('of Array.from(elem.attributes)', 'of elem.attributes'))
    const bundle = join(root, targets[1])
    await writeFile(bundle, `${await readFile(bundle, 'utf8')}\n// unexpected package modification\n`)
    const before = await Promise.all(targets.map(file => readFile(join(root, file), 'utf8')))
    const result = invoke()
    assert.notEqual(result.status, 0)
    assert.match(result.stderr, /Unexpected MapLibre contents/)
    assert.deepEqual(await Promise.all(targets.map(file => readFile(join(root, file), 'utf8'))), before)
  })
})
