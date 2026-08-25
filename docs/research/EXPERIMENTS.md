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

### Historical transition

At this handoff, persistent DD-pseudorange inconsistency entering the first
solve was the next unvalidated hypothesis. Later factor-level experiments and
their conclusions are recorded below; this diagnostics-phase section is not the
current research plan.

## Stage 2B: DD pseudorange factor-level intervention

### Status

Repeated B1/M1, B2/M2, and B3/M3 comparisons were reported complete by the
user. This stage is closed as a factor-level feasibility study; its mechanism
and parameters are frozen.

### Mechanism

Low-reliability DD pseudorange factors identified before their first nonlinear
solve used `ScaledLoss(HuberLoss(1), estimated_weight)`. The residual,
information, Jacobian, carrier phase, Doppler, other sensors, rejection, AR,
solver, and marginalization paths were unchanged.

### Result

- The factor reliability estimate behaved stably across repeats.
- Low-reliability factors were downweighted before their first solve.
- No obvious runtime degradation was reported.
- Trajectory-tail improvement was not repeatable across B1/M1, B2/M2, and
  B3/M3.

### Interpretation

The experiment supports feasibility of pre-first-solve factor-level evidence
and intervention. It does not establish repeatable trajectory robustness,
system-level GNSS reliability management, or cross-dataset generalization.
Further tuning of the Stage 2 threshold, floor, loss family, or a second solve
is not the next research direction.

## Stage 3A.0: Generalizable GNSS Source Reliability Evidence Shadow

### Status

Implemented in the current worktree and statically reviewed only. Compilation,
runtime execution, CSV inspection, dataset testing, and experimental validation
remain pending.

### Objective

Record first-solve-before, source-level GNSS evidence without changing the
optimization objective. The residual evidence means normalized inconsistency
between the predicted multi-sensor state and GNSS observations; it is not pure
GNSS measurement error.

### Configuration

- `estimate_gnss_source_reliability=false`: frozen behavior; no source evidence
  computation or source-evidence CSV.
- `estimate_gnss_source_reliability=true`: shadow computation, with CSV output
  only when `log_intermediate_data=true`.
- No apply option exists.

### Recorded evidence

- loss-free DD pseudorange, DD carrier-phase, and Doppler population counts and
  absolute normalized-residual statistics;
- exact arranged-key DD pseudorange all-group shift, eligible-group shift,
  eligible-group MAD scale, and explicit group/factor insufficiency;
- unique rover-side satellites used by current GNSS factors, including DD
  reference satellites;
- GDOP with explicit sentinel validity;
- complete-population elevation statistics when available; and
- explicitly invalid/NaN SNR statistics until source-wide association and unit
  semantics are established.

### Generalization Contract

`docs/research/GENERALIZATION_CONTRACT.md` is a hard constraint: no online
GT/EVO/APE, event-time, location, route, satellite-ID, or dataset-identity
logic; first-solve evidence must be available before the first optimize; and
mechanisms/parameters must eventually be frozen before external validation.

### Next validation

Run otherwise identical option=false/true shadow pairs in the user's container.
Verify trajectory, solver, rejection, and AR invariance before interpreting the
new CSV. Do not proceed to Stage 3A.1 or formulate/apply `R_G`/`C_G` until this
shadow evidence has been inspected.

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
