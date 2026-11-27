# App-level rules a paywall or onboarding runs into

A paywall can be clean and the build still rejected, or the app removed, for what the app around
it does. These rows are the ones a subscription app's onboarding and paywall touch. Like the store
rows they are checked against what you can see; most need one answer from the user, so put them
to the user with the other questions, **only the rows the app's screens or answers make relevant**.

Severity: a **blocker** for these rows when the screens, the code or the user's answer shows the
gap: only the data the app needs is required, account deletion, an equal private sign-in, consent
before data goes to an AI provider, and moderation of AI output and user content. Every other row
is a **risk** when you see the shape, and a **question** while you need the user's answer. Store findings go in the store sections of the report.

## What the onboarding asks for

| Rule | Look for | Fix | Guideline |
|---|---|---|---|
| **Only the data the app needs is required** | an onboarding step that cannot be skipped and asks for a phone number, date of birth, gender, address or other personal details the app's core feature does not use | Make the field optional, or explain on the screen what the app uses it for | App Store 5.1.1(v): "Apps may not require users to enter personal information to function, except when directly relevant to the core functionality" |
| **A sign-up the app does not need is optional** | creating an account is the only way past an onboarding screen, and the app has no account-based features (the sign-up wall row in `screens-and-code.md`) | "Continue without an account" | App Store 5.1.1(v) |
| **An account can be deleted in the app** | the onboarding creates an account; ask whether the app has an in-app "Delete account". A mail link, a web form or a "deactivate" is not enough | An in-app delete that removes the account and its data | App Store 5.1.1(v); Google Play's [account deletion requirement](https://support.google.com/googleplay/android-developer/answer/13327111) |
| **Social sign-in has an equal private option** | Google, Facebook or another social login with no Sign in with Apple or an equivalent that limits data to name and email and allows a hidden email | Add Sign in with Apple, at least as prominent as the others | App Store 4.8 |
| **Sign in with Apple is not undone** | after Sign in with Apple, the onboarding asks for the name or email again, or refuses a private-relay email | Use the name and email Apple returns; accept the relay address | App Store 4.0, Sign in with Apple |
| **The reviewer can get past the sign-in** | a sign-in wall before the paywall or the main features | Put a working demo account in App Store Connect's review notes | App Store 2.1 |

## AI, chat and user content

The questions to ask when the app's screens or listing show an AI assistant, a character or
companion chat, generated images, user posts or chat between people.

| Rule | Look for | Fix | Guideline |
|---|---|---|---|
| **Consent before personal data goes to an AI provider** | the app sends what people type, say or upload to a third-party AI (an onboarding that "analyzes" answers with a model, a chat with an LLM), and no screen names the provider and asks first | A consent screen before the first send that names the provider and the data, with a real choice | App Store 5.1.2(i): "clearly disclose where personal data will be shared with third parties, including with third-party AI, and obtain explicit permission" |
| **AI output and user content are moderated** | generated text or images, or content from other users, with no way to report it, block a user, or filter what is shown | Filtering, a report button, blocking, and published contact information | App Store 1.2 (it names AI content creation apps); Google Play's [AI-Generated Content policy](https://support.google.com/googleplay/android-developer/answer/13985936) |
| **No random or anonymous chat** | the app's core is chatting with strangers at random or anonymously, or rating people's looks | A different core; App Review removes these without notice | App Store 1.2 |
| **The age rating covers what the AI can say** | a companion or character chat that can produce romantic, sexual or self-harm content, and a rating or gate that does not match; a chat feature with "Messaging and chat" answered "No" in the age rating questionnaire | In App Store Connect's age rating questionnaire, declare "Dating and Relationships" for a virtual companion that engages in romantic or sexual content (the app becomes 18+) and "Messaging and chat" for any chat; add an age gate and crisis resources for self-harm topics | App Store 1.2 and 2.3.6, [age ratings](https://developer.apple.com/help/app-store-connect/reference/age-ratings-values-and-definitions/); Google Play AI-Generated Content |
| **Not a thin wrapper** | the app is a chat box over a third-party model with nothing of its own | Features of its own the model does not give | App Store 4.2 |
| **A crowded category needs a difference** | dating, flashlight, sound effects, wallpaper, simple timers, fortune telling, or a near-copy of a popular app | A clearly different or better experience; say what it is in the review notes | App Store 4.3(b) |

## The paywall's own copy

| Rule | Look for | Fix | Guideline |
|---|---|---|---|
| **No other platforms named** | "Also on Android", "Get it on Google Play", another store's badge on an iOS paywall or onboarding | Remove it from the iOS build | App Store 2.3.10 |
| **No features that do not ship yet** | a benefit list with "coming soon", "beta", "in the next update" | List only what the build does | App Store 2.3.1 |
| **Paid random rewards show their odds** | a paid loot box, mystery box or spin | Show the odds of each reward before the purchase | App Store 3.1.1 |

## Changing screens after review

A paywall or onboarding served from a server (an Adapty flow or paywall, a remote config) can
change without a new build. That is ordinary practice, and the changed screen is held to the same
guidelines as the reviewed one: App Store 2.5.2 forbids downloading code that changes the app's
features, 2.5.19 forbids features hidden from review, and a screen that adds a feature, unlocks something hidden or breaks a rule can get the
app removed later. Say this whenever you offer a fix that reaches users without a new build.
