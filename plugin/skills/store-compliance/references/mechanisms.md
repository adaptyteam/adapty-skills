# `store-compliance` mechanism reference

Per-check evidence for the four checks in `store-check.py` that a store REQUIRES: Restore, the
Terms and Privacy links, and a way out. What each looks at, its severity and why, its
calibration, and the trap it closes. **Read this before changing one.** The advisory
store-review checks are documented in [`store-review.md`](store-review.md).

Calibration corpus: the tracked flow fixtures under `tests/fixtures/` plus
`tests/catalog-fixture.json`, and five real flows measured when these checks were written.
`tabs-paywall.json` is the control: it carries a real `openUrl` × 2 to `/terms` and
`/privacy`, a real `restorePurchases`, and a `closeFlow`, so every check here has a real
passing case to stay silent on, not just an absence of selling screens.
`timeline-anchored.json` carries no actions at all, so `no-escape-in-flow` fires on it,
correctly, as a `question`.

## The mechanisms

Grouped as one family because these checks share a rationale (App Store 3.1.1/3.1.2 and
the Play equivalents) and a fix shape.

| Check | Severity | Why | Calibration |
| :--- | :--- | :--- | :--- |
| `no-restore` — the flow sells (binds a product, or carries a `purchase` action) but has no `restorePurchases` action anywhere | blocker | App Store 3.1.1 requires a restore path | **fires**: 3 of 4 real selling flows measured, including one whose copy literally says "Restore purchase". **silent**: any flow once a `restorePurchases` action exists anywhere (calibrated by injection) |
| `no-terms-link` / `no-privacy-link` — a selling flow has no `openUrl` action whose URL tokenizes to a terms/EULA or privacy vocabulary word (`privacy` also inside a run-together segment, `/privacypolicy`), or whose button's own text names it ("Privacy Policy", "Terms of Use"); a label never makes a link absent. The URL is a catalog entry and is read in the default locale; reading the stored `{_lid}` ref instead finds no URL at all and fires both checks on a paywall that has both links | blocker (no `openUrl` at all, or every `openUrl` is plainly the other legal page or a checkout by its URL or label; `legal` and `policy` never count as plainly other) or question (an `openUrl` exists but no URL matches) | App Store 3.1.2 requires both links on a subscription screen | **fires as blocker**: `openUrl` occurs in **none** of the 5 live flows measured, so no flow there ships a working legal link. **silent**: `tabs-paywall.json` (real `/terms` and `/privacy` URLs) |
| `no-escape-from-paywall` — a selling screen has no `closeFlow`/`navigateBack` reachable via the navigation graph (`navigate`/`navigateNext` edges) | blocker | a user who does not buy must be able to leave | **fires**: one live paywall (only action is `purchase`); silent on `tabs-paywall.json` and the other 3 live paywalls, each with one escape reachable |
| `no-escape-in-flow` — no `closeFlow`/`navigateBack` anywhere in the flow at all, on ANY flow (selling or not) | question | may be legitimate if the host app presents the flow modally with a system dismiss | fires on `d1faba75` (3 screens, no dismissal anywhere) and on `timeline-anchored.json` (1 screen, zero actions of any kind — a true positive on a non-selling flow with genuinely no way off); silent once a `closeFlow`/`navigateBack` exists anywhere, selling or not |

### False-positive / false-negative traps

| Trap | What would have shipped |
| :--- | :--- |
| Detecting a legal link by the button's **label** | Reports a paywall with real, working `/terms` and `/privacy` links as non-compliant when the buttons read "Legal". Detection must live on the `openUrl` action's URL payload, never the label. |
| Matching a legal-link vocabulary word by **substring containment** | A false negative: `tos` matches inside `photos` and `autos`, `legal` matches inside `illegally`. A paywall whose only `openUrl` points at `/photos/hero.jpg` silenced the terms check under substring matching. The fix tokenizes the URL on non-alphanumeric runs and requires an exact token match — deliberately trading a concatenated path with no separator (`/termsofservice`) into a `question` rather than a silent false pass, because a question is honest and a false silence on a 3.1.2 requirement is not. |
| Detecting an escape by its **label** | **7 of 9** real escape affordances measured across the corpus are icon-only with no text at all; the two that do carry text read `'I already have an account'` and `'Leave for now'` — neither contains *close*, *skip* or *later*. A label-based close check finds **0 of 9**. Detection binds to the action type (`closeFlow`/`navigateBack`), graph-reachable rather than screen-local; the label is reported as evidence for the human to judge, never used for detection. |
| Assuming text naming an action proves the action exists | `el_089T`'s "Restore purchase · Terms · Privacy" is the clearest instance: it renders exactly like a working row and satisfies nothing. Every compliance check tests for the *action*, never the word — this is the same rule as `flow-audit`'s `dead-affordance` check, applied in both directions (text without an action, and an action without text). |

## Known limitations

- **A URL query string or fragment word can silence a legal-link check** — token matching
  runs over the whole URL string, so `?ref=terms-promo` on an unrelated page would match.

## The rule

A check ships only when it is **silent on every fixture in the corpus and fires on an
injected instance of its own defect.** Being silent on real data proves nothing about
whether the check works at all; firing only on synthetic data proves nothing about
whether it will misfire on something real.
