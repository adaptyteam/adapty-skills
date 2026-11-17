# Passing custom tags from the app's code

`SKILL.md` phase 5 offers this in the closing callout. Read it on the user's yes.

## Writing the code that passes a custom tag

**A custom tag is not done until the app passes it, so offer the code, and on a yes write it.**
The offer is the callout line above. List the tags off the bytes you wrote, never from memory —
`jq -r '.variables[]? | select(.external == true)'`. On a yes:

1. **Find the app's code.** Usually it is the workspace you are in; if no app project is
   reachable, ask for its path rather than guess one.
2. **Find the call site that creates the flow view.** Search for the flow-view creation call; if
   there are several, match the one that fetches this flow's placement, and ask when you cannot
   tell. None at all — or an SDK below 4.x, which has no flow API — means the app does not render
   flows yet: that is SDK integration, so offer `adapty-integration` instead of building it here.
3. **Find where the app already holds each value** — the user model, the wallet, the store. Ask
   when you cannot find one; never pass a sample value, a placeholder or the fallback itself.
4. **Look up the exact parameter** for the platform in [flow-schema.md → trap 25](flow-schema.md#25-a-value-only-the-app-knows-is-a-custom-tag--shown-in-text-never-read-by-logic)
   — its docs page, or the SDK source at the app's release tag when the page does not show it —
   then pass the values at that call: keys exactly the tag names, values strings formatted for
   display, read right before the view is created. A phrase the app passes needs a version in
   every locale the flow ships; where one is missing, pass nothing — the fallback — never another
   language's words.
5. **Build if the project lets you,** and show the diff in one line per file.

Keep the change to that call site and what it needs — a helper beside it, the strings it reads.
The app's models and every other screen are not this skill's to edit.
