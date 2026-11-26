# Consumer law on paywalls and onboarding

Store review is one gate; consumer-protection law is another, and passing review does not
clear it. These rules are what regulators in the US, the UK and the EU act on when a
subscription is sold. Go through **every row** against the screens, whatever the path: a flow
through `store-check.py --screens`, screenshots, or the app's code.

**Every finding here is a risk or a question, never a blocker,** and it goes in the report's
"Consumer law" section, apart from the store findings. Say "regulators have acted on this", never
"this is illegal": whether a law applies depends on where the app sells, who bills, and facts a
screen does not show. The report carries the line "This is not legal advice."

**Ask where the app sells** (the US, the UK, the EU, elsewhere) once, with the other questions.
Never infer it from the currency or the language. Until the user answers, cite the rule in "if you
sell in …" form.

**Who bills changes what applies.** On an App Store or Google Play purchase, the store's purchase
sheet shows the price and the renewal, and the store runs cancellation. The paywall's own words,
layout and claims are still the app's, so the disclosure, claim, consent and pressure rows apply
either way. The cancellation rows apply only where the app bills people itself (a web checkout,
its own account page). Both can be true: an app billed by the stores that also links to its own
web store bills those web buyers itself.

A row whose "not a finding" condition holds is not reported. A row you could not see goes under
"Tell me, and I can check", never under a pass.

## Disclosure

| Rule | Look for | Not a finding when | Fix | Law |
|---|---|---|---|---|
| **The renewal is as visible as the offer** | that it renews automatically is said nowhere on the screen; or the recurring price, how often it is charged, or the renewal sits in the footnote, in faint or tiny text, below the fold, or only after the purchase button, while the offer (a trial, a discount, a per-day figure) is large | the price, period and "renews automatically" are next to the purchase button in readable text before anyone taps it | Put "Renews at $59.99/year until you cancel" right above or under the button, in body-size text | US: ROSCA, 15 U.S.C. 8403(1); FTC Act s.5. EU: Consumer Rights Directive Arts. 6 and 8(2). UK: DMCC Act 2024 s.227 (misleading omissions) |
| **A "free" trial says what happens next** | "Free", "Try free", "$0 today" with no date or amount of the first charge | the screen says how long the trial lasts and what is charged after it, next to the offer | "Free for 7 days, then $59.99/year. Cancel before [day] and you pay nothing" | US: ROSCA 8403(1); FTC Act s.5. EU: CRD Art. 6 |
| **The price is not framed as smaller than it is** | the only large price is per day or per week, or the offer reads as a one-time payment ("$9.99 today", "one payment") for something that renews | the billed amount and its period are shown with equal or more weight (the store rule on the billed amount covers the same ground) | Show the billed amount first; keep the per-day figure smaller beside it | US: ROSCA 8403(1); FTC Act s.5. EU: Unfair Commercial Practices Directive Arts. 6–7 |
| **"Free" means free** | "100% free", "free app", "no payment needed" on a screen that leads to a paywall nobody can pass without paying | the app has a free tier people can reach, or "free" only describes the trial | Drop the word, or say what is free ("Free for 7 days") | US: FTC Act s.5. EU: UCPD Annex I point 20. UK: DMCC Act Sch. 20 para. 23 |
| **A personal result is really personal** | a loader that says "Analyzing your answers", "Building your plan", a "Your personal plan is ready" screen, or a chart that predicts the person's progress after a quiz | the result changes with the answers (a different plan, schedule or number per answer) — ask; the screen cannot show it | Make the result come from the answers, or word it as an example ("People like you often…") | US: FTC Act s.5. EU: UCPD Art. 6. UK: DMCC Act s.226 |
| **Outcome and health claims can be backed** | "Lose 10 kg in 4 weeks", "Sleep better in 3 nights", "Clinically proven", "Recommended by doctors", a named university or media logo | the user can point to the study, the endorsement or the data behind it — ask | Remove the number or the claim, or name its source on the screen | US: FTC Act s.5 and s.12. EU: UCPD Art. 6. UK: DMCC Act s.226 |

## Consent

| Rule | Look for | Not a finding when | Fix | Law |
|---|---|---|---|---|
| **No paid extra is switched on for the user** | a toggle or checkbox already on that adds a second subscription, an add-on or an upgrade | it is off until the person turns it on | Leave every paid extra off by default | EU: CRD Art. 22. UK: Consumer Contracts Regulations reg. 40. US: ROSCA 8403(2) |
| **The purchase button says it buys** | the button that starts a subscription reads "Continue", "Next" or "Get started", on any paywall, one screen or many | the button or a line touching it says it subscribes or starts a paid trial | "Start free trial", "Subscribe for $59.99/year" | US: ROSCA 8403(2). EU: CRD Art. 8(2) ("order with obligation to pay"). Google Play's rule in `screens-and-code.md` is the same shape |

## Pressure

| Rule | Look for | Not a finding when | Fix | Law |
|---|---|---|---|---|
| **A countdown ends something real** | a countdown on an offer, a "price reserved for 10:00", a promo code that expires, "this price disappears when you leave" | the offer really ends when the timer reaches zero and does not start over for the same person. **A question**: a timer itself is fine, and a screen cannot show what happens at zero. **A risk** only when the flow or the code shows the countdown starting over every time the screen appears (`--screens` says so) | Tie the timer to a real end of the offer, or remove it | US: FTC Act s.5. EU: UCPD Annex I point 7. UK: DMCC Act Sch. 20 para. 7 |
| **Declining is not shamed** | the decline or close text makes the person insult themselves: "No, I don't want to get fit", "I'll stay stressed" | the decline is neutral: "Not now", "No thanks", "Maybe later" | Word it "Not now" | EU: UCPD Arts. 8–9. UK: DMCC Act s.228. US: FTC Act s.5 |
| **Reviews and numbers are real** | review cards with names and stars, "10M users", "#1 app", "Rated 4.9" | the user confirms the reviews are from real customers and the numbers are current — **a question, never a risk**; never judged by how a badge looks | Use real reviews and numbers, with their source | US: FTC Rule on Consumer Reviews and Testimonials, 16 CFR Part 465. EU: UCPD Annex I point 23b. UK: DMCC Act Sch. 20 para. 13 |
| **A wheel or a gift is not staged** | a spin-to-win or scratch card that always lands on the same discount, a "gift" that is the normal trial | the outcome is really random, or the screen says what everyone gets. **A question**; **a risk** when the flow or the code shows one fixed result | Show the discount as it is: "50% off your first year" | US: FTC Act s.5. EU: UCPD Annex I point 31 |

## Leaving and cancelling

| Rule | Look for | Not a finding when | Fix | Law |
|---|---|---|---|---|
| **Saying no is as easy as saying yes** | a close button that appears only after several seconds, a close that opens another offer, a "No" that is much fainter or harder to reach than "Yes". The store rows on a way out and on an exit offer cover the review side | the close is visible from the start and closes | Show the close at once and let it close | US: FTC Act s.5(n) (unfair practices). EU: UCPD Arts. 8–9. UK: DMCC Act s.228 |
| **Cancelling is as easy as signing up** (web billing only) | the app bills on the web and cancelling needs a call, an email, a letter or a chat, or the web account page has no cancel button | billing is through the App Store or Google Play (the store runs cancellation), or the account page cancels in a few taps | A cancel button on the account page, as easy as the sign-up | US: ROSCA 8403(3); California's Automatic Renewal Law, Bus. & Prof. Code 17602, and other states' laws. The FTC's 2024 click-to-cancel rule was vacated in 2025 and is not in force |
| **An EU withdrawal button** (web billing only, EU customers) | the app sells to people in the EU on the web, and there is no clearly labelled "Withdraw from contract" function people can use for the 14-day withdrawal period | billing is through the App Store or Google Play | Add a clearly labelled withdrawal function on the account page, available for the whole withdrawal period | EU: CRD Art. 11a, added by Directive (EU) 2023/2673, from 19 June 2026; each country's own law sets the details |

## Where the law sits

Link these only when the user asks for the text itself:

- [15 U.S.C. 8403 (ROSCA)](https://www.law.cornell.edu/uscode/text/15/8403)
- [16 CFR Part 465 (consumer reviews)](https://www.law.cornell.edu/cfr/text/16/part-465)
- [DMCC Act 2024, Schedule 20](https://www.legislation.gov.uk/ukpga/2024/13/schedule/20)
- [The EU Unfair Commercial Practices Directive](https://commission.europa.eu/law/law-topic/consumer-protection-law/unfair-commercial-practices-law/unfair-commercial-practices-directive_en)

## Credits

The rows above adapt the pattern and norm taxonomy of
[paywall-council](https://github.com/mooreslaws/paywall-council), MIT License,
Copyright (c) 2026 Alexey Vorobey, rewritten for in-app paywalls and onboarding.
