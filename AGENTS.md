# GICI-LIB Research Agent Instructions

## Project purpose

This repository is being used for research on robust RTK/IMU/Camera
multi-sensor fusion based on GICI-LIB.

The current research focuses on:
- GNSS factor diagnostics
- RTK ambiguity fixing / unfixing behavior
- robust residual processing
- adaptive weighting / RRR-related methods
- maintaining estimator accuracy, continuity, and robustness

## General rules

1. Never modify algorithm behavior unless explicitly requested.
2. Diagnostic/logging changes must remain read-only and must not affect estimator results.
3. Do not silently refactor unrelated code.
4. Do not remove or overwrite user changes.
5. Do not revert files without explicit permission.
6. Prefer the smallest change that satisfies the requested task.
7. Preserve existing GICI-LIB architecture and coding style unless there is a concrete reason not to.

## Before modifying code

Always inspect:

1. `git status`
2. `git diff`
3. `docs/research/TASK_STATUS.md`
4. relevant implementation and header files

Understand the current implementation before editing.

Do not assume that previous chat context is complete or correct if repository evidence disagrees with it.

## Source of truth

Use this priority order:

1. current source code
2. runtime / experimental evidence
3. git history and diff
4. TASK_STATUS.md
5. other research documentation
6. chat history

If chat history conflicts with repository state, repository state wins.

## Validation terminology

Never confuse these states:

- implemented
- static inspection completed
- `git diff --check` passed
- compiled
- runtime tested
- dataset tested
- experimentally validated

Never claim a stage has completed unless it actually has.

## Diagnostics

Diagnostics should:

- avoid changing estimator state
- avoid changing factor construction
- avoid changing optimization behavior
- avoid changing residual values
- reuse existing observations and residual enumeration when possible
- avoid introducing duplicate observation lookup mechanisms
- handle missing observations safely
- clearly distinguish raw, normalized, weighted, and robust-loss quantities

## Algorithm changes

Before changing estimator behavior:

1. explain the intended algorithmic change
2. identify the exact affected code path
3. identify possible side effects
4. distinguish diagnostic changes from algorithm changes
5. preserve a way to compare against baseline behavior

## Failed approaches

Before retrying an approach previously marked as failed in
`TASK_STATUS.md`, determine whether the underlying assumptions have changed.

Do not blindly retry failed approaches.

## Git

Before substantial modifications, understand the current branch and diff.

Do not create commits, switch branches, reset, checkout files, or push unless explicitly requested.

## Completion

Before declaring a task complete:

1. inspect `git diff`
2. inspect `git status`
3. compare implementation against the requested scope
4. report exactly what validation was and was not performed
5. update `docs/research/TASK_STATUS.md`
