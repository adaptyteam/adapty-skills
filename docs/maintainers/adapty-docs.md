# Maintainer notes: `adapty-docs`

Evidence and history behind the rules in `CLAUDE.md`: measurements, test rounds, dated findings. Not loaded into sessions. Read the part you need before changing a rule; add new findings here, never to `CLAUDE.md`.

## Files

- `plugin/skills/adapty-docs/SKILL.md` — the docs-discovery skill, and the only file in the repo that maps
  a question to a docs index. Self-contained, no references, no scripts. Owns the routing table
  (`<platform>-llms.txt` / `flows-llms.txt` / `api-llms.txt` / `tutorial-llms.txt` / `llms.txt`
  with each one's token cost), the never-assemble-a-slug rule and what a wrong guess costs, the
  `# File:` grep recipe for the full-text aggregates, the seven generated SDK reference sites, and
  the session marker. **It names no SDK symbols and must not start** — the symbol lint's scope
  guard covers it, and it has no platform to verify one against.

## Conventions and findings: `adapty-docs`

- **The routing table is the skill.** Everything else in the file supports it. The reason it has to
  exist at all is measured: **the root `llms.txt` never names the sub-indexes**, so an agent that
  starts at the documented entry point cannot learn that `ios-llms.txt`, `flows-llms.txt`,
  `api-llms.txt` or `tutorial-llms.txt` exist. Re-check that before deciding the table is
  redundant — if the docs ever link the sub-indexes from the root, most of this skill stops earning
  its place.
- **Every size in the table is measured, and they are the argument for the ordering.** Per-platform
  index ~2k tokens, `flows` ~6k, `api` ~2k, `tutorial` ~14k, root `llms.txt` ~33k. The full-text
  aggregates are ~121k per platform and **~560k for `tutorial`**, which is larger than a context
  window. Re-measure rather than trusting these; they move as the docs grow.
- **A wrong slug is not a cheap error, which is why the never-guess rule is phrased around cost.**
  A 404 returns a **~17k-token HTML page** whose title is the only sign anything went wrong, and 7
  of 10 plausible guesses for two real pages were 404. An agent that does not know this reads the
  error page as content.
- **The full-text files are grep targets, never fetch targets, and the marker is what makes that
  work.** Every article in every aggregate is delimited by `# File: <slug>` — verified present in
  all nine (`ios` 56, `android` 52, `flutter` 55, `react-native` 60, `unity` 55, `kmp` 51,
  `capacitor` 47, `tutorial` 347, `api` 21). The shipped recipe prints slugs and stops there
  **deliberately**: an earlier version piped through `sed` to build full URLs, and the URL literal
  inside the `sed` expression was scraped by `lint-links.mjs` as a dead link. Keep the recipe free
  of bare URL literals inside shell quoting, or the lint reddens on a working command.
- **This skill must name no SDK symbols.** It has no platform, so `lint-symbols.mjs` cannot verify
  one against a docs aggregate — and the scope guard now covers `adapty-docs`, so a symbol turns
  the lint red. Describe a method's purpose and link its reference site; never write its name.
- **`<platform>` is the lint-safe placeholder.** `lint-links.mjs` skips any URL containing
  `{}<>*…`, so `https://adapty.io/docs/<platform>-llms.txt` is correctly treated as a template.
  Anything else — a bare `platform`, a real example like `ios` — gets fetched and checked.
- **The four API pages are spec headers, not the API docs.** `api-adapty.md` and its siblings carry
  auth and servers; the per-endpoint pages are separate, and `api-llms.txt` is the index that maps
  `METHOD /path` to each operation's own page. Route an endpoint question to the index, not to the
  spec header.
- **`android.adapty.io` is the canonical Android reference host.** `kotlin.adapty.io` redirects to
  it and is what the docs index uses; the site footer uses the canonical form, and so does this
  skill.

### Finding 39 (2026-09-16): the skill changes the PATH, not the PRICE — correctness and cost both null, mechanism a complete separation

Six agents, three per arm, arms differing only in the new skill; scenario, rubric and the null
clause written to disk before dispatch (`docs/superpowers/baselines/2026-09-16-adapty-docs-baseline.md`).
The question was a product one whose correct answer is counter-intuitive — the Adapty-side price is
a placeholder fixed at creation that never reaches the store, and the customer-facing price comes
from StoreKit at paywall open — so the plausible wrong answer ("wait for the sync") was confidently
stateable. Scenario chosen after rejecting two others for contamination: `rtdn` and `refund` appear
in 9 and 8 repo files, `store-sync` in **zero**.

**Correctness: 6 of 6 in both arms**, so the eighth null in this repo's record and the **seventh**
time predicting control failure has been wrong. **Cost: also null** — 210k control tokens against
213k treatment, 15.3 tool calls against 16.3. The 33k the routing table saves was reinvested in
cross-checking rather than banked, so **no token-saving claim is supported by this round**, which
matters because the docs' own banner promises exactly that.

**What separated is the route, completely: 3/3 control opened the root `llms.txt` and 0/3 opened a
sub-index; treatment was the exact inverse.** The mechanism is not agent quality, it is
availability — `llms.txt` does not name the sub-indexes, so control could not have chosen one. That
makes this the gate's information-not-convenience case, and it is why the round separated on
mechanism where `helper-green` and `video-green` did not.

**The honest limit, and it is the whole round-2 scenario.** This question was *answerable from the
root index*, so control never took a wrong turn, and the two rules with the strongest measurements
behind them — never assemble a slug, grep the aggregates — were never load-bearing for the outcome.
Round 2 must ask something the root index cannot resolve, where the answer exists only inside a
`-llms-full.txt`, so the recipe has to carry the result rather than shorten the route. Two
consecutive clean rounds remain the bar, and this is one round that is null on both scored
dimensions.

**Acted on per the pre-registration**: the one advisory section was cut in half. Everything kept is
a fact no agent can derive, and treatment runs used three of the four unprompted — including one
that reached a second index (`api-llms.txt`) to cross-check a claim against the CLI reference, and
one that inferred the `?ref=skill-dev-` convention from CLAUDE.md without being told.

### Round 2 (2026-09-16): a full-text-only question, and it was null too — the routing separation replicates, the outcome separation is still zero

Round 1's stated limit was that its question was answerable from the root index. Round 2 was built
to remove that: a **symptom** question about a Flow Builder paywall whose elements had been renamed,
whose decisive fact — *renaming a progress-bar segment updates its references automatically, the one
documented exception* — occurs **once in the entire corpus**, in `flow-common-issues`, and **zero
times anywhere in this repo**. Scorer written and self-tested against the real doc sentence before
dispatch, with a plausible-wrong-answer negative.

**All six runs passed all seven rows, control included.** Control found the one-sentence exception
3/3. Cost was again null and slightly against treatment (216k control tokens against 220k, 15.3 tool
calls against 17.7). **The route separated again and identically: control opened the 33k root
`llms.txt` first 3/3, treatment opened the 6k `flows-llms.txt` first 3/3**, and both arms then read
the same two articles. Across the two rounds that is **6/6 against 0/6 on routing and zero on
outcome**.

**The scenario flaw is the transferable finding, and it is mine.** I pre-registered "not reachable
from any index" and verified it by grepping the index files for `element id`, `renam` and
`progress.bar` — a check that passed and measured the wrong thing. The index describes that article
as *"Fix the issues that stop a flow from previewing, publishing, or behaving the way you built
it"*, which matches the symptom **semantically while sharing no keyword with it**. **I tested
lexical reachability and called it semantic reachability.** To claim an answer is not
index-reachable, read the candidate descriptions as an agent would and name the one you would open;
a keyword count is not that check. That belongs in `docs/green-round-gate.md`.

**Acted on per the pre-registration**: the grep section lost its own heading and its claim to find
what indexes cannot, dropping from 22 lines to 9 and keeping only the measured half — the sizes, do
not fetch one, and the `# File:` marker if you grep anyway. Skill 834 → 753 words.

**Standing conclusion, and it bounds what may be claimed for this skill.** Two consecutive nulls on
outcome mean **no quality claim and no token-saving claim is supported**. What is supported is that
the cheap indexes are undiscoverable from `llms.txt`, so the routing table makes the route
deterministic instead of dependent on the root index happening to carry the answer. A third arm
comparison against this hypothesis is not worth running: two deliberately hard scenarios both
produced competent control answers.
