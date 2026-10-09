# Adapty Skills

[![skills.sh](https://skills.sh/b/adaptyteam/adapty-skills)](https://skills.sh/adaptyteam/adapty-skills)

Skills that hand your app's subscription surface to the agent you already have open: integrate the Adapty SDK on any mobile platform, get the first sandbox purchase through, build and audit Flow Builder paywalls and onboardings, move paywall placements to flows, plan revenue tests from your own numbers, run Apple Search Ads, read which campaigns pay back in Adapty Attribution, and answer questions from Adapty's docs.

**Everything about using them — what each skill does, what you can ask, what runs on your machine — is in the [plugin README](plugin/README.md).**

## Install

**Claude Code**

```bash
claude plugin marketplace add adaptyteam/adapty-skills
claude plugin install adapty-skills@adapty
```

**Codex**

```bash
codex plugin marketplace add adaptyteam/adapty-skills
codex plugin add adapty-skills@adapty
```

**Any agentic CLI**, through the [skills CLI](https://skills.sh):

```bash
npx skills add adaptyteam/adapty-skills --all
```

Other routes, including copying the skill directories by hand, are in the [plugin README](plugin/README.md#install).

## What is where

| Path | What it is |
| --- | --- |
| `plugin/` | The plugin users install: manifests for Claude Code and Codex, the skills, the logo, its README |
| `.claude-plugin/marketplace.json` | The marketplace that `marketplace add` reads |
| `scripts/`, `tests/`, `docs/`, `.github/` | Lints, test fixtures and maintainer notes. They do not ship |

## License and security

[MIT](LICENSE). Report a vulnerability privately as [SECURITY.md](SECURITY.md) describes.
