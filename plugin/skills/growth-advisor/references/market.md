# Market medians

Where the typical subscription app sits, from Adapty's State of Paywalls 2026: 78,000+ paywalls
from 30,000+ apps, App Store only, October 2025 to September 2026. Revenue is in USD after
refunds and before store fees; European prices include VAT. Most numbers are medians, computed
app by app so the largest apps do not skew them.

This file owns market medians and how often each kind of test wins. `evidence.md` owns the uplift
ranges from winning tests. When you use a number from here, name it as the market median from
Adapty's State of Paywalls 2026. Never call it the user's category average unless the row is for
their category, and never present a median as their target.

## Read this before comparing

- **Paywall view → paid is not install → paid.** The report counts conversion from paywall
  views. The CLI gives installs and purchases, not paywall views, so the app's install → paid can
  never be set against these rows. Compare only a paywall conversion the user reads from the
  dashboard.
- **Trial → paid is comparable, roughly.** The CLI's trial → paid (see `diagnosis.md`) is a
  same-period approximation; say so when you set it against the median.
- **Prices compare directly**, per plan length, in USD, for the same region.
- **The median is not the goal.** The top 10% convert 4-5× the median outside the US. Being at
  the median says the app is typical, not that it is done.
- **App Store only.** For a Google Play question, say there is no market median here.

## Conversion

| Measure | Median | Notes |
|---|---|---|
| Paywall view → paid, US | 2.75% | Within 30 days |
| Paywall view → paid, Europe | 1.38% | About half the US |
| Top 10% start at | 3.30% (MEA) to 5.71% (Europe) | Above the typical US app in every region |
| Trial → paid, US | 26.2% | |
| Trial → paid, MEA | 15.1% | |
| Trial → paid, Health & Fitness | 19.8% (MEA) to 33.3% (US) | Highest of any category in every region |
| Paywall view → trial start, Health & Fitness | 1.46% (LATAM, MEA) to 2.93% (Europe) | Lowest category outside the US |

US paywall view → paid by category: Graphics & Design 3.50%, Education 3.28%, Lifestyle 3.20%,
Health & Fitness 2.86%, Entertainment 2.44%. Category ranks change by region; a US ranking does
not carry over.

## Prices and plans

| Measure | Median |
|---|---|
| Typical price, US | $6.99 a week, $9.99 a month, $39.99 a year |
| Europe | $8.06 a week, $11.55 a month, $40.88 a year (the most expensive region) |
| LATAM, annual | $30.11 a year; weekly stays close to $6.99 everywhere |
| Health & Fitness | $5.33 a week, $29.99 a year (the cheapest category) |
| Lifetime | About 1.3× the annual price; 14% of apps offer it, and it brings 5.6% of revenue where sold |

- **Revenue by plan length:** weekly 62%, annual 21%, monthly 12% overall. Weekly is 76% in LATAM
  and 50% in Europe. Health & Fitness gets 62% from annual; Utilities 90% from weekly. Judge an
  app's mix against its category, not the overall split.
- **Number of plan lengths:** 41% of apps offer one, 39% two, 20% three or more. Apps with two
  lengths convert 67% higher than apps with one. In A/B tests, adding products won only 53% of
  the time.
- **Preselection:** 90% of buyers keep weekly when it is preselected, 46% keep annual.
  Preselecting annual does not hurt conversion.

## Trials

- 79% of trial starts are 1-3 days; 20% are 4-7 days.
- 32% of trials are cancelled within the first hour, 44% within 24 hours (55% in Europe, 40% in
  the US). Fewer early cancellations go with higher trial → paid.
- Longer trials get fewer day-one cancellations, but convert better only on monthly and annual
  plans. On weekly plans, 3-day trials do better.

## Discounts

Six-month revenue per subscriber, against full price:

| Discount on the first payment | Revenue kept |
|---|---|
| Up to 30% off | 90% |
| 31-60% off | 70% |
| Over 60% off | 46% |

Offers work far better for win-back: 56% of returning subscribers who take an offer still pay
three months later, against about 1 in 10 new users who start with one.

## Timing and placements

- 93% of first purchases happen within 24 hours of install, bringing 89% of first-90-day revenue.
- 60% of buyers purchase on the first paywall view, 15% on the second.
- Onboarding paywalls convert 0.85% of views against 0.23% for later paywalls: about $170 per
  1,000 views against $40.
- 7 in 10 paywall views happen after the first session, and subscriptions started there bring
  38% of revenue (48% in Lifestyle and Utilities, 47% of monthly revenue).
- Only 4% of apps show a second paywall right after the first is closed. Those convert at 0.88×
  the main paywall and beat it in 45% of apps. The typical discount there is 38%.
- 80% of apps use two or more paywalls; 44% use five or more.

## Testing

Share of A/B tests that increased each metric:

| Kind of change | Raised LTV | Raised conversion |
|---|---|---|
| Localization | 62% | |
| Trial | 60% | |
| Plan length | 59% | |
| Price | 46% | 28% |
| Visual or copy | 35% | 31% |

- Change the offer before the look: localization, trials and plan lengths win more often than
  visual changes.
- Price tests trade conversion for value, which is why they are judged on revenue per user.
- The most active apps test often: among apps with 50K-500K monthly paywall views, the top
  quarter run 9+ tests a year; above 500K, 21+.
- Only 1 in 4 apps personalize paywalls by audience. Most who do split by country or language
  (61%), app version (44%) or platform (43%); 15% use their own user attributes and 6% the
  acquisition source.

## How paywalls look

From 100 main paywalls of well-known iOS subscription apps. These say what is common, not what
converts.

- 62% show two plans; 73% use plan cards; 67% preselect annual.
- 66% offer a free trial, and 83% of those name it in the button.
- 54% use no image; 27% show social proof; 48% use a feature checklist.
- 62% show the full annual price, 24% a monthly breakdown, 4% a weekly one. 41% use a "Save X%"
  badge, 16% a crossed-out price.
- 2% of headlines use what the app knows about the user.
