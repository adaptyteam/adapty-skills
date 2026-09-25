#!/usr/bin/env node
/**
 * Frontmatter lint: every skills/<name>/SKILL.md opens with frontmatter that a
 * STRICT YAML parser accepts and that meets the Agent Skills spec.
 *
 * Why strict: harnesses differ in how forgiving their YAML parser is. An
 * unquoted description containing ": " is invalid YAML ("mapping values are
 * not allowed in this context"); a lenient loader shrugs, a strict one drops
 * the skill. Neither of the other lints parses frontmatter, so that defect
 * reached main once and was found by skill-validator, not by CI.
 *
 * No dependencies, like the other lints, so this is NOT a general YAML parser.
 * It accepts a deliberately small subset -- top-level `key: value` pairs whose
 * value is a plain scalar, a single- or double-quoted scalar, or a block
 * scalar (`>`, `>-`, `|`, `|-`) -- and REFUSES anything else by name. A shape
 * it cannot fully check is an error, never a pass: if a skill needs one (a
 * `metadata` map, say), extend this file rather than loosening a check.
 *
 * Checks, per the spec (https://agentskills.io/specification):
 *   - frontmatter present, opened and closed by `---`
 *   - every value in a supported shape; plain scalars obey YAML's rules
 *   - `name` and `description` present; no key repeated; no unknown key
 *   - `name` matches its directory, lowercase letters/digits/hyphens, <= 64 chars
 *   - `description` non-empty, <= 1024 chars once parsed
 *
 * Usage:  node scripts/lint-frontmatter.mjs [path/to/SKILL.md ...]
 *         (no arguments = every skills/<name>/SKILL.md)
 * Exit codes: 0 = clean, 1 = findings, 2 = infra error (unreadable file).
 */

import {readdir, readFile} from 'node:fs/promises'
import {basename, dirname, join, relative} from 'node:path'
import {fileURLToPath} from 'node:url'

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const SKILLS_DIR = join(REPO_ROOT, 'skills')

// Top-level keys the spec defines. `metadata` is a map, which this subset
// does not parse -- it is listed so the refusal names the real reason.
const SCALAR_KEYS = new Set(['name', 'description', 'license', 'compatibility', 'allowed-tools'])
const MAP_KEYS = new Set(['metadata'])
const NAME_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/
const MAX_NAME = 64
const MAX_DESCRIPTION = 1024

/** Characters that may not start a plain scalar in block context. */
const PLAIN_BAD_START = /^[\[\]{},#&*!|>'"%@`]|^[-?:](\s|$)/

/**
 * Parse the frontmatter subset. Returns {values, errors}; errors carry the
 * 1-based line number within the SKILL.md.
 */
export function parseFrontmatter(text) {
  const errors = []
  const values = {}
  const lines = text.split('\n')
  if (lines[0] !== '---') return {values, errors: [{line: 1, msg: 'no frontmatter: the file must start with a `---` line'}]}
  const end = lines.indexOf('---', 1)
  if (end === -1) return {values, errors: [{line: 1, msg: 'frontmatter is never closed: no second `---` line'}]}

  let i = 1
  while (i < end) {
    const n = i + 1
    const line = lines[i]
    if (line.trim() === '' || /^\s*#/.test(line)) { i++; continue }
    if (/^\s/.test(line)) { errors.push({line: n, msg: 'unexpected indented line outside a block scalar'}); i++; continue }
    const m = /^([A-Za-z0-9_-]+):(?: (.*))?$/.exec(line)
    if (!m) { errors.push({line: n, msg: `not a \`key: value\` line: ${JSON.stringify(line.slice(0, 60))}`}); i++; continue }
    const [, key, rawValue = ''] = m
    if (key in values) errors.push({line: n, msg: `key \`${key}\` appears twice`})
    if (MAP_KEYS.has(key)) { errors.push({line: n, msg: `\`${key}\` is a map; this lint only parses scalar values -- extend scripts/lint-frontmatter.mjs before using it`}); i++; continue }
    if (!SCALAR_KEYS.has(key)) errors.push({line: n, msg: `unknown key \`${key}\` (spec keys: ${[...SCALAR_KEYS, ...MAP_KEYS].join(', ')})`})

    const raw = rawValue.replace(/\s+$/, '')
    if (/^[>|][+-]?$/.test(raw)) {
      // Block scalar: every following indented (or blank) line belongs to it.
      const folded = raw[0] === '>'
      const chomp = raw[1] ?? ''
      const body = []
      i++
      while (i < end && (lines[i].trim() === '' || /^\s/.test(lines[i]))) body.push(lines[i++])
      const indents = body.filter((l) => l.trim()).map((l) => l.match(/^ */)[0].length)
      if (!indents.length) { errors.push({line: n, msg: `\`${key}\` block scalar has no content`}); values[key] = ''; continue }
      if (body.some((l) => /^\t/.test(l))) errors.push({line: n, msg: `\`${key}\` block scalar is indented with a tab`})
      const ind = Math.min(...indents)
      const stripped = body.map((l) => l.slice(ind))
      let v = folded ? stripped.join('\n').replace(/([^\n])\n(?=[^\n])/g, '$1 ') : stripped.join('\n')
      v = chomp === '+' ? v : chomp === '-' ? v.replace(/\n+$/, '') : v.replace(/\n+$/, '') + '\n'
      values[key] = v
      continue
    }

    if (raw.startsWith("'")) {
      if (!/^'(?:[^']|'')*'$/.test(raw)) errors.push({line: n, msg: `\`${key}\`: unterminated or badly escaped single-quoted value (a literal ' is written '')`})
      values[key] = raw.slice(1, -1).replace(/''/g, "'")
    } else if (raw.startsWith('"')) {
      if (!/^"(?:[^"\\]|\\.)*"$/.test(raw)) errors.push({line: n, msg: `\`${key}\`: unterminated double-quoted value (a literal " is written \\")`})
      try { values[key] = JSON.parse(raw) } catch { values[key] = raw.slice(1, -1) }
    } else {
      const col = raw.indexOf(': ')
      if (col !== -1) errors.push({line: n, msg: `\`${key}\`: unquoted value contains ": " at column ${key.length + 3 + col} ("${raw.slice(Math.max(0, col - 20), col + 20)}") -- a strict YAML parser reads it as a nested mapping and rejects the frontmatter. Quote the value: wrap it in single quotes and double any ' inside`})
      if (/\s#/.test(raw)) errors.push({line: n, msg: `\`${key}\`: unquoted value contains " #", which YAML reads as the start of a comment. Quote the value`})
      if (PLAIN_BAD_START.test(raw)) errors.push({line: n, msg: `\`${key}\`: unquoted value starts with a YAML indicator character. Quote the value`})
      if (raw.endsWith(':')) errors.push({line: n, msg: `\`${key}\`: unquoted value ends with ":". Quote the value`})
      values[key] = raw
    }
    i++
  }
  return {values, errors}
}

/** Spec checks on top of the parse. `dir` is the skill's directory name. */
export function checkSkill(text, dir) {
  const {values, errors} = parseFrontmatter(text)
  if (errors.some((e) => /no frontmatter|never closed/.test(e.msg))) return errors
  const at1 = (msg) => errors.push({line: 1, msg})
  if (!('name' in values)) at1('missing required key `name`')
  else {
    const name = values.name
    if (!NAME_RE.test(name)) at1(`\`name\` ${JSON.stringify(name)} must be lowercase letters, digits and single hyphens`)
    if (name.length > MAX_NAME) at1(`\`name\` is ${name.length} characters (max ${MAX_NAME})`)
    if (dir && name !== dir) at1(`\`name\` ${JSON.stringify(name)} does not match its directory \`${dir}\``)
  }
  if (!('description' in values)) at1('missing required key `description`')
  else {
    const d = values.description.trim()
    if (!d) at1('`description` is empty')
    if (d.length > MAX_DESCRIPTION) at1(`\`description\` is ${d.length} characters (max ${MAX_DESCRIPTION})`)
  }
  return errors
}

async function main() {
  let files = process.argv.slice(2)
  if (!files.length) {
    const dirs = (await readdir(SKILLS_DIR, {withFileTypes: true})).filter((d) => d.isDirectory())
    files = dirs.map((d) => join(SKILLS_DIR, d.name, 'SKILL.md'))
  }
  let findings = 0
  for (const file of files.sort()) {
    let text
    try { text = await readFile(file, 'utf8') } catch (e) {
      console.error(`${relative(REPO_ROOT, file)}: cannot read (${e.code})`)
      process.exitCode = 2
      continue
    }
    const errors = checkSkill(text, basename(dirname(file)))
    for (const e of errors) console.log(`${relative(REPO_ROOT, file)}:${e.line}: ${e.msg}`)
    findings += errors.length
  }
  console.log(`${files.length} SKILL.md file(s) -> ${findings} frontmatter finding(s)`)
  if (findings && process.exitCode !== 2) process.exitCode = 1
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await main()
