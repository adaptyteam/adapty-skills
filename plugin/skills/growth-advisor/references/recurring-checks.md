# Recurring checks

Open this when you offer, set up or run a check that repeats: the app's health every week, an A/B
test set up from a hypothesis, or every A/B test running in the app. A recurring check is a task
the user's agent runs on a schedule, with one of the prompts below as its instructions. Each run
starts with no memory of this conversation, so the prompt carries everything the run needs.

## Offering one

Offer it as the last "Me:" item, once per conversation, after these replies:

| After | Offer | Template |
|---|---|---|
| A health check | "Me: run this check every Monday morning and send you the result. Want me to?" | The app's health |
| `hypotheses link` of a test that is live, or a start of one through `ab-tests` | "Me: check this A/B test twice a week and tell you when it's ready to decide. Want me to?" | A hypothesis's A/B test |
| "How is my test going?" with tests live and none linked to a hypothesis | "Me: check your running A/B tests every Monday. Want me to?" | Every running A/B test |

The examples show the shape, not words to copy. A user who asks for a check outright ("check my
app every week", "tell me when my test is done", "send me a weekly report") gets it set up without
the offer. They pick the cadence: the defaults are every Monday at 9:00 for health and running
tests, and Monday and Thursday at 9:00 for one test. A monthly health check reads the 28-day
columns.

Before you offer, look for one already set up: if your scheduling tool can list tasks, an
existing task with the same app and template is offered as changed, never doubled.

## Setting one up

On the user's yes:

1. **Ask where the reports go,** in the same message as the cadence, unless they said. The
   default is wherever the scheduler shows a run (its chat or notification). Look at your tools:
   each connector that can post a message or write a page (Slack, email, Teams, Notion, Linear and
   the like) is an option, named with the place it would post to ("your #growth channel in
   Slack"). Holding none, add one line: they can connect one in their agent's connector or MCP
   settings, and the reports go to the default until then. The user names the exact channel,
   address or page; never pick one.
2. **Fill the template.** Replace every `<SLOT>` with a value you read in this conversation: ids
   from the CLI, names as the dashboard shows them. A slot you did not read is read first, never
   guessed. `<DESTINATION>` is "Show the report as your answer." for the default, or "Post the
   report to <the place> with your <connector> tool, then show it as your answer too."
3. **Create the task with your own scheduling tool,** if you hold one (a tool that creates a
   scheduled, recurring or cron task), with the filled prompt as its instructions and the cadence
   the user picked. Name it `Adapty: health for <APP NAME>`, `Adapty: tests for <APP NAME>`, or
   `Adapty: test <TEST NAME> for <APP NAME>`.
   - It runs on this computer: it uses this computer's Adapty sign-in and connectors.
   - It runs on another machine or in the cloud: the run needs `ADAPTY_TOKEN` set in that
     environment, and the connector connected there. Tell the user to set the token there from
     their Adapty account; never put a token in the prompt.
4. **No scheduling tool:** give the user the filled prompt, to save as a file, and their
   scheduler's line. A cron line runs the agent in its non-interactive mode (`claude -p`, `codex
   exec`, `gemini -p`, `copilot -p`) from this folder, allowed to run shell commands without
   asking, and appends the report to a file the user picks. Example of the shape for Claude Code,
   not a line to copy:

   ```bash
   0 9 * * 1 cd ~/my-app && claude -p "$(cat adapty-weekly-health.txt)" --allowedTools "Bash" >> ~/adapty-checks.md
   ```

   Say in one line that the flag that lets the run use the shell differs per agent and is in its
   docs.
5. **Send the feedback note** (SKILL.md, "Feedback note"), type `check`: which check, how often,
   and whether a scheduling tool, cron or a connector carries it, never where it posts.

Then reply in one line: what runs, when, and where the result shows up. A check on one A/B test
ends itself: its prompt says how.

## Templates

Each block is the task's whole prompt. Keep its wording; change only the slots. The last
paragraph is the same in all three.

### The app's health

```text
Use the growth-advisor skill, "Recurring checks". This run starts with nobody watching.

Run a health check of the Adapty app "<APP NAME>" (app id <APP_ID>) over the last <7 or 28> days,
as the skill's "A health check" describes, then read the backlog
(reads.py backlog for placements <PLACEMENT_IDS>) for anything due.

Report in the health check's shape: the bold verdict, the table, each other signal in one
sentence. Add "Due in your backlog:" with one line per due item, if any. End with Next steps:
each thing I can do for the user as a question they can answer yes to ("Find why Google Play
revenue fell?"), each thing only they can do starting "You:".
<DESTINATION>

Until the user answers, run only reads. When they answer, act on it as growth-advisor does in any
chat, with every confirmation it asks for.
```

### A hypothesis's A/B test

```text
Use the growth-advisor skill, "Recurring checks". This run starts with nobody watching.

Check the <flow or paywall> A/B test "<TEST NAME>" (id <TEST_ID>) in the Adapty app "<APP NAME>"
(app id <APP_ID>). It tests the hypothesis "<HYPOTHESIS TITLE>" (id <HYPOTHESIS_ID>), judged on
<METRIC>, planned to run until about <END DATE>.
When this check was set up, the test was live on placement "<PLACEMENT NAME>" (id
<PLACEMENT_ID>), audience "<AUDIENCE NAME>", with arms <ARM A NAME> and <ARM B NAME> at <WEIGHTS>.

Read: ab-tests get, ab-tests metrics total, hypotheses get, hypotheses by-ab-test, placements get.

Report, in this order:
1. One bold line: "Not ready yet", "Ready to decide", or "Something changed".
2. What changed since this check was set up, one line each: the test's state, an arm or weight,
   the placement or audience, the hypothesis no longer linked. Nothing changed: say so.
3. Each arm's purchases against about 200, and whether a leader has settled by the ab-tests
   skill's "Results and the leader". Name no leader that has not settled.
4. Next steps, as questions the user can answer yes to: when ready to decide, "Stop the test and
   keep <the leader>?"; a lost link, "Link the test that replaced it?"; a test stopped without a
   result, "Mark the hypothesis won, lost or inconclusive?".
When the test is no longer live and the hypothesis is resolved, end with: "This check has nothing
left to do: delete the scheduled task 'Adapty: test <TEST NAME> for <APP NAME>'."
<DESTINATION>

Until the user answers, run only reads. When they answer, act on it as growth-advisor does in any
chat, with every confirmation it asks for.
```

### Every running A/B test

```text
Use the growth-advisor skill, "Recurring checks". This run starts with nobody watching.

List the live A/B tests of the Adapty app "<APP NAME>" (app id <APP_ID>): ab-tests list --state
live, once with --type flow and once with --type paywall. For each, read ab-tests metrics total and
hypotheses by-ab-test.

Report one block per test, the ones ready to decide first: its name and placement, days run,
each arm's purchases against about 200, and whether a leader has settled by the ab-tests skill's
"Results and the leader". Name no leader that has not settled. No live test: say so in one line.
End with Next steps: for each test ready to decide, "Stop <name> and keep <the leader>?".
<DESTINATION>

Until the user answers, run only reads. When they answer, act on it as growth-advisor does in any
chat, with every confirmation it asks for.
```

## Running one

A run that starts from one of these prompts follows its prompt over the rest of this skill.

- **Before the user answers,** it runs reads only, sends no feedback note, suggests no new
  hypothesis and offers no recurring check. A read that fails is one line in the report naming
  the data it lacks; the run never retries in a loop. A sign-in the run cannot use (`adapty auth
  whoami` shows no account and no Adapty tools answer) is the whole report: "I couldn't reach your
  Adapty account; sign in again on this computer, or set ADAPTY_TOKEN where the check runs."
- **A report posted through a connector** cannot be answered there. Its last line says where to
  answer: "To act on this, reply in <the scheduler's place for this task>, or paste this report
  into a chat with your agent." (the shape, not words to copy).
- **Once the user answers,** in the run's own chat or with the report pasted into a new one, they
  are here: act on their answer as in any conversation. Every write keeps its own confirmation: a
  stop goes through the `ab-tests` card, a hypothesis is resolved, linked or dismissed only on
  their word. Read the test and placement again first; the report may be days old. Send one
  feedback note, type `check`, for what they acted on.
