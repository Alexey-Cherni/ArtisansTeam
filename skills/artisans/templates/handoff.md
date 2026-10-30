<!-- Handoff envelope. The orchestrator fills every field and pastes it as the FIRST block of every subagent prompt. All paths are written from the repository root. Pass paths, not file contents. -->

## Handoff

- run_id: {YYYY-MM-DD}-{slug}
- role: {researcher | architect | developer | reviewer | qa | security}
- mode: {research | design | implement | fix | code-review | test-review | test | security-review}
- round: {1, 2, … — rework round for this role}
- language: {language the user wrote the task in; answer in it}
- run dir: {trackingDir}/runs/{run_id}
- knowledge dir: {trackingDir}/knowledge ({present | missing — explore the repository instead})
- baseline: commit {short sha} on branch {branch}; pre-existing uncommitted files: {none | list}
- prior learnings: {matching LEARNINGS.md lines verbatim | none}
- task: {the user's task, verbatim, or the approved subtask}
- inputs: {paths this role must read, e.g. {run dir}/plan.md, {run dir}/reviews/code-review-2.md}
- constraints: {approved scope, files that must not be touched, user decisions; security only: blocking severities = config.flow.securityBlocksOn}
- expected output: {path of the file to write} + the return block from your role prompt
