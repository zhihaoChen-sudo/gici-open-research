# Current Task Status

Last reconciled: 2026-08-21

## Current objective

Develop multi-source reliability-aware fusion without further robust-loss
replacement. The active implementation is Phase 1 only: add optional Graph
ownership for factor-specific loss functions. No estimator currently uses the
new owned-loss API, and DD pseudorange reliability weighting is reserved for
Phase 2.

---

## Repository state

- Branch: `exp/pseudorange-firstsolve-huber`
- HEAD before the current worktree change: `f458046`
  (`research: add configurable DD pseudorange Cauchy loss experiment`)
- Validated diagnostics baseline tag: `rrr-diagnostics-baseline-v1` at
  `f5c2125`
- Separate historical experiment branch: `exp/reopt-after-gnss-rejection` at
  `cd42a61`; it is **not** the current branch and its second-optimize code is
  not present in the current worktree.

No final adaptive method, Huber delta change, rejection change, second solve,
or ambiguity change is implemented.

## Phase 1 final summary: Graph-owned loss infrastructure

**Status:** implemented and statically inspected; `git diff --check` passed.
It has not been compiled or runtime tested.

Modified production files:

- `include/gici/estimate/graph.h`
- `src/estimate/graph.cpp`

`Graph::ResidualBlockSpec` now has an optional shared owner for a
factor-specific `ceres::LossFunction`, and the opt-in
`Graph::addResidualBlockWithOwnedLoss()` API stores that owner while Ceres
continues to receive the same raw pointer under `DO_NOT_TAKE_OWNERSHIP`.
Removal still calls `ceres::Problem::RemoveResidualBlock()` before erasing the
Graph bookkeeping that owns the loss. Parameter removal, marginalization, and
direct residual removal therefore converge on the same safe release path. The
explicit `Graph` destructor destroys the Ceres Problem before member maps and
their owned losses are destroyed.

Baseline mathematics is unchanged: every existing factor still calls the
original `addResidualBlock()` API, all existing loss pointers remain borrowed,
and no caller uses the new owned-loss API. Residual models, factor ordering,
solver settings, rejection, ambiguity resolution, marginalization logic, and
diagnostics are unchanged. No Phase 2 reliability option, indicator, weight,
or DD pseudorange cost scaling is implemented.

Remaining validation before relying on the infrastructure:

1. compile the repository in the known-working environment;
2. run a focused owned/borrowed loss lifetime test covering direct residual
   removal, parameter-removal cascade, reset, marginalization, and Graph
   destruction, preferably with AddressSanitizer;
3. run the existing option-false baseline and confirm unchanged factor counts,
   loss diagnostics, solver costs, rejection/AR sequence, and trajectory; and
4. verify the new owned-loss API still has no production caller before Phase 2
   begins.

---

## Completed work already in the validated diagnostics baseline

The baseline commit `f5c2125` already contains the following RRR diagnostics,
enabled by `base_options_.log_intermediate_data` and written beneath
`base_options_.log_intermediate_data_directory`:

- post-fit/pre-GNSS-rejection GNSS factor CSV,
  `gnss_residual_diagnostics-<timestamp>.csv`, for DD pseudorange, DD carrier
  phase, and rover Doppler;
- visual reprojection factor CSV, including whitened/raw 2D residuals and
  factor covariance-derived effective pixel sigma;
- latest-state IMU factor CSV, including the 15D whitened residual, interval
  sample statistics, velocity, and biases;
- HMC/NHC motion-constraint CSV, separate from IMU;
- GNSS rejection-event CSV with residual IDs and stage/role attribution; and
- RRR epoch CSV with GNSS stage snapshots, rejection counts, and AR/unfix
  status fields.

The GNSS diagnostic lookup deliberately uses guarded direct map lookup rather
than `GnssMeasurement::getObs()`. A missing observation is warned and skipped;
it does not terminate the estimator. This protects diagnostics against the
known possibility that an error index's `code_type` reflects
`Observation::raw_code` while the observation map uses an arranged-code key.

All three GNSS measurement factor classes use the shared
`EstimatorBase::huber_loss_function_`, initialized in
`src/estimate/estimator_base.cpp` as `ceres::HuberLoss(1)`. This applies to
DD pseudorange, DD carrier phase, and Doppler; it is not a pseudorange-only
baseline loss.

---

## Diagnostics implemented at the current HEAD

### GNSS pre-opt/post-fit pairing and loss diagnostics

The current HEAD includes:

- `gnss_preopt_residual_diagnostics-<timestamp>.csv`, enumerated for the
  latest GNSS state after factors enter the graph and immediately before the
  original first `optimize()`;
- unchanged semantic placement of the existing post-fit CSV: after that first
  `optimize()` and before any GNSS rejection;
- shared `residual_uid` (the in-run `ResidualBlockId` value) for pre/post
  association only;
- `loss_type`, `loss_delta`, `rho0`, `rho1`, and `rho2` in both CSVs;
- direct use of the residual block's actual
  `LossFunction::Evaluate(s, rho)` with `s = normalized_residual^2`, rather
  than a hand-written Huber approximation; and
- compatibility for a future null loss: `loss_type=none`, `rho0=s`,
  `rho1=1`, and `rho2=0`.

The residual evaluation explicitly uses
`EvaluateResidualBlock(..., false, ...)`: it records the factor's whitened
residual without applying the Ceres robust loss. `deNormalizeResidual()` is
then applied only to a copied residual for the raw physical residual and to a
unit probe for effective sigma.

### Pre-opt epoch summary and timing

The current diff also appends to `rrr_epoch_diagnostics`:

- pre-opt max absolute normalized residual and `>3`/`>5` counts for each of
  DD pseudorange, DD carrier phase, and Doppler; and
- `first_optimize_ms`, `gnss_rejection_ms`, `ar_ms`, and
  `epoch_compute_ms`, measured with `std::chrono::steady_clock`.

The pre-opt summary is accumulated during the pre-opt CSV enumeration; it
does not perform a second residual evaluation. For a measurement type with no
successfully evaluated factor, its counts remain zero and its maximum is NaN.

`first_optimize_ms` brackets only the original first `optimize()` call.
`gnss_rejection_ms` brackets the three original rejection stages and final
after-rejection ID collection. `ar_ms` brackets the existing float status,
ambiguity covariance/`solveRtk()`, and continuous-unfix reset path.
`epoch_compute_ms` runs from immediately before the first optimize until the
AR path completes. The diagnostic-call elapsed time (IMU/Motion, post-fit
GNSS, and rejection-event logging) is subtracted; pre-opt logging occurs
before the timing start and epoch CSV writing occurs after the timing end.
It is a core RRR-update timing diagnostic, not end-to-end sensor-to-publish
latency.

All new evaluation failures and absent error interfaces are warning-and-skip
paths; the residual buffer is not read after a failed evaluation.

### Completed GNSS CSV diagnostics repair

A 4.1 diagnostic baseline run exposed two logger defects:

- DD pseudorange and DD carrier-phase rows omitted the empty `doppler_lli`
  cell, producing 32 fields against the original 33-field header and shifting
  the loss columns; and
- after `EvaluateResidualBlock()` succeeded, a missing guarded observation
  lookup caused the logger to `continue`, so the factor row was absent even
  though the pre-opt summary retained its normalized residual.

Commit `f5edd11` repairs these issues: it appends `metadata_complete` to both
GNSS residual CSVs, preserves every successfully evaluated GNSS factor row, leaves unavailable
metadata blank, and adds an offline field-count checker. It does not change
any estimator computation.

---

## Validation performed

- Read-only source audit of the relevant RRR, GNSS, Graph, and
  `EstimatorBase` paths.
- Review of the complete current `git diff`.
- `git diff --check` passed after the current diagnostic changes.
- A 4.1 diagnostic baseline run was completed and jointly analyzed; it
  identified the CSV field-alignment and metadata-row-loss defects.
- The CSV repair and offline checker were committed in `f5edd11`.

## Validation not yet performed

- Compilation of the CSV diagnostics repair.
- ROS/RRR runtime execution with the repaired CSV output.
- Inspection of produced pre-opt/post-fit CSV rows and headers.
- Verification that a pre/post pair shares the expected residual UID and that
  all current GNSS measurement factors report `huber,1`.
- Validation of NaN/zero handling for epochs without a factor type.
- Timing sanity check against runtime logs.
- Dataset-level residual/APE/AR analysis or numerical-position comparison.

Do not describe this committed work as compiled, runtime tested, or
experimentally validated.

---

## Validated and negative findings

### Validated findings

- The diagnostics baseline covers GNSS, Vision, IMU, Motion, GNSS rejection,
  RRR epoch state, AR/unfix status, pre-opt/post-fit GNSS pairing, robust-loss
  quantities, and core update timing.
- The source audit verifies that the existing shared `HuberLoss(1)` is applied
  to DD pseudorange, DD carrier phase, and rover Doppler factors.
- The 4.1 baseline run verified that the diagnostic CSV defects described
  above existed. Their implementation repair is committed, but its runtime
  output has not yet been revalidated.

### Negative findings and rejected approaches

1. **No new Huber experiment is currently warranted.** The earlier intended
   comparison of `loss=nullptr` versus `Huber(1.345)` was rejected after the
   source audit: the validated baseline already uses `Huber(1)` for all three
   GNSS measurement factor types. Replacing it with `nullptr` would change the
   baseline, while `1.345` would be weaker rather than an unambiguous
   strengthening.

2. **The re-optimize-after-rejection experiment is not a final algorithm.**
   The separate branch `exp/reopt-after-gnss-rejection` contains its isolated
   conditional second solve. Prior A×3/B×3 runtime evidence reported that it
   improved one repeat but did not reproduce in two others and caused roughly
   56% of GNSS epochs to perform an additional nonlinear solve. Treat it as a
   rejected final real-time method, not code to merge into this branch.

3. **Post-fit residuals are diagnostic inconsistency scores, not pre-fit
   innovations/NIS.** They are affected by the joint solve, shared parameter
   blocks, and robust losses. The pre-opt/post-fit pair is needed to separate
   first-solve inconsistency from post-fit accommodation.

4. **Do not use `raw_residual / normalized_residual` for sigma.** A unit probe
   through `deNormalizeResidual()` avoids an unstable near-zero division.

5. **Do not infer observation lookup semantics from a factor index alone.**
   Preserve guarded lookup and warning context rather than changing
   `getGnssMeasurementIndex()` or `GnssMeasurement::getObs()`.

6. **A pre-opt summary and its factor CSV must enumerate the same successful
   residual evaluations.** Metadata availability is contextual only; it must
   not determine whether an already evaluated residual receives a CSV row.

---

## Current algorithm hypothesis and implementation

The current, unvalidated hypothesis recorded in
`docs/research/ALGORITHM_DECISION.md` is that persistent DD-pseudorange gross
inconsistency entering the first nonlinear solve is the dominant unresolved
failure mode. The document names a DD-pseudorange-only redescending robust
loss as its first candidate and keeps all other factor classes and the AR
pipeline unchanged.

The controlled Cauchy(1) mechanism is implemented behind an RRR-only,
default-false option. This is still a research hypothesis, not a validated
causal conclusion or final adaptive method. The existing negative findings
above remain in force.

## Next experimental plan

First compile and run the committed diagnostics baseline in the user's
known-working ROS environment. For the repaired output, run one unchanged RRR
configuration with intermediate logging enabled, then use
`python3 tools/check_gnss_residual_csv.py <preopt.csv> <postfit.csv>` and
inspect a short time window to verify:

1. both GNSS CSVs are created with the documented header;
2. pre-opt and post-fit rows share `residual_uid` within a run;
3. DD pseudorange, DD carrier phase, and Doppler all report actual
   `huber,1` loss diagnostics and finite `rho0/rho1/rho2`;
4. absent factor types produce `NaN,0,0` in the corresponding epoch summary;
5. `first_optimize_ms`, rejection, AR, and epoch timings are plausible and
   no diagnostic warning causes an abort; and
6. enabling diagnostics does not alter the output trajectory versus the same
   configuration without diagnostics, within normal deterministic/replay
   expectations.

Then compare the same build and configuration with
`use_cauchy_loss_for_dd_pseudorange=false` and `true`. Verify that false logs
Huber(1) for all GNSS factors, while true logs Cauchy(1) only for DD
pseudorange and Huber(1) for DD carrier phase and Doppler. Do not combine
mechanisms or alter Vision, IMU, Motion, rejection, solver, or AR behavior.

---

## Completion checklist

- [x] factor-level GNSS, Vision, IMU, Motion, rejection, and epoch diagnostics
  implemented in the validated diagnostics baseline
- [x] pre-opt/loss/summary/timing diagnostics committed at `696300a`
- [x] current `git diff --check`
- [x] GNSS CSV repair and offline field-count checker committed at `f5edd11`
- [x] RRR-only, default-false DD pseudorange Cauchy(1) option implemented
- [x] diagnostics distinguish Huber and Cauchy loss pointers
- [ ] compilation of the committed diagnostics baseline
- [ ] compilation of the controlled Cauchy experiment
- [ ] runtime execution and CSV inspection
- [ ] timing sanity check
- [ ] numerical/trajectory comparison
- [ ] controlled single-candidate algorithm experiment
- [ ] dataset-level failure attribution and experimental conclusion
