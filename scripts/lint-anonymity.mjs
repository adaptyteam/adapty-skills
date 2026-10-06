#!/usr/bin/env node
/**
 * Anonymity lint: this repository is public and `plugin/` ships to every user, so no tracked file
 * may point into Adapty's internal systems. Fails on task-tracker keys, helpdesk and chat links,
 * merge-request numbers, internal hosts, the internal sandbox app, and names, paths and line
 * numbers from closed-source repos.
 *
 * Ported from the docs repo's context-mill anonymity test and extended with what this repo
 * needed. It is the mechanical half of the rule in CLAUDE.md ("This repo is public: keep it
 * anonymous"). It cannot see people's names, customer names, or a retold customer case, so the
 * rule, not this lint, covers those.
 *
 * Scans every tracked text file, CLAUDE.md and tests included: a file that does not ship is
 * still public on GitHub.
 *
 * Usage:  node scripts/lint-anonymity.mjs   (runs its own self-test first)
 * Exit codes: 0 = clean, 1 = findings, 2 = infra error (git unavailable, file unreadable).
 */

import {execFileSync} from 'node:child_process'
import {readFileSync} from 'node:fs'
import {dirname, join} from 'node:path'
import {fileURLToPath} from 'node:url'

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')

// Hyphenated identifiers that look like tracker keys but are standards.
const NOT_TRACKER_KEYS = new Set([
  'ISO-8601', 'ISO-639', 'ISO-4217', 'ISO-3166', 'UTF-16', 'UTF-32', 'SHA-256', 'SHA-512', 'RFC-4122',
])

// Files whose bytes are not prose: vendored data, images, fonts, and this lint's own patterns.
const SKIP = [/\.(png|jpe?g|gif|webp|gz|zip|pdf|ttf|otf|woff2?)$/i, /^scripts\/lint-anonymity\.mjs$/]

const PATTERNS = [
  {kind: 'tracker key', re: /\b[A-Z][A-Z0-9]{1,9}-\d{2,}\b/g, skip: (m) => NOT_TRACKER_KEYS.has(m)},
  {kind: 'helpdesk link', re: /usepylon\.com|intercom\.(com|io)|zendesk\.com|atlassian\.net/gi},
  {kind: 'helpdesk ticket', re: /\b(pylon|intercom|zendesk)\s+#?\d+/gi},
  {kind: 'chat link', re: /slack\.com\/(archives|app_redirect)/gi},
  {kind: 'chat channel', re: /#adp-[a-z0-9-]+/g},
  {kind: 'merge request', re: /(?<!&)![0-9]{3,}\b/g},
  {kind: 'internal host', re: /gitlab(-ssh)?\.adapty\.io|\/api\/v4\/|adpinfra\.dev/gi},
  {kind: 'internal sandbox app', re: /app_finance|7c154682-251d-4734-8c1d-afd3c0449a96/g},
  {
    kind: 'closed-source repo',
    re: /adapty-dashboard-(api|interface)|dashboard-(backend|interface)|noty-wave|unified-builder|adapty-agents|asa-analytics|figma-flow|adapty-swift-app|UniversalDevtool|revenue-cat-migrator|flow-publish-doctor/gi,
  },
  {kind: 'closed-source path', re: /\b(generate-handlers|generate-meta|collect-variables|user-input-analytics|buildFlowMeta|PlacementFlowList|Routes)\.tsx?\b/g},
]

export function findLeaks(text) {
  const leaks = []
  for (const {kind, re, skip} of PATTERNS) {
    for (const [match] of text.matchAll(re)) {
      if (!skip?.(match)) leaks.push({kind, match})
    }
  }
  return leaks
}

function selfTest() {
  const cases = [
    ['fixed geometry breaks (ABC-7117)', ['tracker key']],
    ['see https://example.atlassian.net/browse/ABC-12', ['tracker key', 'helpdesk link']],
    ['mined from #adp-builder-cs-ps', ['chat channel']],
    ['Source: some-repo!13221 @ d0b878cb', ['merge request']],
    ['points at app.dev.adpinfra.dev', ['internal host']],
    ['measured in `app_finance`', ['internal sandbox app']],
    ['read from `unified-builder-transformer@dcf2df4`', ['closed-source repo']],
    ['(`generate-handlers.ts:489`)', ['closed-source path']],
    ['ISO-8601 dates, SHA-256, RFC-4122 UUIDs, SDK-3, `@adapty/capacitor`, x != !y, &#123;', []],
  ]
  let failed = 0
  for (const [text, want] of cases) {
    const got = findLeaks(text).map((l) => l.kind)
    const ok = JSON.stringify([...new Set(got)].sort()) === JSON.stringify([...want].sort())
    if (!ok) {
      failed++
      console.log(`self-test FAIL: ${JSON.stringify(text)} -> ${JSON.stringify(got)}, want ${JSON.stringify(want)}`)
    }
  }
  console.log(`${cases.length} self-test case(s) -> ${failed} failure(s)`)
  return failed
}

function main() {
  if (selfTest()) {
    process.exitCode = 1
    return
  }
  let files
  try {
    files = execFileSync('git', ['ls-files'], {cwd: REPO_ROOT, encoding: 'utf8'}).split('\n').filter(Boolean)
  } catch (e) {
    console.error(`cannot list tracked files: ${e.message}`)
    process.exitCode = 2
    return
  }
  let findings = 0
  let scanned = 0
  for (const file of files) {
    if (SKIP.some((re) => re.test(file))) continue
    let text
    try {
      text = readFileSync(join(REPO_ROOT, file), 'utf8')
    } catch (e) {
      if (e.code === 'ENOENT') continue // deleted in the working tree, not yet committed
      console.error(`${file}: cannot read (${e.code})`)
      process.exitCode = 2
      continue
    }
    scanned++
    text.split('\n').forEach((line, i) => {
      for (const {kind, match} of findLeaks(line)) {
        console.log(`${file}:${i + 1}: ${kind}: ${match}`)
        findings++
      }
    })
  }
  console.log(`${scanned} tracked file(s) -> ${findings} anonymity finding(s)`)
  if (findings && process.exitCode !== 2) process.exitCode = 1
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main()
