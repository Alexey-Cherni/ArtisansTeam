# Status: {title}

**Run:** `{trackingDir}/runs/{run_id}/`
**Started:** {YYYY-MM-DD HH:MM}
**Closed:** —
**Host:** {Claude Code | VS Code Copilot | Copilot CLI}
**Branch:** {branch} · **Baseline:** commit `{short sha}`; pre-existing uncommitted files: {none | list}
**Language:** {language of the task}
**Result:** {IN PROGRESS | DONE | REJECTED | STOPPED | FAILED}

## Task (user's words)

{verbatim}

## Team (approved at kickoff, may change at the plan gate)

| Role | Involved | Model | Approved at |
|------|----------|-------|-------------|
| Researcher | {yes/no} | {model} | {kickoff} |
| Architect | {yes/no} | {model} | {kickoff} |
| Developer | {yes/no} | {model} | {kickoff / plan gate} |
| Code Reviewer | {yes/no} | {model} | |
| QA | {yes/no} | {model} | |
| Security | {yes/no} | {model} | |

## Phases

- [ ] 0 Preflight (branch: {ok | user switched | user chose to stay}; user actions: {none | list})
- [ ] 1 Kickoff gate (team + models approved)
- [ ] 2 Research ({done | skipped — reason})
- [ ] 3 Architecture ({done | not needed — reason | skipped — not selected})
- [ ] 4 Plan gate ({approved | approved with changes | split into N subtasks | rejected})
- [ ] 5 Development (rounds: {N})
- [ ] 6 Code review (rounds: {N}; verdict: {APPROVED | CHANGES_REQUESTED})
- [ ] 7 QA (tests added: {N}; run: {pass/fail counts}; rounds: {N})
- [ ] 8 Test review (rounds: {N}; verdict)
- [ ] 9 Security review (rounds: {N}; verdict: {APPROVED | BLOCKED}; findings: {C/H/M/L})
- [ ] 10 Report ({path})

## Subtasks (only when the plan was split)

| # | Subtask | Status | Notes |
|---|---------|--------|-------|

## Timeline

<!-- One line per event: time — actor — event. Feeds the report's timeline. -->
- {HH:MM} — orchestrator — run created

## Decisions log

- {YYYY-MM-DD HH:MM} — {decision} — {who decided: user | orchestrator | role}

## Needs from user

<!-- Everything the team asked the user to do, and whether it is done. -->
- {none}

## Verify by hand

<!-- Checks the team could not run (needs a device, a deployed env, credentials...). -->
- {none}

## Process notes

<!-- Deviations from the skill, loop limits hit, roles that failed. -->
- {none}
