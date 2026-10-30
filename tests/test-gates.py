#!/usr/bin/env python3
"""`gates.sh` on a bare PATH and under parallel runs: the digest, the validate lock, the 502 retry.

Repo-only. Runs the shipped script as a subprocess with a stand-in `adapty` (ADAPTY=) that answers
from a state directory, so nothing reaches an account. PATH is `/usr/bin:/bin`: no `md5` (it lives
in /sbin on a Mac), no `md5sum`, no `node`, so the advisory schema step skips itself.

Why. Three field reports in one week: the digest printed "command not found" and came out empty
on a Mac; gates over several flows at once made `flows config validate` answer http_502 for most
of them; and a single 502 read as a failed gate. The script now hashes through Python, serialises
its `validate` call across every gates.sh run on the machine, and retries a gateway error once.

    DIGEST  -- a 12-character md5 with no md5/md5sum on PATH
    LOCK    -- three parallel runs never overlap inside `validate`, and the waiters say so
    STALE   -- a lock left by a dead process is taken over at once
    RETRY   -- a 502 then a verdict reads as the verdict

Usage: python3 tests/test-gates.py     # 0 all pass, 1 a case regressed
"""
import os, re, shutil, stat, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATES = os.path.join(ROOT, 'plugin', 'skills', 'flow-generator', 'references', 'gates.sh')
FIXTURE = os.path.join(ROOT, 'tests', 'fixtures', 'reviews-carousel.json')
APP, FLOW = '00000000-0000-4000-8000-000000000000', '11111111-1111-4111-8111-111111111111'
fails = []

# The stand-in CLI. Each call marks itself ACTIVE for a second; a second call arriving while one
# is active records an overlap. `FAKE_502=n` answers the first n calls with the CLI's own JSON for
# a 502 (`code: http_502`), then a verdict.
FAKE = r'''#!/bin/bash
S="$FAKE_STATE"
n=$(( $(cat "$S/calls" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$S/calls"
mkdir "$S/active" 2>/dev/null || echo overlap >> "$S/overlaps"
sleep 1
rmdir "$S/active"
if [ "$n" -le "${FAKE_502:-0}" ]; then
  printf '{"error": {"code": "http_502", "message": "Bad Gateway", "status": 502}}\n'
  exit 4
fi
printf '{"valid": true, "issues": []}\n'
'''


def check(name, ok, detail=''):
    print(f'  {"ok  " if ok else "FAIL"}  {name}')
    if not ok:
        fails.append(f'{name}: {detail[:900]}')


def env_for(tmp, **extra):
    fake = os.path.join(tmp, 'adapty')
    if not os.path.exists(fake):
        open(fake, 'w').write(FAKE)
        os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
        os.makedirs(os.path.join(tmp, 'state'), exist_ok=True)
    e = {'PATH': '/usr/bin:/bin', 'HOME': tmp, 'TMPDIR': tmp + '/',
         'PYTHON': sys.executable, 'PYTHONDONTWRITEBYTECODE': '1',
         'ADAPTY': fake, 'FAKE_STATE': os.path.join(tmp, 'state'),
         'AJV_DIR': os.path.join(tmp, 'ajv')}
    e.update(extra)
    return e


def gates(env, *args):
    return subprocess.Popen(['/bin/bash', GATES, FIXTURE, *args], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


if shutil.which('md5', path='/usr/bin:/bin') or shutil.which('md5sum', path='/usr/bin:/bin'):
    print('  note  md5 or md5sum is on /usr/bin:/bin here; the DIGEST case proves less')

with tempfile.TemporaryDirectory() as tmp:
    out = gates(env_for(tmp)).communicate(timeout=120)[0]
    m = re.search(r'\(md5 ([0-9a-f]*)\)', out)
    check('DIGEST: 12 hex characters with no md5 or md5sum on PATH',
          bool(m) and len(m.group(1)) == 12 and 'command not found' not in out, out)

with tempfile.TemporaryDirectory() as tmp:
    env = env_for(tmp)
    t0 = time.time()
    runs = [gates(env, APP, FLOW) for _ in range(3)]
    outs = [p.communicate(timeout=180)[0] for p in runs]
    took = time.time() - t0
    overlaps = os.path.exists(os.path.join(tmp, 'state', 'overlaps'))
    check('LOCK: three parallel runs never validate at the same moment',
          not overlaps and all('valid: true' in o for o in outs), '\n---\n'.join(outs))
    check('LOCK: a run that waits says why',
          any('waiting: another gates.sh run is validating' in o for o in outs),
          '\n---\n'.join(outs))
    check('LOCK: released on exit, nothing left behind',
          not os.path.exists(os.path.join(tmp, 'adapty-gates-validate.lock')), os.listdir(tmp))

with tempfile.TemporaryDirectory() as tmp:
    env = env_for(tmp)
    lock = os.path.join(tmp, 'adapty-gates-validate.lock')
    os.mkdir(lock)
    dead = subprocess.Popen(['/bin/sleep', '0']); dead.wait()
    open(os.path.join(lock, 'pid'), 'w').write(str(dead.pid))
    t0 = time.time()
    out = gates(env, APP, FLOW).communicate(timeout=120)[0]
    check('STALE: a lock whose holder is gone is taken over at once',
          'valid: true' in out and time.time() - t0 < 30, out)

with tempfile.TemporaryDirectory() as tmp:
    out = gates(env_for(tmp, FAKE_502='1'), APP, FLOW).communicate(timeout=120)[0]
    check('RETRY: one 502, then the verdict',
          'retrying once' in out and 'valid: true' in out and 'ALL GATES PASS' in out, out)
with tempfile.TemporaryDirectory() as tmp:
    out = gates(env_for(tmp, FAKE_502='2'), APP, FLOW).communicate(timeout=120)[0]
    check('RETRY: two 502s are a failed call, not a verdict, and say to run alone',
          'API ERROR (not a verdict' in out and 'NOT CLEAR' in out, out)

print()
if fails:
    print(f'{len(fails)} FAILED')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('all checks passed')
