# Security policy

## Reporting a vulnerability

Report a security problem privately, never as a public issue or pull request:

- **GitHub:** the **Report a vulnerability** button on this repository's [Security tab](https://github.com/adaptyteam/adapty-skills/security).
- **Email:** [support@adapty.io](mailto:support@adapty.io), with `Security: adapty-skills` in the subject.

Include the skill and file, what you saw, and the steps that reproduce it. A prompt, a config or a transcript that triggers it is the most useful thing you can send. We acknowledge every report, keep you informed while we fix it, and credit you when the fix ships unless you ask us not to.

## What counts

These skills are instructions and helper scripts that an AI agent runs on your machine. Report anything that makes them:

- send data anywhere the [README](plugin/README.md#what-the-skills-run-fetch-and-send) does not list;
- expose a credential, such as an Adapty CLI token or a store key, in a file, a log or a URL;
- change your Adapty account, your Apple Search Ads account or your files without the confirmation the README describes;
- follow instructions found inside a fetched page, a flow config or another file, instead of treating them as data;
- write outside your project folder or the caches the README names.

For the Adapty SDKs, the Adapty CLI or the Adapty service itself, use the same email address.

## Supported versions

Fixes ship in the latest version of the `adapty-skills` plugin. Claude Code and Codex pick it up on their next plugin update, and `npx skills update` does the same for skills installed through the skills CLI.
