# Experiment Log

## Diagnostics-phase handoff

### Status

Diagnostics instrumentation is complete in `f5edd11` (`baseline: finalize
diagnostics phase before algorithm development`). This is a handoff record,
not an algorithm experiment result.

### Completed diagnostics

- GNSS pre-opt/post-fit residual pairing, robust-loss values, rejection-event
  attribution, and RRR update timing are available.
- Existing Vision, IMU, Motion, RRR epoch, and AR/unfix diagnostics remain
  part of the baseline.
- The GNSS CSV field-alignment and metadata-row-loss repair, with an offline
  checker, is committed in `f5edd11`.

### Validated findings

- Source inspection verifies a shared `HuberLoss(1)` on DD pseudorange, DD
  carrier phase, and rover Doppler factors.
- A 4.1 baseline diagnostic run exposed the two GNSS CSV defects repaired in
  `f5edd11`.

### Negative findings and rejected approaches

- The `nullptr` versus `Huber(1.345)` comparison was rejected: it would not
  compare against the actual baseline, and `1.345` is weaker than the
  existing `Huber(1)`.
- Re-optimizing after GNSS rejection is rejected as a final real-time method:
  prior A×3/B×3 evidence improved one repeat, did not reproduce in two, and
  added a second nonlinear solve in about 56% of GNSS epochs.
- Post-fit residuals alone are not pre-fit innovations/NIS and cannot by
  themselves establish the source of a fault.

### Current hypothesis and next experiment

The unvalidated current hypothesis is persistent DD-pseudorange gross
inconsistency entering the first nonlinear solve. The already recorded first
candidate is a DD-pseudorange-only redescending robust loss; all other factor
classes and the AR pipeline remain unchanged. Before evaluating it, compile
and rerun the committed diagnostics baseline, validate the repaired CSVs with
the checker, and retain that baseline as the controlled comparator.

### Not yet validated

The repaired CSV runtime output, timing sanity, trajectory equivalence with
diagnostics enabled, and any algorithm result are not yet compiled, runtime
tested, or experimentally validated.

## EXP-001

### Date

YYYY-MM-DD

### Objective

What hypothesis is being tested?

### Git state

Branch:

Commit:

Uncommitted changes:

### Dataset

Dataset:

Sequence:

Time interval:

### Configuration

Config file:

Important parameter changes:

### Code changes

Describe only changes relevant to this experiment.

### Expected result

What should happen if the hypothesis is correct?

### Actual result

Record observed behavior.

### Metrics

Position RMSE:

Maximum error:

Fix rate:

Other metrics:

### Diagnostics

Relevant CSV/log files:

### Interpretation

What does the result support?

What does it NOT prove?

### Decision

- keep
- reject
- investigate further

### Next experiment

...
