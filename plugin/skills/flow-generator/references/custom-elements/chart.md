# Template: a chart of the user's data

Rules, shape and the reply: [custom-elements.md](../custom-elements.md). This file holds only what
is particular to a chart.

**Fits** a chart drawn from the user's own numbers: a projected weight, savings over time, sleep
by night, progress to a goal. The user can drag along it or tap a point to read a value.

**Does not fit** an illustrative curve that is the same for everyone: a picture, as an `image`
([media.md](../media.md) draws one when there is no file).

## Where the numbers come from

The flow cannot hand the chart its data. The usual case is an onboarding that asks for the
numbers and a paywall that shows the chart; then:

1. The **onboarding flow** asks with inputs (a `number-input` per value, format `integer` so the
   app reads the same digits in every locale), each with a `customId` the app reads.
2. The **app** collects the answers from the flow's events, works out the series, and holds it.
3. The **paywall** is a separate flow with the chart, and the app hands its view the series.

When the inputs are in the same flow as the chart, the app still has to read them from the flow's
events before the chart's screen opens: say so, because the chart then shows the fallback for a
user whose answers have not arrived. Two flows, onboarding then paywall, is the reliable shape.

## The box

| Field | Value |
| :--- | :--- |
| Type | `line_chart`, `bar_chart`, or one Type per kind of chart the app draws |
| ID | the series, such as `weight_goal` |
| Height | fixed, never `hug`; 200–260 pt |
| Width | `fill` |

```python
fk.custom_element('line_chart', 'weight_goal', fixed_h=240,
                  fallback=[fk.image(fk.PLACEHOLDER, fixed_h=240, fit='fit')])
```

**Fallback:** a sample chart of the same kind, as an `image`. The number that matters (the goal
weight, the date it is reached) goes in text **outside** the box as a custom tag, so it reaches
users who see the fallback too.

**Placement:** never inside a `carousel` when the user drags along the chart.

## What the app's view does

- Draws the chart with the app's chart library (Swift Charts on iOS) from the series the app
  holds.
- Answers a drag or a tap by marking the point and showing its value.
- Draws nothing when the series is missing, so the fallback shows.
- Dragging along a Swift Charts chart needs iOS 17; on iOS 16 the line still draws.

Docs: https://adapty.io/docs/custom-element-interactive-chart.md

## On the device

Finish the onboarding with real values and check the line starts and ends where they say; drag
along it and read a few weeks.
