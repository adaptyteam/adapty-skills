#!/bin/bash
# All of phase 3 in ONE tool call. Runs every gate over the SAME bytes and prints one verdict.
#
#   gates.sh draft.json                          # local gates only
#   gates.sh draft.json <APP_UUID> <FLOW_ID>     # + the ids read and the publish gate
#
# Why this exists: the gates were three separate commands, i.e. three agent turns at ~30 s of
# round-trip each — far more than the checks themselves cost. Order is deliberate: the local
# structural walk first (it names every defect at once), then the schema shape check, then
# `validate` (one fatal per round trip, and the only one that needs the network).
#
# Exit 0 only if nothing blocking was found. `validate` needs an existing flow id purely as a
# target; the call is read-only and saves nothing.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="${1:?usage: gates.sh <config.json> [APP_UUID FLOW_ID]}"
APP="${2:-}"; FLOW="${3:-}"
[ -f "$CFG" ] || { echo "gates: no such file: $CFG" >&2; exit 2; }
# Python 3 by RUNNING each candidate, never by name: on Windows `python3` is usually the Microsoft
# Store stub, which is on PATH, prints an install hint and fails — so the structural step failed
# while the gate itself looked broken. `-X utf8` because Windows otherwise reads and prints the
# config in the console code page, and a non-Latin locale does not survive that. PYTHON= wins.
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3 python "py -3"; do
    if $c -X utf8 -c 'import sys; sys.exit(sys.version_info[0] != 3)' >/dev/null 2>&1; then PY="$c -X utf8"; break; fi
  done
fi
[ -n "$PY" ] || { echo "gates: no Python 3 found (tried python3, python, py -3) — set PYTHON=/path" >&2; exit 2; }
# Absolutise both paths NOW. The schema step runs inside `cd "$AJV_DIR"`, so a relative path
# resolves against the ajv cache dir, the node call cannot find the file, and because that step is
# wrapped in `|| true` the gate is SILENTLY SKIPPED while the run still reports a pass. The -f
# guard above does not catch it: it runs in the original cwd, where the relative path is fine.
CFG="$(cd "$(dirname "$CFG")" && pwd)/$(basename "$CFG")"
[ -n "${BASELINE:-}" ] && [ -f "$BASELINE" ] && \
  BASELINE="$(cd "$(dirname "$BASELINE")" && pwd)/$(basename "$BASELINE")"
# The publish gate takes the BARE config and answers an envelope with "Invalid flow input", which
# reads exactly like a broken document. `config get`/`config update` return the envelope, so unwrap
# one here instead of letting the gate fail on the file's shape.
if $PY -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if isinstance(d,dict) and isinstance(d.get("config"),dict) else 1)' "$CFG" 2>/dev/null; then
  BARE="$(mktemp "${TMPDIR:-/tmp}/gates-bare.XXXXXX")"
  $PY -c 'import json,sys; json.dump(json.load(open(sys.argv[1]))["config"], open(sys.argv[2],"w"))' "$CFG" "$BARE"
  echo "gates: $CFG is an envelope; checking its .config"
  CFG="$BARE"
fi

# The CLI is the one SKILL.md phase 1 resolved: pass it as ADAPTY, or have `adapty` on PATH. This
# script never launches a package itself, so what runs is always the CLI the run already chose.
ADAPTY_BIN=${ADAPTY:-}
if [ -z "$ADAPTY_BIN" ] && command -v adapty >/dev/null 2>&1; then ADAPTY_BIN="adapty"; fi
if [ -z "$ADAPTY_BIN" ] && [ -n "$APP" ]; then
  echo "gates: no Adapty CLI. Install it (npm install -g adapty) or pass the command: ADAPTY='npx --yes adapty@latest' gates.sh ..." >&2
  exit 2
fi

fail=0
# The digest through Python, which this script already requires: `md5` is not on PATH in every
# shell (a sandboxed one on a Mac lacks it) and macOS has no `md5sum`, so the old fallback chain
# printed "command not found" and an empty digest.
md5="$($PY -c 'import hashlib, sys; print(hashlib.md5(open(sys.argv[1], "rb").read()).hexdigest())' "$CFG")"
echo "== gates over $CFG  (md5 ${md5:0:12})"

echo "-- 1/4 structure (verify-config.py)"
# BASELINE does double duty: the schema step uses it to suppress a v9 flow's pre-existing
# findings, and verify-config.py uses it to tell a price THIS draft invented from one the flow
# already had. Both are already absolute (see above), and this runs before any `cd`.
if [ -n "${BASELINE:-}" ] && [ -f "$BASELINE" ]; then
  if $PY "$HERE/verify-config.py" --baseline "$BASELINE" "$CFG"; then :; else fail=1; fi
else
  if $PY "$HERE/verify-config.py" "$CFG"; then :; else fail=1; fi
fi

echo "-- 2/4 schema shape (ADVISORY — does not decide the verdict)"
# --config, not a positional. Pass BASELINE=flow.backup.json when editing a fetched config, or a
# v9 flow buries you in pre-existing findings that are not yours.
# ajv is installed ONCE into a cache dir, never resolved through `npx` per run. Measured: the
# npx form cost 12.7 s of a 24 s gate run — over half of it — for a step that is only advisory.
# From the cache dir the same check is 0.3 s. `loadAjv` searches cwd first, hence the subshell cd.
AJV_DIR="${AJV_DIR:-$HOME/.cache/adapty-flow-schema}"
if [ -f "$HERE/validate-with-schema.mjs" ]; then
  if [ ! -d "$AJV_DIR/node_modules/ajv" ]; then
    echo "   (installing ajv once into $AJV_DIR)"
    mkdir -p "$AJV_DIR"
    npm i --prefix "$AJV_DIR" ajv@8 --silent --no-audit --no-fund >/dev/null 2>&1 \
      || echo "   (could not install ajv — schema step skipped)"
  fi
  if [ -d "$AJV_DIR/node_modules/ajv" ]; then
    # no arrays: macOS ships bash 3.2, where an empty array under `set -u` is an unbound variable
    if [ -n "${BASELINE:-}" ]; then
      ( cd "$AJV_DIR" && node "$HERE/validate-with-schema.mjs" \
          --config "$CFG" --baseline "$BASELINE" ) 2>&1 | tail -15 || true
    else
      ( cd "$AJV_DIR" && node "$HERE/validate-with-schema.mjs" --config "$CFG" ) 2>&1 | tail -15 || true
    fi
  fi
else
  echo "   (validate-with-schema.mjs missing — skipped)"
fi

# Advisory on purpose: `validate` outranks the schema in both directions, and configs the builder
# itself saves still disagree with it in places (a `border.style`, an icon's `width`). Read its
# findings — on an element you wrote they are usually real — but do not let them gate.

# `validate` answers `valid: true` for a product id the app does not have, a store code in place
# of an Adapty id, and an offer that is not one of its product's offers (all measured, adapty
# 0.15.0); the builder then refuses the publish. So the ids are read against the app here: one
# `products list`, and one `product-offers list` per product bound with an offer. A flow that binds
# nothing makes no call.
echo "-- 3/4 bound products and offers exist in the app"
if [ -z "$APP" ]; then
  echo "   SKIPPED — pass APP_UUID to read them"
else
  if $PY - "$CFG" "$APP" "$ADAPTY_BIN" <<'PYEOF'
import json, re, shlex, subprocess, sys
cfg, app, cli = json.load(open(sys.argv[1], encoding='utf-8')), sys.argv[2], shlex.split(sys.argv[3])
pairs, where = set(), {}
def bind(pid, oid, at):
    if isinstance(pid, str) and pid:
        oid = oid if isinstance(oid, str) and oid else None
        pairs.add((pid, oid)); where.setdefault((pid, oid), at)
def walk(o, at):
    if isinstance(o, dict):
        if o.get('type') == 'product' and isinstance((o.get('props') or {}).get('product'), dict):
            p = o['props']['product']; bind(p.get('id'), p.get('offerId'), at)
        bought = (o.get('payload') or {}).get('product') if o.get('type') == 'purchase' else None
        if isinstance(bought, dict) and bought.get('type') == 'const' and isinstance(bought.get('value'), dict):
            bind(bought['value'].get('id'), bought['value'].get('offerId'), at)
        if o.get('kind') == 'product':
            bind(o.get('id'), o.get('offerId'), at)
        if isinstance(o.get('fallbackOfferId'), str):
            bind(o.get('id'), o['fallbackOfferId'], at)
        v = o.get('variableId')
        if isinstance(v, str) and re.match(r'[0-9a-fA-F-]{36}(@\w+)?\.', v):
            bind(v[:36], None, at)
        for v in o.values(): walk(v, at)
    elif isinstance(o, list):
        for v in o: walk(v, at)
for s in cfg.get('screens') or []:
    walk(s, s.get('id'))
    for p in s.get('products') or []: bind(p.get('id'), p.get('offerId'), s.get('id'))
for sid, m in ((cfg.get('_meta') or {}).get('screens') or {}).items():
    for p in m.get('products') or []: bind(p.get('id'), p.get('offerId'), sid)
walk(cfg.get('components') or {}, 'a component')
if not pairs:
    print('   no products bound'); sys.exit(0)
def read(args):
    r = subprocess.run(cli + args + ['--app', app, '--json'], capture_output=True, text=True)
    try: d = json.loads(r.stdout)
    except Exception: d = None
    if not isinstance(d, dict) or 'data' not in d:
        raise RuntimeError((r.stdout or r.stderr).strip()[:200])
    return d
try:
    prods, page = {}, 1
    while True:
        d = read(['products', 'list', '--page-size', '100', '--page', str(page)])
        prods.update({p['id']: p for p in d['data']})
        if page >= ((d.get('meta') or {}).get('pagination') or {}).get('pages', 1): break
        page += 1
except RuntimeError as e:
    print(f'   COULD NOT READ products list ({e}) — check each id with `products get` before publishing')
    sys.exit(1)
bad = 0
for pid in sorted({p for p, _ in pairs}):
    if pid not in prods:
        bad += 1
        at = next(a for (p, _), a in sorted(where.items(), key=str) if p == pid)
        print(f'   NOT IN THIS APP: product {pid} (on {at}). validate passes it; rebind it to a'
              f' product from `products list`')
for pid in sorted({p for p, o in pairs if o and p in prods}):
    try:
        offers = {o['id']: o for o in read(['product-offers', 'list', '--product', pid])['data']}
    except RuntimeError as e:
        print(f'   COULD NOT READ the offers of {prods[pid].get("title", pid)} ({e})'); bad += 1; continue
    for oid in sorted(o for p, o in pairs if p == pid and o and o not in offers):
        bad += 1
        have = '; '.join(f'{o.get("title")} = {i}' for i, o in offers.items()) or 'none'
        print(f'   NOT AN OFFER OF {prods[pid].get("title", pid)}: {oid}. Bind an `id` from'
              f' `product-offers list` (its offers: {have})')
if not bad:
    print(f'   ok — {len({p for p, _ in pairs})} product(s), {len({o for _, o in pairs if o})} offer(s), all in this app')
sys.exit(1 if bad else 0)
PYEOF
  then :; else fail=1; fi
fi

echo "-- 4/4 publish gate (flows config validate)"
if [ -z "$APP" ] || [ -z "$FLOW" ]; then
  echo "   SKIPPED — pass APP_UUID and FLOW_ID to run it. A green local pass is NOT a publish gate."
  fail=1
else
  # ONE `validate` at a time across every gates.sh run on this machine. Gates over several flows
  # at once made validate answer http_502 for most of them; validate.md says to run it alone, but
  # agents run this script, so the script enforces it. `mkdir` is the lock because it is atomic
  # everywhere and macOS has no `flock`. The holder writes its pid; a lock whose holder is gone,
  # or that never got a pid, is taken over, and after ten minutes this run goes ahead anyway.
  LOCK="${TMPDIR:-/tmp}/adapty-gates-validate.lock"
  unlock_validate() { [ "$(cat "$LOCK/pid" 2>/dev/null)" = "$$" ] && rm -rf "$LOCK"; return 0; }
  held=1; waited=0; misses=0
  while ! mkdir "$LOCK" 2>/dev/null; do
    if [ ! -d "$LOCK" ]; then                     # released just now, or no lock can be made here
      misses=$((misses + 1)); [ "$misses" -lt 5 ] && continue
      held=0; break                               # run unserialized rather than not at all
    fi
    holder="$(cat "$LOCK/pid" 2>/dev/null || true)"
    if { [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; } \
        || { [ -z "$holder" ] && [ "$waited" -ge 10 ]; }; then
      rm -rf "$LOCK"; continue
    fi
    if [ "$waited" -ge 600 ]; then
      echo "   still locked by pid $holder after 10 minutes — validating anyway"; held=0; break
    fi
    [ "$waited" -eq 0 ] && echo "   waiting: another gates.sh run is validating (pid ${holder:-?}); validate runs one at a time, because parallel calls answer http_502"
    sleep 1; waited=$((waited + 1))
  done
  if [ "$held" -eq 1 ]; then
    echo "$$" > "$LOCK/pid"
    trap unlock_validate EXIT
    trap 'unlock_validate; exit 130' INT TERM
    [ "$waited" -gt 0 ] && echo "   validating now (waited ${waited}s)"
  fi

  run_validate() {  # $1 = config file -> the CLI's raw JSON answer, one 502 retried
    local raw
    raw="$($ADAPTY_BIN flows config validate --app "$APP" "$FLOW" --config-file "$1" --json 2>&1)"
    case "$raw" in *http_502*|*http_504*)
      echo "   validate answered a gateway error (the server, not your config); retrying once in 5 s" >&2
      sleep 5
      raw="$($ADAPTY_BIN flows config validate --app "$APP" "$FLOW" --config-file "$1" --json 2>&1)" ;;
    esac
    printf '%s\n' "$raw"
  }
  verdict_of() {  # $1 = config file -> the verdict, one line
    run_validate "$1" | $PY -c '
import json,sys
try: d=json.load(sys.stdin)
except Exception: print("UNPARSEABLE"); raise SystemExit
v=d.get("valid")
if v is True:  print("valid: true")
elif v is False:
    iss=d.get("issues") or []
    print("valid: false — " + "; ".join(str(i.get("message")) for i in iss[:3] or ["(no issues listed)"]))
else:
    print("API ERROR (not a verdict — retry this run alone, not beside another): " + json.dumps(d)[:160])
' 2>/dev/null
  }
  verdict="$(verdict_of "$CFG")"
  echo "   $verdict"
  case "$verdict" in "valid: true") ;; *) fail=1 ;; esac
  # A fatal the fetched config already had is not this run's, and it hides any fatal of this
  # run's behind it, since validate reports one per run. Without this line the agent cannot tell
  # the two apart; SKILL.md says what to do with it.
  case "$verdict" in "valid: false"*)
    # The backup is the `config get` envelope; validate takes the bare config inside it.
    bare="$(mktemp "${TMPDIR:-/tmp}/adapty-baseline.XXXXXX")"
    [ -n "${BASELINE:-}" ] && [ -f "$BASELINE" ] && $PY -c '
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
json.dump(d.get("config", d) if isinstance(d, dict) else d, open(sys.argv[2], "w", encoding="utf-8"))
' "$BASELINE" "$bare" 2>/dev/null
    if [ -s "$bare" ] && [ "$(verdict_of "$bare")" = "$verdict" ]; then
      echo "   ALREADY IN $(basename "$BASELINE"): the fetched config fails with this same fatal, before"
      echo "   this run's edit. It is not yours, and it hides anything of yours behind it."
    fi
    rm -f "$bare" ;;
  esac
fi

echo
if [ "$fail" -eq 0 ]; then echo "== ALL GATES PASS over ${md5:0:12}"; else echo "== NOT CLEAR — see above"; fi
exit "$fail"
