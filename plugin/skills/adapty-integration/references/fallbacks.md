# Fallback file

Read this at the closing review, once the app's placements are live. It covers what a fallback
file is, how to tell the user, how to download it with the CLI, and how to keep it fresh.

## What it is, in the user's words

The app fetches its paywalls and flows from Adapty. When it cannot reach Adapty — no network on
first launch, a captive Wi-Fi, an outage — the SDK has nothing to show, and the paywall is empty.
The fallback file is a snapshot of every placement, bundled into the app, that the SDK shows
instead. The SDK's own cache covers a user who has opened the app before; only the bundled file
covers the first launch.

Say it like this, in the user's language (the shape, not words to copy):

> Before you ship: if someone opens your app for the first time with no internet, the paywall
> will be empty. A fallback file fixes that — it's a copy of your paywalls bundled into the app.
> I can download it and wire it in now. Want me to?

**It needs live placements, and covers only those.** The file holds active placements and
published flows, nothing else. If Phase 3 deferred the placement, or a flow is still a draft,
there is nothing to download yet: put "download the fallback file" in the closing message's
left-to-do list, after the step that makes the placement live, and stop here.

## Download it

```bash
$ADAPTY fallbacks get --app <appId> --platform ios --sdk-version <X.Y.Z> --output <path>/ios_fallback.json
$ADAPTY fallbacks get --app <appId> --platform android --sdk-version <X.Y.Z> --output <path>/android_fallback.json
```

- **One file per store.** Run the `ios` line for an App Store build and the `android` line for a
  Play build. A cross-platform app (Flutter, React Native, Unity, KMP, Capacitor) that ships to
  both needs both files. macOS and visionOS use the `ios` file.
- **`--sdk-version` is the Adapty SDK version you installed in Phase 4** — for a cross-platform
  app, the Adapty plugin or package version, exactly as the lockfile records it. The server picks
  the file format from it, and the SDK rejects a file of any other format at startup. Never pass
  a remembered or rounded version; if you did not install the SDK in this run, read it from the
  lockfile.
- **`<path>` is where the platform's docs page says the file lives** (next section). Read that
  page before choosing it.
- **Always `--output`.** It writes the file only after a complete download, so a failure keeps
  the old file. A plain `> file` truncates first and leaves a partial file on failure.
- The command makes one request and never retries, because the server builds the file on every
  request. Do not loop it.

| Exit | Meaning | What you do |
|---|---|---|
| 0 | File written | Continue |
| 2 | Bad input (app ID, platform, version format) | Fix the flag |
| 3 | No token or access refused | Re-run Phase 3 Step 1 |
| 4 | API error; on a 429 the message says how long to wait | Wait at least that long, then run it once more; otherwise tell the user |
| 5 | Adapty was not reached, or the download broke | Check the network, run once more |
| 1 | The file could not be written | Check the path and permissions |

If `fallbacks get --help` says the command does not exist, try once with
`npx --yes adapty@beta fallbacks get --help` before telling the user the CLI cannot do it. Then
the route is the dashboard download: https://adapty.io/docs/local-fallback-paywalls

## Wire it into the app

Bundling the file and the call that loads it are platform code. Fetch the platform's page before
writing it, with the session marker:

| Platform | Page |
|---|---|
| iOS | https://adapty.io/docs/ios-use-fallback-paywalls.md |
| Android | https://adapty.io/docs/android-use-fallback-paywalls.md |
| Flutter | https://adapty.io/docs/flutter-use-fallback-paywalls.md |
| React Native | https://adapty.io/docs/react-native-use-fallback-paywalls.md (Expo and pure React Native each have their own page, linked from it) |
| Unity | https://adapty.io/docs/unity-use-fallback-paywalls.md |
| KMP | https://adapty.io/docs/kmp-use-fallback-paywalls.md |
| Capacitor | https://adapty.io/docs/capacitor-use-fallback-paywalls.md |

The checkpoint: build, then launch with networking off on a fresh install. The paywall shows
instead of an empty screen. That is the user's check to run; ask for it in one line.

## Keep it fresh

The file is a snapshot. It goes stale when:

- **A placement changes** — a new paywall or flow, a new audience, edited copy. Users offline on
  first launch see the old version.
- **The Adapty SDK is upgraded to a version with a different file format.** The old file is
  rejected at startup with no build error, so every placement silently loses its fallback.

So offer the user one of two things, and say which you did:

1. **A manual step** (the default): give the user both download lines with the real app ID and SDK
   version filled in, and tell them to run them before each release build and commit the result.
   Put the lines in the closing message's left-to-do list, or in `ADAPTY_SETUP.md` if you wrote one.
2. **A CI step**, only if the user asks for one or already runs release builds in CI. Run the same
   two commands before the build, with the `--sdk-version` read from the lockfile in the job so an
   SDK upgrade cannot leave it behind. Tell the user plainly what the job authenticates with before
   they set it up:
   - There is no CI token yet. The job uses the personal token that `adapty auth login` stores in
     `~/.config/adapty/config.json`, set as an `ADAPTY_TOKEN` secret. The CLI reads that variable
     instead of a login.
   - **The token lasts 90 days, so the user has to replace the secret by hand before then.** Suggest
     a calendar reminder. When it expires, or after `adapty auth revoke`, the job fails with exit
     code 3, and the fix is a fresh `adapty auth login` and an updated secret.
   - That token can do everything its owner can in the dashboard, not just download this file.
     Suggest logging in with a shared account the team controls rather than someone's own.
   - The user copies the token into the secret themselves, with a command that never prints it.
     For GitHub Actions:

     ```bash
     jq -r '.access_token' ~/.config/adapty/config.json | gh secret set ADAPTY_TOKEN
     ```

     For another CI, give its own way to set a secret from standard input. Never run it yourself,
     and never print, paste or commit the token.
