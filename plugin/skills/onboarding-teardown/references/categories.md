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

**Usual length** is the middle half of the top 50 US apps in the category, by steps in their
recorded onboarding, with the median in brackets and the usual number of quiz questions. **Most
apps** is the median app's screen count. Both are from Adapty's
[State of Onboarding 2026](https://adapty.io/state-of-onboarding/report/); the top apps are the
target, the median app is what the user's competitors usually ship.

| Category | Usual length | Most apps | Opens with | Why |
| :-- | :-- | :-- | :-- | :-- |
| **Health & Fitness** | 11–26 steps (19), 7 questions | 12 | An easy choice: the goal, or an age range | The flow builds the feeling of a plan made for you before the price |
| **Mental health, wellness, sleep** | As Health & Fitness | — | A goal or a first-person "how do you feel" question | Same job, softer pace |
| **Education, language learning** | 11–18 steps (13), 5 questions; a level check is common | 9 | The goal or the current level | Explains the method and the pace before asking for money |
| **Lifestyle** | 7–15 steps (10), 2 questions | 8 | The goal or the user's situation | A plan or a result for this user; shows the price per week or day more than any category |
| **Entertainment** | 4–8 steps (6), no quiz | 8 | The content itself | Users decide on the first day; earns the most per onboarding open of any category |
| **Photo & video, AI photo** | 5–9 steps (7), no quiz | 5 | The output: what you will make | The user already knows what they want to see; a long quiz cut purchases in half when tested against a short one |
| **Productivity** | 6–9 steps (8), no quiz | 4 | A UI preview of the main job | Rational buyers; static screens, no ceremony |
| **Utilities, scanners, cleaners** | 4–8 steps (5), no quiz | 4 | The capability, working | Monetization is contextual; the paywall that converts is often the one at a limit |

Length costs finishers and earns money, both at once: 90% of opens finish a flow of 1–5 screens
against 63% for 21+, while the 21+ flows earn about four times as much per open and their trials
convert better. That comes mostly from Health & Fitness and Education, so it says what length
suits a category, not that adding screens pays.

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
