# Category shapes

What an onboarding in each category usually looks like: how long it runs, what it opens with,
and which screens fill the length. Read it in Design before choosing the skeleton, and in an
audit when the flow's length looks wrong for its category. The pattern library
([patterns.md](patterns.md)) says *which* patterns work; this file says *how much* and *in what
mix*.

## Length by category

Length follows the job the onboarding does. Where the user already knows what they want, every
extra question costs; where the app has to make someone feel understood before they pay, a short
flow skips that job.

| Category | Usual length | Opens with | Why |
| :-- | :-- | :-- | :-- |
| **Health & Fitness** | 20–50 screens; the longest pass 70 | An easy choice: the goal, or an age range | The flow builds the feeling of a plan made for you before the price |
| **Mental health, wellness, sleep** | 20–50 screens | A goal or a first-person "how do you feel" question | Same job, softer pace |
| **Education, language learning** | Long and quiz-style; a level check is common | The goal or the current level | Explains the method and the pace before asking for money |
| **Photo & video, AI photo** | 5–15 screens | The output: what you will make | The user already knows what they want to see; a long quiz cut purchases in half when tested against a short one |
| **Utilities, scanners, cleaners** | 3–6 screens | The capability, working | Monetization is contextual; the paywall that converts is often the one at a limit |
| **Productivity** | Short, close to utilities | A UI preview of the main job | Rational buyers; static screens, no ceremony |

**Traffic moves it too.** The same app needs a longer flow for cold traffic (paid social) and a
shorter one for high-intent traffic (search, the store page). When you don't know the source,
build for the middle of the range and ask.

**Not knowing whether the app uses the answers rules out a computed plan, not length.** A fitness
flow of six screens is a category mismatch, whatever the reason. Fill the length with the honest
screens below — none of them claims a plan the app may not have — and keep the "your plan" promise
out until the user confirms it.

**A first build may stop at the low end of the range**, never below it. Say what the next screens
would be.

## Screens that fill a long flow honestly

Each one is buildable in Flow Builder and none needs data you don't have.

| Screen | What it does | Builds as |
| :-- | :-- | :-- |
| **Easy opener** | An age range or the goal; a quick first tap raises completion | A single-choice group, big tap targets |
| **Single choice** | One question, one answer | A single-choice group |
| **Select all that apply** | Struggles, interests, equipment | A multi-choice group |
| **First-person statement** | "I start strong, then skip a week." The user agrees or not; it feels personal without asking for a fact | A statement in large type over a 1–5 agree scale, or Yes / No |
| **Agree scale** | Rates a statement from 1 to 5 | A row of five selectables |
| **Number or date** | Height, weight, target, birthday, bedtime | A number, date or time input, in the middle of the flow, never first |
| **Name** | Lets later screens use it | A text input; read back with its value |
| **Reaction** | After every two to four questions: names the last answer and why it matters ("20 minutes is enough when it's consistent") | Text only, or text and one large icon. No statistics you can't source |
| **Method** | How the program or the app works, in three steps or one picture | A step list, a carousel, or a before→after built from shapes |
| **Before → after** | Where the user is and where their goal is, in their own words | Two blocks reading the answers back |
| **Proof** | Rating, reviews, user count | Only with the real numbers and quotes; otherwise leave it out |
| **Commitment** | "I'm ready to train 3 days a week" — holds or taps to commit | A large button or a hold, reading the answers back |
| **Loader** | Only right before a payoff; three labelled steps that name what the user told you | A spinner and a timer; reviews under it only if they are real |
| **Summary** | Every answer read back as the starting point | A card list of the answers |

## Rhythm

A long flow fails when it is the same screen twenty times. Build it to a rhythm:

1. **One question per screen.**
2. **At most three questions in a row**, then a reaction, method or before→after screen.
3. **No two neighbouring screens are the same screen type.** A list of choices, then a statement
   in large type, then a 1–5 scale, then a grid of choices. Variety comes from changing the type,
   never from restyling one: every single-choice question in the flow looks the same.
4. **A flow over ten screens uses at least five different screens from the table above.**
5. **The first screens are the easiest.** Personal data (numbers, name) sits in the middle.
