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

E0/E1/E2 repeatability experiment completed and reported PASS by the user.
Stage 3A.0 is frozen.

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

### Result

- PR population, DD-PR group shift/scale, insufficiency ratios, and GDOP were
  highly repeatable across E0/E1/E2.
- Group-shift all/eligible P90 pairwise Spearman was approximately
  0.99997--0.99999; group-scale eligible P90 was approximately 0.996--0.999.
- Insufficiency ratios were identical in all three runs.
- The 219 s group-shift/scale anomaly repeated in all three runs.
- Raw phase P90 was less repeatable, with pairwise Spearman approximately
  0.945--0.974 and large differences at individual epochs.
- Trajectory output retained visible run-to-run variability; GT/APE is not an
  online reliability input or a calibration target.

### Interpretation

The PR/group/sufficiency evidence is sufficiently repeatable to freeze the
Stage 3A.0 mechanism. Raw phase evidence is ambiguity- and solver-path-coupled,
so it must not be treated as pure carrier-phase source quality. The next stage
is conditional evidence shadowing, not `R_G`/`C_G` construction or weighting.

## Stage 3A.1a: Conditional GNSS Evidence Shadow

### Status

Implemented in the current worktree and statically reviewed only. It has not
been compiled, runtime tested, repeatability tested, dataset tested, or
experimentally validated.

### Objective

Record first-solve-before ambiguity-provenance-conditioned phase evidence,
ambiguity-state transition evidence, and per-system Doppler center/dispersion
without changing the optimization objective or introducing final reliability
or confidence values.

### Configuration

- Reuses `estimate_gnss_source_reliability=false/true`.
- No new apply or conditional-evidence option is introduced.
- CSV output still additionally requires `log_intermediate_data=true`.

### Phase provenance and conditioned population

Each current DD carrier-phase factor is classified into both continued/no-slip,
both new, either mixed direction, any slip, or unknown. Continued requires both
an actual `RelativeAmbiguityError` connection and exact current-value equality
with the connected previous ambiguity; identity matching alone is not enough.
Slip metadata comes from the exact arranged observations stored at factor
construction and covers all four DD observations.

Only both-continued/no-slip factors contribute the loss-free normalized
continuity-conditioned phase-inconsistency population. It is not labeled pure
carrier-phase measurement error or reliability.

### Ambiguity transition evidence

The exact SD phase-code initializer is captured immediately after the existing
ambiguity construction and before the relative-ambiguity path can overwrite the
current value. For ambiguities with an actual continuation, the absolute
difference between that initializer and the connected previous value is
summarized by count/median/P90/max. It is unnormalized and measured in meters;
it is ambiguity-state transition evidence only.

Previous GNSS FIX/FLOAT status is logged as offline explanatory metadata only.
It is prohibited from entering `R_G`, `C_G`, or any current rule because it is
solver/AR-path dependent.

### Doppler conditional evidence

Loss-free normalized Doppler residuals are grouped by constellation. A separate
per-system CSV records factor/finite/failure counts, signed median normalized
center, and `1.4826*MAD` normalized scale without a floor. The epoch CSV records
system support and center/scale summaries. Because each factor may use different
information, these quantities are per-system frequency/velocity-conditioned
Doppler evidence, not exact cancellation of a raw receiver-frequency offset.

No raw-domain common-offset estimator or Jacobian nuisance projection is added
in Stage 3A.1a.

### Required validation

Compile and run in the user's container. Check option=false behavior, shadow
optimizer invariance, categorical count/ratio closure, continuity-conditioned
finite counts, transition units, per-system Doppler aggregation, and CSV field
alignment. Repeat the shadow run before considering Stage 3A.1b or any final
`R_G`/`C_G` design.

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
