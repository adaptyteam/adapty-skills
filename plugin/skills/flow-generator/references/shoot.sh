#!/bin/bash
# Preview + screenshot + montage for N screens in ONE tool call, then you Read one image.
#
#   shoot.sh draft.json                                  # the default screen
#   shoot.sh draft.json scr_a scr_b scr_c                # three screens, one strip
#   OUT=/tmp/x shoot.sh draft.json scr_a                 # choose the output dir
#   DEVICE=iphone-se-3 shoot.sh draft.json scr_a         # a short phone (375x667)
#   DEVICE=google-pixel-9 shoot.sh draft.json scr_a      # a tall phone (412x924)
#   LOCALE=de shoot.sh draft.json scr_a                  # another language (the page draws one)
#   CHROME=/path/to/browser shoot.sh draft.json scr_a    # any Chromium-based browser
#   TIME_LIMIT=900 shoot.sh draft.json scr_a ...         # seconds before it stops (default 300)
#
# Renders go next to the config, unless the config sits inside a git work tree -- an app repo,
# usually -- in which case they go to $TMPDIR/adapty-flow-shots, so no PNG lands in the user's
# working tree. OUT= always wins.
#
# Prints the path of the strip to open. That is the only thing you need from it -- read the path
# it prints rather than guessing the name: every output carries an 8-char signature of the
# CONFIG'S CONTENT (shot-<sig>-<screen>.png), so re-rendering after an edit writes a new file
# instead of overwriting the old one, and a render of superseded bytes is identifiable on sight.
#
# Two routes, the first that works:
#   1. preview-with-playwright.mjs, through the render page's file input, all screens in one
#      browser launch: a few seconds a screen, no URL length limit, anything the page draws over
#      the screen hidden, and a screen that scrolls shown at every scroll position. It needs
#      playwright-core in ~/.cache/adapty-flow-playwright, installed here once when npm is
#      there; it drives the installed browser and downloads none. PLAYWRIGHT=0 skips it.
#   2. The browser's own --screenshot of the `flows config preview` URL: ~18 s of cold start a
#      screen, and it cannot hide what the page draws over the screen.
#
# Each screen prints a line as it starts and as it lands. Every finished PNG is kept: a run that
# hits TIME_LIMIT, or is stopped, names what it rendered and what it did not.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="${1:?usage: shoot.sh <config.json> [screen-id ...]}"; shift || true
SCREENS="$*"
if [ -z "${OUT:-}" ]; then
  if git -C "$(dirname "$CFG")" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    OUT="${TMPDIR:-/tmp}"; OUT="${OUT%/}/adapty-flow-shots"
  else
    OUT="$(dirname "$CFG")"
  fi
fi
BUDGET="${BUDGET:-8000}"
TIME_LIMIT="${TIME_LIMIT:-300}"
# 520 wide, not the phone's own 430: the render page centres its phone frame with a margin, so at
# 430 the frame starts ~55px in and its right edge is cut off, which reads as a layout overflow.
# A named device can be taller than the default frame (google-pixel-9 is 924pt), and a window
# shorter than the frame crops it, so a device run gets a taller window.
DEVICE="${DEVICE:-}"
if [ -n "$DEVICE" ]; then WINDOW="${WINDOW:-520,1100}"; else WINDOW="${WINDOW:-520,900}"; fi
DEVFLAG="${DEVICE:+--device $DEVICE}"; DEVTAG="${DEVICE:+-$DEVICE}"
LOCALE="${LOCALE:-}"; LOCTAG="${LOCALE:+-$LOCALE}"
[ -f "$CFG" ] || { echo "shoot: no such file: $CFG" >&2; exit 2; }
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
ABS_CFG="$(cd "$(dirname "$CFG")" && pwd)/$(basename "$CFG")"

# Every output is named after a signature of the CONFIG'S CONTENT, not just the screen id: two
# configs of the same screen cannot overwrite each other, and a render of superseded bytes -- an
# orphaned browser from a killed run can still write one -- carries the old signature, so it can
# never be mistaken for the current one. `cksum` is the fallback so this never fails the run.
if command -v shasum >/dev/null 2>&1; then
  CFGSIG=$(shasum -a 256 "$CFG" | cut -c1-8)
elif command -v sha256sum >/dev/null 2>&1; then
  CFGSIG=$(sha256sum "$CFG" | cut -c1-8)
else
  CFGSIG=$(cksum "$CFG" | awk '{print $1}')
fi

# Python 3 by RUNNING each candidate, never by name: on Windows `python3` is usually the Microsoft
# Store stub, which is on PATH, prints an install hint and fails. PYTHON= wins.
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3 python "py -3"; do
    if $c -X utf8 -c 'import sys; sys.exit(sys.version_info[0] != 3)' >/dev/null 2>&1; then PY="$c -X utf8"; break; fi
  done
fi
[ -n "$PY" ] || { echo "shoot: no Python 3 found (tried python3, python, py -3) — set PYTHON=/path" >&2; exit 2; }

# Windows (Git Bash, MSYS, Cygwin) differs in three places below: where the browser lives, the
# path it is handed, and how long a command line may be.
WIN=0
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) WIN=1 ;; esac
LINUX=0
case "$(uname -s)" in Linux*) LINUX=1 ;; esac

png_for() {  # $1 = screen id or __default__
  if [ "$1" = "__default__" ]; then echo "$OUT/shot-$CFGSIG$LOCTAG$DEVTAG.png"
  else echo "$OUT/shot-$CFGSIG-$1$LOCTAG$DEVTAG.png"; fi
}

[ -n "$SCREENS" ] || SCREENS="__default__"
TOTAL=$(echo $SCREENS | wc -w | tr -d ' ')
shots=""; n=0; done_ids=""; CHILD=""

# The strip, or the one image, and the line that says which. Called at the end and when stopped.
finish() {  # $1 = exit code
  if [ "$n" -eq 0 ]; then echo "shoot: nothing rendered" >&2; exit "${1:-1}"; fi
  if [ "$n" -eq 1 ]; then
    echo; echo "LOOK AT:$shots"
  else
    strip="$OUT/strip-$CFGSIG$LOCTAG$DEVTAG.png"
    $PY "$HERE/montage.py" "$strip" $shots >/dev/null
    echo; echo "LOOK AT: $strip  ($n screens, left to right in the order given)"
  fi
  exit "${1:-0}"
}

not_done() {
  local left=""
  for s in $SCREENS; do case " $done_ids " in *" $s "*) ;; *) left="$left $s" ;; esac; done
  echo "${left# }"
}

# A tool timeout or a Ctrl-C used to lose the whole batch: the finished PNGs stayed on disk, but
# nothing said where. Now the run says what landed and what did not, and still makes the strip.
on_signal() {
  trap - TERM INT HUP
  if [ -n "$CHILD" ]; then
    command -v pkill >/dev/null 2>&1 && pkill -TERM -P "$CHILD" 2>/dev/null
    kill -TERM "$CHILD" 2>/dev/null
  fi
  [ -n "${PWLIST:-}" ] && [ -s "$PWLIST" ] && collect_pw
  echo "shoot: stopped after ${SECONDS}s. Not rendered: $(not_done)" >&2
  echo "       Every finished render is kept. Run the rest on their own, in the background." >&2
  finish 143
}
trap on_signal TERM INT HUP

# --- Route 1: the file input, through preview-with-playwright.mjs -----------------------------

PW_DIR="${PW_DIR:-$HOME/.cache/adapty-flow-playwright}"
have_pw() { [ -d "$PW_DIR/node_modules/playwright-core" ] || [ -d "$PW_DIR/node_modules/playwright" ]; }

collect_pw() {  # read the paths the script printed; a scroll view replaces its screen's shot
  local line prev=""
  shots=""; n=0; done_ids=""
  while IFS= read -r line; do
    [ -s "$line" ] || continue
    case "$line" in
      *-scroll.png) shots="${shots% $prev} $line"; prev="$line" ;;
      *) shots="$shots $line"; prev="$line"; n=$((n+1)) ;;
    esac
  done < "$PWLIST"
  for s in $SCREENS; do
    grep -qxF "$(png_for "$s")" "$PWLIST" && done_ids="$done_ids $s"
  done
}

if [ "${PLAYWRIGHT:-1}" != 0 ] && command -v node >/dev/null 2>&1; then
  if ! have_pw && command -v npm >/dev/null 2>&1; then
    echo "   (installing playwright-core once into $PW_DIR; it drives your installed browser and downloads none)" >&2
    npm i --prefix "$PW_DIR" playwright-core --silent --no-audit --no-fund >/dev/null 2>&1 \
      || echo "   (could not install playwright-core; using the browser's own screenshot instead)" >&2
  fi
  if have_pw; then
    PWLIST="$OUT/.shoot-$CFGSIG-$$.list"; : > "$PWLIST"
    args=(--config "$ABS_CFG" --time-limit "$TIME_LIMIT")
    [ -n "$DEVICE" ] && args+=(--device "$DEVICE")
    [ -n "$LOCALE" ] && args+=(--locale "$LOCALE")
    if [ "$SCREENS" = "__default__" ]; then
      args+=(--out "$(png_for __default__)")
    else
      for s in $SCREENS; do args+=(--screen "$s"); done
      args+=(--out "$OUT/shot-$CFGSIG-{screen}$LOCTAG$DEVTAG.png")
    fi
    # In the background and waited on, so a signal reaches the trap above at once.
    ( cd "$PW_DIR" && exec node "$HERE/preview-with-playwright.mjs" "${args[@]}" ) > "$PWLIST" &
    CHILD=$!
    wait "$CHILD"; rc=$?
    CHILD=""
    collect_pw
    rm -f "$PWLIST"; PWLIST=""
    [ "$rc" = 2 ] && exit 2                       # a bad LOCALE or config; the script said why
    if [ "$n" -gt 0 ]; then
      for s in $shots; do echo "   rendered -> $s"; done
      [ "$rc" = 0 ] && finish 0
      echo "   not rendered: $(not_done) (the reason is above)" >&2
      finish 1
    fi
    # 3 is no browser that starts, 4 a page that never drew anything (it did not load, or did not
    # take the file): the URL route below is a different way into the same page, so try it. Any
    # other failure is the page's own verdict on the request, which that route would only repeat.
    case "$rc" in 3|4) ;; *) exit 1 ;; esac
    echo "   the file-input route rendered nothing; trying the browser's own screenshot of the preview URL" >&2
  fi
fi

# --- Route 2: the browser's own --screenshot of the preview URL --------------------------------

win_dir() { [ "$WIN" = 1 ] && [ -n "$1" ] && cygpath -u "$1" 2>/dev/null; }
PF="$(win_dir 'C:\Program Files')"; PF86="$(win_dir 'C:\Program Files (x86)')"
LAD="$(win_dir "${LOCALAPPDATA:-}")"

CHROME="${CHROME:-}"
if [ -z "$CHROME" ]; then
  # Any Chromium-based browser takes the same flags. Chrome first, then the others people have
  # instead of it; a Windows path is skipped where there is no Windows.
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
           "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" \
           "/Applications/Chromium.app/Contents/MacOS/Chromium" \
           "/Applications/Vivaldi.app/Contents/MacOS/Vivaldi" \
           "/Applications/Opera.app/Contents/MacOS/Opera" \
           "$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           "$HOME/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" \
           google-chrome google-chrome-stable chromium chromium-browser microsoft-edge \
           microsoft-edge-stable brave-browser brave vivaldi vivaldi-stable opera /snap/bin/chromium \
           "$PF/Google/Chrome/Application/chrome.exe" \
           "$PF86/Google/Chrome/Application/chrome.exe" \
           "$LAD/Google/Chrome/Application/chrome.exe" \
           "$PF86/Microsoft/Edge/Application/msedge.exe" \
           "$PF/Microsoft/Edge/Application/msedge.exe" \
           "$PF/BraveSoftware/Brave-Browser/Application/brave.exe" \
           "$LAD/BraveSoftware/Brave-Browser/Application/brave.exe" \
           "$LAD/Chromium/Application/chrome.exe" \
           "$LAD/Vivaldi/Application/vivaldi.exe"; do
    case "$c" in /Google/*|/Microsoft/*|/BraveSoftware/*|/Chromium/*|/Vivaldi/*) continue ;; esac
    if [ -x "$c" ] || command -v "$c" >/dev/null 2>&1; then CHROME="$c"; break; fi
  done
fi
if [ -z "$CHROME" ]; then
  echo "shoot: no Chromium-based browser found (looked for Chrome, Edge, Brave, Chromium, Vivaldi, Opera)." >&2
  echo "       Set CHROME to any Chromium-based browser, e.g." >&2
  echo "       CHROME='/Applications/Brave Browser.app/Contents/MacOS/Brave Browser' shoot.sh ..." >&2
  exit 2
fi

# On Linux a container usually runs as root, where Chrome refuses to start without --no-sandbox,
# and gives /dev/shm 64MB, where its renderer crashes. Both fail silently through --screenshot:
# no file, nothing said. Playwright passes the same two flags by default.
LINUX_FLAGS=""
[ "$LINUX" = 1 ] && LINUX_FLAGS="--no-sandbox --disable-dev-shm-usage"

# The CLI is the one SKILL.md phase 1 resolved: pass it as ADAPTY, or have `adapty` on PATH. This
# script never launches a package itself, so what runs is always the CLI the run already chose.
ADAPTY_BIN=${ADAPTY:-}
if [ -z "$ADAPTY_BIN" ] && command -v adapty >/dev/null 2>&1; then ADAPTY_BIN="adapty"; fi
if [ -z "$ADAPTY_BIN" ]; then
  echo "shoot: no Adapty CLI. Install it (npm install -g adapty) or pass the command: ADAPTY='npx --yes adapty@latest' shoot.sh ..." >&2
  exit 2
fi

# A copy made by preview-with-playwright.mjs, which owns the config copies (it needs no browser
# for this). LOCALE renders that language; the long-URL fallback below drops previews and every
# language but the one drawn.
copy_config() {  # $1 = source, $2 = dest, rest = options
  local src="$1" dst="$2"; shift 2
  command -v node >/dev/null 2>&1 || { echo "shoot: making a config copy needs node, which runs the Adapty CLI" >&2; return 1; }
  node "$HERE/preview-with-playwright.mjs" --config "$src" "$@" --save-config "$dst" >/dev/null
}
RCFG="$ABS_CFG"
if [ -n "$LOCALE" ]; then
  RCFG="$OUT/locale-$CFGSIG$LOCTAG.json"
  copy_config "$ABS_CFG" "$RCFG" --locale "$LOCALE" || exit 2
fi

# One launch, watchdogged -- and it returns the moment the PNG is complete rather than waiting for
# the browser to exit. A browser hangs often enough that an unguarded call costs a whole turn; and
# a COLD first launch can spend ~130 s inside Google's own updater before painting anything, so
# the watchdog stays generous. Polling for the file is what makes that free: you only wait the
# full time when nothing lands at all. Sets SHOT_END to done, exited or timeout.
CHROME_LOG="$(mktemp "${TMPDIR:-/tmp}/adapty-shoot-log.XXXXXX")"
trap 'rm -f "$CHROME_LOG"' EXIT
shoot_one() {  # $1 = url, $2 = out png, $3 = budget ms, $4 = watchdog s
  # The browser writes to a per-run temp name and the result is MOVED into place only once it is
  # complete, so an orphan from a killed run can never write the real name, and the real name never
  # exists half-written. The temp MUST end in .png: --screenshot writes NOTHING, silently, for a
  # path with any other extension.
  rm -f "$2"
  tmp="${2%.png}.partial.$$.png"; rm -f "$tmp"
  # On Windows the browser is a native program: hand it a C:\ path, not a /tmp one it cannot
  # resolve, and its own throwaway profile, so it cannot pass the job to a window the user already
  # has open and exit at once with nothing written.
  shot="$tmp"; profile=""
  if [ "$WIN" = 1 ]; then
    shot="$(cygpath -w "$tmp")"
    profile="$(mktemp -d "${TMPDIR:-/tmp}/adapty-chrome.XXXXXX")"
  fi
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars $LINUX_FLAGS \
    --window-size="$WINDOW" --virtual-time-budget="$3" \
    ${profile:+--user-data-dir="$(cygpath -w "$profile")"} \
    --screenshot="$shot" "$1" >/dev/null 2>"$CHROME_LOG" &
  c=$!; CHILD=$c
  ticks=$(( $4 * 2 )); waited=0; last=-1; SHOT_END=timeout
  while [ "$waited" -lt "$ticks" ]; do
    kill -0 "$c" 2>/dev/null || { SHOT_END=exited; break; }
    # Test first: `wc -c <"$tmp"` would leak the shell's own redirect error while it is missing.
    if [ -f "$tmp" ]; then sz=$(wc -c <"$tmp" | tr -d ' '); else sz=0; fi
    # Non-empty AND unchanged since the last poll: the browser has finished writing.
    if [ "$sz" -gt 0 ] && [ "$sz" = "$last" ]; then SHOT_END=done; break; fi
    last="$sz"
    waited=$((waited + 1))
    sleep 0.5
  done
  # Its helpers first: killing only the main process left renderer and GPU processes running.
  command -v pkill >/dev/null 2>&1 && pkill -9 -P "$c" 2>/dev/null
  kill -9 "$c" 2>/dev/null
  wait "$c" 2>/dev/null
  CHILD=""
  [ -n "$profile" ] && rm -rf "$profile"
  if [ -s "$tmp" ]; then mv -f "$tmp" "$2"; SHOT_END=done; else rm -f "$tmp"; fi
}

# What the browser said on its way out, which is the only clue when it writes nothing.
browser_said() {
  grep -v '^[[:space:]]*$' "$CHROME_LOG" 2>/dev/null | tail -n 4 | cut -c1-220 | sed 's/^/           | /' >&2
}

# Is the render host reachable? When it cannot be resolved or refuses the connection, the browser
# screenshots its own error screen into a perfectly valid PNG. Testing the host directly is
# unambiguous where the pixels are not, names the actual problem, and costs ~0.3 s.
probed=0
host_ok=0          # 1 only when curl actually RAN and the host answered -- not merely "probed"
probe_host() {  # $1 = any URL on the host
  [ "$probed" = 1 ] && return 0
  probed=1
  command -v curl >/dev/null 2>&1 || return 0
  origin=$(printf '%s' "$1" | sed -E 's#^(https?://[^/]+).*#\1#')
  if ! curl -s -o /dev/null -m 10 "$origin"; then
    echo "shoot: the render host $origin is unreachable from here." >&2
    echo "       The browser would screenshot its own error page into a valid PNG, which is how a" >&2
    echo "       broken network gets reported as a broken config. Fix the network, then retry." >&2
    exit 1
  fi
  host_ok=1
}

preview_url() {  # $1 = config, $2 = screen
  if [ "$2" = "__default__" ]; then $ADAPTY_BIN flows config preview "$1" $DEVFLAG 2>&1
  else $ADAPTY_BIN flows config preview "$1" --screen "$2" $DEVFLAG 2>&1; fi
}

i=0; failed_in_a_row=0
for s in $SCREENS; do
  i=$((i+1))
  left=$(( TIME_LIMIT - SECONDS ))
  if [ "$left" -le 0 ]; then
    echo "shoot: TIME_LIMIT of ${TIME_LIMIT}s reached. Not rendered: $(not_done)" >&2
    echo "       Run those on their own, in the background, or raise TIME_LIMIT." >&2
    break
  fi
  echo "[$i/$TOTAL] $s" >&2
  t0=$SECONDS
  png="$(png_for "$s")"
  url="$(preview_url "$RCFG" "$s")"
  case "$url" in
    http*) ;;
    *) echo "shoot: preview failed for $s: $(printf '%s' "$url" | head -2)" >&2; exit 1 ;;
  esac
  # Past ~100K characters the render page draws its own "There's been a glitch" page, which passes
  # the pixel guard as a real screen. Windows caps a whole command line at 32,767 characters.
  if [ "$WIN" = 1 ]; then limit=30000; else limit=100000; fi
  if [ "${#url}" -gt "${URL_LIMIT:-$limit}" ]; then
    # What grows a URL is image previews (thousands of characters each, and the render downloads
    # the full image anyway) and languages the page does not draw. A copy without both draws the
    # same screen; the one layout it can change is a sliding-sheet cover image with a hug height,
    # whose crop is decided from the preview (media.md).
    lean="$OUT/lean-$CFGSIG$LOCTAG.json"
    if [ -s "$lean" ] || {
         dflt=$($PY -c 'import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8")); c=d["config"] if isinstance(d.get("config"),dict) else d
print((c.get("localization") or {}).get("defaultLocale") or "")' "$RCFG" 2>/dev/null)
         copy_config "$RCFG" "$lean" --no-previews ${dflt:+--locale "$dflt"} 2>/dev/null; }; then
      lurl="$(preview_url "$lean" "$s")"
      case "$lurl" in
        http*) if [ "${#lurl}" -le "${URL_LIMIT:-$limit}" ]; then
                 echo "   URL is ${#url} chars — rendering $s from a copy without image previews and other languages" >&2
                 echo "   (same screen; only a sliding-sheet cover image with a hug height can crop differently)" >&2
                 url="$lurl"
               fi ;;
      esac
    fi
  fi
  if [ "${#url}" -gt "${URL_LIMIT:-$limit}" ]; then
    if [ "$WIN" = 1 ]; then   # the command line cannot carry it at all
      echo "   SKIPPED $s — the preview URL is ${#url} characters, longer than a Windows command line." >&2
      echo "           The file-input route has no such limit; install it once and rerun:" >&2
      echo "           npm i --prefix ~/.cache/adapty-flow-playwright playwright-core" >&2
      continue
    fi
    echo "   URL is ${#url} chars even without previews; rendering it anyway. LOOK AT IT: a page" >&2
    echo "   this long has drawn its own error page instead of the screen." >&2
  fi
  probe_host "$url"
  wd=${WATCHDOG:-180}; [ "$wd" -gt "$left" ] && wd=$left
  shoot_one "$url" "$png" "$BUDGET" "$wd"
  if [ "$SHOT_END" = exited ]; then
    # The browser quit on its own and wrote nothing: it could not start or could not run here. A
    # longer wait changes nothing, and neither will the next screen.
    echo "   FAILED  $s — the browser exited without a screenshot. It said:" >&2
    browser_said
    echo "           Browser: $CHROME. Set CHROME to another Chromium-based browser, or install the" >&2
    echo "           file-input route once: npm i --prefix ~/.cache/adapty-flow-playwright playwright-core" >&2
    break
  fi
  if [ ! -s "$png" ]; then
    left=$(( TIME_LIMIT - SECONDS ))
    if [ "$left" -gt 30 ]; then
      # Escalate before concluding anything: on a slow render host an 8 s budget produced no file
      # while 60 s produced a correct screenshot of the same config ~72 s later.
      echo "   slow host? retrying $s at 60s..." >&2
      wd=${WATCHDOG_RETRY:-300}; [ "$wd" -gt "$left" ] && wd=$left
      shoot_one "$url" "$png" 60000 "$wd"
    fi
  fi
  if [ -s "$png" ] && [ "$host_ok" = 1 ] && ! $PY "$HERE/render-measure.py" --sanity "$png" >/dev/null 2>&1 \
     && [ $(( TIME_LIMIT - SECONDS )) -gt 30 ]; then
    # A flat page from a host that answered is often a load hiccup that a second shot clears. The
    # retry goes to its own name, so a retry that lands nothing keeps the first shot.
    echo "   $s came back flat; retrying once (a load hiccup usually clears)" >&2
    again="${png%.png}-again.png"
    wd=${WATCHDOG:-180}; [ "$wd" -gt $(( TIME_LIMIT - SECONDS )) ] && wd=$(( TIME_LIMIT - SECONDS ))
    shoot_one "$url" "$again" "$BUDGET" "$wd"
    if [ -s "$again" ] && $PY "$HERE/render-measure.py" --sanity "$again" >/dev/null 2>&1; then
      mv -f "$again" "$png"; echo "   $s drew on the retry" >&2
    else
      rm -f "$again"
    fi
  fi
  if [ -s "$png" ]; then
    failed_in_a_row=0
    # A non-empty PNG is NOT a render: the browser screenshots its own error page perfectly.
    # `--sanity` flags flatness AND ink confined to one band AND nothing wider than a line of text
    # (render-measure.py records the calibration, and the one case still not separable: a screen
    # made only of text -- the host probe above covers that one).
    if $PY "$HERE/render-measure.py" --sanity "$png" >/dev/null 2>&1; then
      echo "   rendered $s in $((SECONDS - t0))s -> $png"
      shots="$shots $png"; n=$((n+1)); done_ids="$done_ids $s"
    elif [ "$host_ok" = 1 ]; then
      # The host ANSWERED, so this is not the offline error page. A sparse screen and a served
      # error page are not separable by pixels, so keep the file and say both things: renaming it
      # would destroy a correct render. Looking at the PNG is what settles it.
      echo "   rendered $s -> $png  (FLAT — look closely)"
      $PY "$HERE/render-measure.py" --sanity "$png" >&2
      echo "           The host answered, so this is NOT the offline error page. Either the" >&2
      echo "           screen really is this sparse, or the page served an error. LOOK AT IT." >&2
      shots="$shots $png"; n=$((n+1)); done_ids="$done_ids $s"
    else
      bad="$OUT/NOT-A-RENDER-$(basename "$png")"
      mv "$png" "$bad"
      echo "   NOT A RENDER  $s — the PNG is a flat page, almost certainly an error screen:" >&2
      $PY "$HERE/render-measure.py" --sanity "$bad" >&2
      echo "           Renamed so it cannot be mistaken for evidence. Load the preview URL in a" >&2
      echo "           real browser: this is a host/network problem far more often than a config one." >&2
    fi
  else
    failed_in_a_row=$((failed_in_a_row+1))
    echo "   FAILED  $s — no file even at 60s. Load the URL in a REAL browser before blaming the" >&2
    echo "           config: the page can render there while headless yields nothing." >&2
    browser_said
    if [ "$failed_in_a_row" -ge 2 ]; then
      echo "shoot: two screens in a row drew nothing; the render host is too slow from here right now." >&2
      echo "       Not rendered: $(not_done)" >&2
      break
    fi
  fi
done
rm -f "$CHROME_LOG"

finish $([ "$n" -eq "$TOTAL" ] && echo 0 || echo 1)
