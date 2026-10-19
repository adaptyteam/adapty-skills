# Maintainer notes: `purchase-testing`

Evidence and history behind the rules in `CLAUDE.md`: measurements, test rounds, dated findings. Not loaded into sessions. Read the part you need before changing a rule; add new findings here, never to `CLAUDE.md`.

## Files

- `plugin/skills/purchase-testing/SKILL.md` — the testing skill's entry point. Four phases (preflight → run → verify → diagnose) plus the five-layer table the diagnosis turns on. Its governing rule is **route, don't restate**: it owns sequence, gates and diagnosis, and hands every store-console procedure to the doc that maintains it. Every preflight check is grounded in the CLI's own shipped typings — `PlacementSummaryDTO.is_active`, `FlowStatus` (`draft`/`dirty`/`published`), `PlacementDetailDTO.audiences[].content_type`, `ProductDTO.access_level_id` — not in prose about what the CLI probably returns.
- `plugin/skills/purchase-testing/references/{app-store,google-play}.md` — split by **store**, not platform, because the content always was: five of the seven platform references used to fan out to the same two files. App Store owns the StoreKit-file-versus-sandbox choice (the local loop never reaches the Adapty dashboard, which reads as a broken integration) and the device/account traps; Google Play owns the AAB-before-products ordering gate and the three silent purchase gates.
