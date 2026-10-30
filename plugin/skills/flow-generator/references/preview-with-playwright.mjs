#!/usr/bin/env node
/**
 * Screenshot flow-config screens through the render page's file input, in one browser launch.
 *
 *   npm i --prefix ~/.cache/adapty-flow-playwright playwright-core      # ONCE; no browser download
 *   (cd ~/.cache/adapty-flow-playwright && node <abs-path>/preview-with-playwright.mjs \
 *     --config /abs/flow.json --screen scr_a --screen scr_b --out /abs/dir/shot-{screen}.png)
 *
 * `shoot.sh` runs this for you when the package is installed (and installs it once when npm is
 * there). Paths must be ABSOLUTE: the command runs from the cache dir.
 *
 * It opens the render page on a short URL and hands the config to the page's file input, so the
 * config never travels through the address bar: no URL length limit, whatever the config's size,
 * locale count or image previews.
 *
 * Browser: $CHROME first (any Chromium-based browser: Chrome, Chromium, Edge, Brave), then the
 * installed Chrome, Edge, Brave, Chromium, Vivaldi or Opera at their usual places, and only then
 * Playwright's own Chromium, which needs `npx playwright install chromium` once.
 *
 * What it does for every screen:
 *   - prints `[i/n] <screen>` to stderr as it starts, and the PNG's path to stdout once written;
 *   - hides anything the page draws over the screen that is not part of it (a toast, a
 *     maintenance banner) and names it;
 *   - when the screen scrolls, also writes `<out>-scroll.png`: every scroll position, left to
 *     right, so content below the fold is seen;
 *   - retries once, with a longer wait, when the page errors, stays blank or never draws. That
 *     happens and is usually gone on the retry; it says when it retried.
 *
 *   --locale <code>     render that language: a copy where it is the default and only language;
 *                       a value it lacks (usually an image) shows the default language's value
 *   --no-previews       drop every image `previewValue` (shoot.sh uses it to shorten a URL)
 *   --save-config <p>   write the config as it would be rendered and stop; needs no browser
 *   --time-limit <s>    start no new screen after this many seconds; the rest are listed
 *
 * Exit: 0 every screen rendered; 1 one or more did not; 2 bad usage or config; 3 no browser;
 * 4 nothing drew at all and the page gave no reason (it did not load, or did not take the file).
 *
 * An agent that already has a browser tool can drive the page the same way: open
 * <app-url>/flow-preview?screen=…&device=…&orientation=…, set the config file on
 * [data-testid="preview-config-input"], then screenshot [data-screen-content].
 */

import {existsSync, mkdirSync, readFileSync, rmSync, writeFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import {homedir} from 'node:os'
import {basename, delimiter, dirname, join, resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import {parseArgs} from 'node:util'

const CONFIG_INPUT_SELECTOR = '[data-testid="preview-config-input"]'
const SCREEN_CONTENT_SELECTOR = '[data-screen-content]'
const DEFAULT_APP_URL = 'https://app.adapty.io'
const SETTLE_MS = 500
const TIMEOUT_MS = 30_000
const RETRY_TIMEOUT_MS = 60_000
const IMAGE_WAIT_MS = 10_000
// Messages the page draws INSTEAD of a screen when the request itself is wrong. A retry cannot
// change these, so they fail at once.
const FINAL_PAGE_MESSAGES = [/Unknown device "/, /No screen "/, /Flow has no screens/, /Config must be a flow/]

const USAGE =
  'Usage: node preview-with-playwright.mjs --config <flow.json> [--screen <id> ...]\n' +
  '         [--out shot.png | --out <dir>/shot-{screen}.png] [--device iphone-14] [--orientation portrait]\n' +
  '         [--locale <code>] [--no-previews] [--save-config <path>] [--time-limit <s>] [--app-url <url>]'

class UsageError extends Error {}

// ---------------------------------------------------------------------------------------------
// The config: read, normalise, and the two copies (--locale, --no-previews). No browser needed.

/**
 * The render page insists on `{flow, remoteConfigs}`, which is neither of the two shapes you
 * actually have on disk: `flows config get` returns `{config, remote_configs, …}`, and
 * `validate`/`update` take the bare flow. Accept all three so the caller never has to care.
 */
export function normalize(doc) {
  if (doc && typeof doc === 'object' && 'flow' in doc) return doc
  if (doc && typeof doc === 'object' && 'config' in doc) {
    return {flow: doc.config, remoteConfigs: doc.remote_configs ?? doc.remoteConfigs ?? null}
  }

  return {flow: doc, remoteConfigs: null}
}

const isRecord = (v) => typeof v === 'object' && v !== null && !Array.isArray(v)
const emptyText = (n) => isRecord(n) && n.type === 'text' && n.text === ''
const emptyParagraph = (n) =>
  isRecord(n) && n.type === 'paragraph' && (n.content == null || (Array.isArray(n.content) && n.content.every(emptyText)))

/** "Missing" for a catalog value, the same predicate as `localization.py`'s `is_empty`. */
export function isEmpty(kind, value) {
  if (value === undefined || value === null) return true
  if (kind === 'rich-text') {
    if (typeof value === 'string') return value === ''
    return Array.isArray(value) && value.every(emptyParagraph)
  }

  if (kind === 'rich-string') return typeof value === 'string' ? value === '' : Array.isArray(value) && value.length === 0
  if (kind === 'image') return !isRecord(value) || value.url === ''
  if (kind === 'video') return !isRecord(value) || value.videoUrl === ''
  return false
}

/**
 * A copy that renders `code`. The render page draws `localization.defaultLocale`, so the copy makes
 * `code` the default AND the only locale (which also shortens a preview URL by every other
 * language). A value `code` lacks falls back to the original default's, so an image stored only
 * under the first language does not render empty. Returns how many values fell back, per kind.
 */
export function localeCopy(flow, code) {
  const lz = flow?.localization
  if (!isRecord(lz) || !isRecord(lz.content) || !Array.isArray(lz.locales)) {
    throw new UsageError(
      'This config keeps its texts outside a localization catalog (schemaVersion below 13), so a ' +
        'language cannot be picked here. Open the flow in the builder and switch the language there.',
    )
  }

  const entry = lz.locales.find((l) => isRecord(l) && (l.code === code || l.id === code))
  if (!entry) {
    const have = lz.locales.map((l) => l?.code ?? l?.id).join(', ')
    throw new UsageError(`This flow has no locale "${code}". It has: ${have || 'none'}.`)
  }

  const from = lz.defaultLocale
  const fellBack = {}
  const content = {}
  for (const [id, item] of Object.entries(lz.content)) {
    const values = isRecord(item?.values) ? item.values : {}
    let value = values[entry.id]
    if (isEmpty(item?.kind, value) && from !== entry.id && !isEmpty(item?.kind, values[from])) {
      value = values[from]
      fellBack[item.kind] = (fellBack[item.kind] ?? 0) + 1
    }

    content[id] = {...item, values: isEmpty(item?.kind, value) ? {} : {[entry.id]: value}}
  }

  const out = {...flow, localization: {...lz, content, defaultLocale: entry.id, locales: [entry]}}
  // Some read-backs also echo the legacy top-level pair; keep it in step so nothing disagrees.
  if ('locales' in flow) out.locales = [entry]
  if ('defaultLocale' in flow) out.defaultLocale = entry.id
  return {flow: out, fellBack, code: entry.code ?? entry.id, from}
}

/** Every bound image carries a base64 `previewValue`; the render downloads the full file anyway. */
export function withoutPreviews(node) {
  if (Array.isArray(node)) return node.map(withoutPreviews)
  if (!isRecord(node)) return node
  return Object.fromEntries(Object.entries(node).filter(([k]) => k !== 'previewValue').map(([k, v]) => [k, withoutPreviews(v)]))
}

// ---------------------------------------------------------------------------------------------
// In-page helpers. Each runs inside the render page through page.evaluate, so each is
// self-contained: no closures over this module.

/** Waits for the screen's images and fonts, so a shot never catches a half-loaded image. */
export async function pageWaitForAssets([selector, ms]) {
  const content = document.querySelector(selector)
  const images = [...(content?.querySelectorAll('img') ?? [])].filter((img) => !img.complete)
  const loaded = Promise.all(images.map((img) => new Promise((done) => {
    img.addEventListener('load', done, {once: true})
    img.addEventListener('error', done, {once: true})
  })))
  await Promise.race([Promise.all([loaded, document.fonts?.ready]), new Promise((done) => setTimeout(done, ms))])
}

/** True when the screen drew no text, image, video, canvas, vector or background image at all. */
export function pageIsBlank(selector) {
  const content = document.querySelector(selector)
  if (!content) return true
  if ((content.innerText ?? '').trim()) return false
  for (const el of content.querySelectorAll('*')) {
    const box = el.getBoundingClientRect()
    if (box.width < 1 || box.height < 1) continue
    if (/^(IMG|SVG|VIDEO|CANVAS|PICTURE)$/i.test(el.tagName)) return false
    if (getComputedStyle(el).backgroundImage !== 'none') return false
  }

  return true
}

/**
 * Hides everything the page draws over the screen that is not part of it: a toast, a maintenance
 * banner, any notice. Only the branches BESIDE the screen's own subtree are touched, so nothing the
 * flow draws can be hidden. Returns a short label for each thing hidden.
 */
export function pageHideOverlays(selector) {
  const content = document.querySelector(selector)
  if (!content) return []
  const r = content.getBoundingClientRect()
  const overlaps = (b) => b.width > 0 && b.height > 0 && b.left < r.right && b.right > r.left && b.top < r.bottom && b.bottom > r.top
  const drawn = (el) => {
    const s = getComputedStyle(el)
    return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity) > 0 && overlaps(el.getBoundingClientRect())
  }

  const hidden = []
  for (let node = content; node.parentElement; node = node.parentElement) {
    for (const sibling of node.parentElement.children) {
      if (sibling === node || /^(SCRIPT|STYLE|LINK|META|TEMPLATE)$/.test(sibling.tagName)) continue
      if (![sibling, ...sibling.querySelectorAll('*')].some(drawn)) continue
      sibling.style.setProperty('opacity', '0', 'important')
      hidden.push((sibling.innerText ?? '').trim().replace(/\s+/g, ' ').slice(0, 80) || `a ${sibling.tagName.toLowerCase()} with no text`)
    }
  }

  return hidden
}

/**
 * The screen's own scroll container, when its content is taller than the phone. At least half the
 * screen tall: a review card or a text box with its own overflow is not the screen scrolling.
 */
export function pageScroller(selector) {
  const content = document.querySelector(selector)
  const floor = (content?.clientHeight ?? 0) / 2
  let best = null
  for (const el of content?.querySelectorAll('*') ?? []) {
    if (!/(auto|scroll)/.test(getComputedStyle(el).overflowY) || el.clientHeight < floor) continue
    const extra = el.scrollHeight - el.clientHeight
    if (extra > 1 && (!best || extra > best.extra)) best = {el, extra}
  }

  if (!best) return null
  best.el.setAttribute('data-shot-scroller', '')
  return {client: best.el.clientHeight, scroll: best.el.scrollHeight}
}

// ---------------------------------------------------------------------------------------------
// The browser.

/** Playwright is a run-time dependency of the caller: this cache dir, npx, or the project. */
function loadChromium() {
  const roots = [
    process.cwd(),
    join(homedir(), '.cache', 'adapty-flow-playwright'),
    ...(process.env.PATH ?? '')
      .split(delimiter)
      .filter((dir) => dir.endsWith(join('node_modules', '.bin')))
      .map((dir) => join(dir, '..')),
  ]
  for (const root of roots) {
    for (const name of ['playwright', 'playwright-core']) {
      try {
        return createRequire(join(root, 'noop.js'))(name).chromium
      } catch {
        continue
      }
    }
  }

  return null
}

/** Installed Chromium-based browsers, most likely to work first. */
export function browserCandidates(env = process.env, platform = process.platform) {
  if (platform === 'darwin') {
    const apps = [
      'Google Chrome.app/Contents/MacOS/Google Chrome',
      'Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
      'Brave Browser.app/Contents/MacOS/Brave Browser',
      'Chromium.app/Contents/MacOS/Chromium',
      'Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta',
      'Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
      'Vivaldi.app/Contents/MacOS/Vivaldi',
      'Opera.app/Contents/MacOS/Opera',
    ]
    return ['/Applications', join(homedir(), 'Applications')].flatMap((dir) => apps.map((app) => join(dir, app)))
  }

  if (platform === 'win32') {
    const roots = [env.PROGRAMFILES, env['PROGRAMFILES(X86)'], env.LOCALAPPDATA].filter(Boolean)
    const exes = [
      'Google/Chrome/Application/chrome.exe',
      'Microsoft/Edge/Application/msedge.exe',
      'BraveSoftware/Brave-Browser/Application/brave.exe',
      'Chromium/Application/chrome.exe',
      'Vivaldi/Application/vivaldi.exe',
    ]
    return roots.flatMap((dir) => exes.map((exe) => join(dir, exe)))
  }

  const names = [
    'google-chrome', 'google-chrome-stable', 'microsoft-edge', 'microsoft-edge-stable', 'brave-browser',
    'brave', 'chromium', 'chromium-browser', 'vivaldi', 'vivaldi-stable', 'opera',
  ]
  const dirs = (env.PATH ?? '').split(delimiter).filter(Boolean)
  return [...dirs.flatMap((dir) => names.map((name) => join(dir, name))), '/snap/bin/chromium']
}

/** Launches the first browser that starts. Returns {browser, name}, or {tried} with each reason. */
async function launch(chromium) {
  const tried = []
  const attempt = async (executablePath) => {
    try {
      // 30 s, not Playwright's 180: a browser that cannot run headless should cost little.
      return await chromium.launch({executablePath, headless: true, timeout: 30_000})
    } catch (error) {
      tried.push(`${executablePath ?? "Playwright's own Chromium"}: ${String(error?.message ?? error).split('\n')[0]}`)
      return null
    }
  }

  if (process.env.CHROME) {
    const browser = await attempt(process.env.CHROME)
    return browser ? {browser, name: process.env.CHROME} : {tried}
  }

  for (const path of [...new Set(browserCandidates())]) {
    if (!existsSync(path)) continue
    const browser = await attempt(path)
    if (browser) return {browser, name: path}
  }

  const browser = await attempt(undefined)
  return browser ? {browser, name: "Playwright's own Chromium"} : {tried}
}

// ---------------------------------------------------------------------------------------------
// One screen.

const brief = (error) => String(error?.message ?? error).split('\n')[0].replace(/\s*Call log:?\s*$/, '')

class RenderError extends Error {
  constructor(message, {final = false} = {}) {
    super(message)
    this.final = final
  }
}

async function renderScreen(context, {appUrl, args, payloadBuffer, configName, screen, out, timeout, retry}) {
  const query = `${screen ? `screen=${encodeURIComponent(screen)}&` : ''}device=${encodeURIComponent(args.device)}` +
    `&orientation=${encodeURIComponent(args.orientation)}`
  const url = `${appUrl}/flow-preview?${query}`
  const page = await context.newPage()
  page.setDefaultTimeout(timeout)
  try {
    // `load` is the wrong signal: it can hang long past the point where the screen is drawn.
    try {
      await page.goto(url, {timeout, waitUntil: 'domcontentloaded'})
    } catch (error) {
      throw new RenderError(`could not open ${appUrl} (${brief(error)})`)
    }

    try {
      await page.locator(CONFIG_INPUT_SELECTOR).setInputFiles({buffer: payloadBuffer, mimeType: 'application/json', name: configName})
    } catch (error) {
      throw new RenderError(`the page never showed its config input (${brief(error)})`)
    }

    const content = page.locator(SCREEN_CONTENT_SELECTOR).first()
    try {
      // Whichever comes first: the screen, or the page's own verdict (which then fails at once
      // instead of after the whole wait).
      const first = await page.waitForFunction(([selector, patterns]) => (document.querySelector(selector) && 'screen') ||
        (patterns.some((p) => new RegExp(p).test(document.body?.innerText ?? '')) && 'verdict'),
      [SCREEN_CONTENT_SELECTOR, FINAL_PAGE_MESSAGES.map((re) => re.source)], {timeout})
      if ((await first.jsonValue()) === 'verdict') throw new Error('the page gave a verdict')
      await content.waitFor({state: 'visible', timeout})
    } catch (error) {
      // The page reports config problems as plain text where the screen would be; that names the
      // actual fault, so show it instead of a timeout.
      const shown = (await page.evaluate(() => document.body.innerText ?? '').catch(() => '')).trim()
      const final = FINAL_PAGE_MESSAGES.some((re) => re.test(shown))
      throw new RenderError(shown ? `the page says: ${shown.slice(0, 300)}` : `nothing drew within ${timeout / 1000}s (${brief(error)})`, {final})
    }

    await page.waitForTimeout(SETTLE_MS)
    await page.evaluate(pageWaitForAssets, [SCREEN_CONTENT_SELECTOR, IMAGE_WAIT_MS]).catch(() => {})
    // A screen of plain colour is legitimate, so a second blank is shot and named, not failed.
    const blank = await page.evaluate(pageIsBlank, SCREEN_CONTENT_SELECTOR)
    if (blank && !retry) throw new RenderError('the screen drew no text and no image')

    const hidden = await page.evaluate(pageHideOverlays, SCREEN_CONTENT_SELECTOR)
    mkdirSync(dirname(out), {recursive: true})
    await content.screenshot({path: out, type: 'png'})

    const scroll = await page.evaluate(pageScroller, SCREEN_CONTENT_SELECTOR)
    let scrollOut = out.replace(/\.png$/i, '') + '-scroll.png'
    rmSync(scrollOut, {force: true})   // an older render's views would read as this one's
    if (!scroll) scrollOut = null
    if (scroll) {
      const scroller = page.locator('[data-shot-scroller]').first()
      const shots = []
      const tops = []
      for (let top = 0; top < scroll.scroll - scroll.client; top += scroll.client) tops.push(top)
      tops.push(scroll.scroll - scroll.client)
      for (const top of tops) {
        await scroller.evaluate((el, y) => { el.scrollTop = y }, top)
        await page.waitForTimeout(150)
        shots.push((await content.screenshot({type: 'png'})).toString('base64'))
      }

      await stitch(context, shots, scrollOut)
      Object.assign(scroll, {views: shots.length})
    }

    return {blank, hidden, scroll, scrollOut}
  } finally {
    await page.close().catch(() => {})
  }
}

/** Lays the scroll positions side by side, left to right, with the same gutter as montage.py. */
async function stitch(context, shots, out) {
  const page = await context.newPage()
  try {
    const imgs = shots.map((b64) => `<img src="data:image/png;base64,${b64}" style="display:block">`).join('')
    await page.setContent(`<body style="margin:0;background:#fff"><div id="s" style="display:inline-flex;gap:8px;align-items:flex-start">${imgs}</div></body>`)
    await page.evaluate(() => Promise.all([...document.images].map((img) => img.decode())))
    const box = await page.locator('#s').boundingBox()
    await page.setViewportSize({height: Math.ceil(box.height), width: Math.ceil(box.width)})
    await page.locator('#s').screenshot({path: out, type: 'png'})
  } finally {
    await page.close().catch(() => {})
  }
}

// ---------------------------------------------------------------------------------------------

async function main() {
  const fail = (message, code = 2) => {
    console.error(`${message}\n${USAGE}`)
    process.exit(code)
  }

  let args
  try {
    ;({values: args} = parseArgs({
      options: {
        'app-url': {type: 'string'},
        config: {type: 'string'},
        device: {default: 'iphone-14', type: 'string'},
        locale: {type: 'string'},
        'no-previews': {type: 'boolean'},
        orientation: {default: 'portrait', type: 'string'},
        out: {type: 'string'},
        'save-config': {type: 'string'},
        screen: {multiple: true, type: 'string'},
        'time-limit': {type: 'string'},
      },
    }))
  } catch (error) {
    fail(error.message)
  }

  if (!args.config) fail('No config: pass --config <path to the flow JSON>.')

  let doc
  let payload
  try {
    doc = JSON.parse(readFileSync(resolve(args.config), 'utf8'))
    payload = normalize(doc)
  } catch (error) {
    fail(`Could not read ${args.config}: ${error.message}`)
  }

  if (!Array.isArray(payload.flow?.screens)) fail(`${args.config} has no screens array; it is not a flow config.`)

  if (args.locale) {
    try {
      const copy = localeCopy(payload.flow, args.locale)
      payload = {...payload, flow: copy.flow}
      const filled = Object.entries(copy.fellBack).map(([kind, n]) => `${n} ${kind}${n === 1 ? '' : 's'}`)
      console.error(`rendering ${copy.code}` + (filled.length
        ? `; it has no value of its own for ${filled.join(', ')}, which show the ${copy.from} value`
        : ''))
    } catch (error) {
      if (error instanceof UsageError) fail(error.message)
      throw error
    }
  }

  if (args['no-previews']) payload = withoutPreviews(payload)

  if (args['save-config']) {
    // In the shape it came in, so `flows config preview` and `validate` take the copy too.
    const shaped = doc && typeof doc === 'object' && 'flow' in doc ? payload
      : doc && typeof doc === 'object' && 'config' in doc ? {...doc, config: payload.flow}
        : payload.flow
    writeFileSync(resolve(args['save-config']), JSON.stringify(shaped))
    console.log(resolve(args['save-config']))
    return
  }

  const screens = args.screen?.length ? args.screen : [null]
  const firstScreen = payload.flow.screens[0]?.id
  if (!firstScreen && screens[0] === null) fail(`No screen to render: ${args.config} has no screens.`)
  const outFor = (screen) => {
    const id = screen ?? firstScreen
    const template = args.out ?? (screens.length > 1 ? 'preview-{screen}.png' : 'preview.png')
    if (screens.length > 1 && !template.includes('{screen}')) {
      fail(`Several screens need {screen} in --out, e.g. --out /abs/dir/shot-{screen}.png (got ${template}).`)
    }

    return resolve(template.replaceAll('{screen}', id))
  }

  const outs = screens.map(outFor)
  const limitS = Number(args['time-limit'] ?? 0)
  const appUrl = (args['app-url'] ?? process.env.ADAPTY_APP_URL ?? DEFAULT_APP_URL).replace(/\/+$/, '')

  const chromium = loadChromium()
  if (!chromium) {
    console.error(
      'Playwright is not installed. Install it once (no browser download; it uses your installed browser):\n' +
        '  npm i --prefix ~/.cache/adapty-flow-playwright playwright-core\n' +
        'then run this from that directory.',
    )
    process.exit(3)
  }

  const launched = await launch(chromium)
  if (!launched.browser) {
    console.error(
      'Could not start a browser. Tried:\n' + launched.tried.map((t) => `  - ${t}`).join('\n') + '\n' +
        'Set CHROME=/path/to/a Chromium-based browser (Chrome, Chromium, Edge, Brave), or install\n' +
        "Playwright's own Chromium once: npx playwright install chromium",
    )
    process.exit(3)
  }

  console.error(`browser: ${launched.name}`)
  const started = Date.now()
  const missed = []
  let rendered = 0
  let verdicts = 0
  try {
    // Room for the largest frame (ipad-pro-13, landscape) with the page's margin, so the whole
    // screen is on the viewport and nothing the page pins to the window edge lands on it.
    const context = await launched.browser.newContext({viewport: {height: 1600, width: 1600}})
    const payloadBuffer = Buffer.from(JSON.stringify(payload))
    for (const [i, screen] of screens.entries()) {
      const label = screen ?? firstScreen
      if (limitS > 0 && (Date.now() - started) / 1000 > limitS) {
        missed.push(...screens.slice(i).map((s) => s ?? firstScreen))
        console.error(`time limit of ${limitS}s reached; not rendered: ${missed.join(' ')}`)
        break
      }

      console.error(`[${i + 1}/${screens.length}] ${label}`)
      const t0 = Date.now()
      const job = {appUrl, args, configName: basename(args.config), out: outs[i], payloadBuffer, screen}
      let result
      try {
        result = await renderScreen(context, {...job, timeout: TIMEOUT_MS})
      } catch (error) {
        if (!(error instanceof RenderError)) throw error
        if (error.final) {
          console.error(`   NOT RENDERED ${label}: ${error.message}`)
          missed.push(label)
          verdicts += 1
          continue
        }

        console.error(`   retrying ${label} once, with a longer wait: ${error.message}`)
        try {
          result = await renderScreen(context, {...job, retry: true, timeout: RETRY_TIMEOUT_MS})
          console.error(`   ${label} rendered on the retry`)
        } catch (again) {
          if (!(again instanceof RenderError)) throw again
          console.error(`   NOT RENDERED ${label}: ${again.message}`)
          missed.push(label)
          continue
        }
      }

      rendered += 1
      const secs = ((Date.now() - t0) / 1000).toFixed(1)
      console.error(`   ${label} in ${secs}s`)
      if (result.blank) console.error(`   ${label} drew no text and no image, twice: LOOK AT IT before trusting it`)
      for (const what of result.hidden) console.error(`   hid something the page drew over the screen: "${what}"`)
      if (result.scroll) {
        console.error(`   ${label} scrolls: ${result.scroll.scroll}pt of content in a ${result.scroll.client}pt screen, ` +
          `${result.scroll.views} views left to right in ${basename(result.scrollOut)}`)
      }

      console.log(outs[i])
      if (result.scrollOut) console.log(result.scrollOut)
    }
  } finally {
    await launched.browser.close().catch(() => {})
  }

  if (missed.length) {
    console.error(`${rendered} of ${screens.length} rendered; not rendered: ${missed.join(' ')}`)
    // 4: the page never drew anything and never said why, so another way into it may work.
    process.exitCode = rendered === 0 && verdicts === 0 ? 4 : 1
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main()
}
