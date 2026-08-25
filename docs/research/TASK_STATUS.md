# Current Task Status

Last reconciled: 2026-08-25

## Current objective

Develop a generalizable multi-source reliability-aware fusion framework without
further robust-loss replacement. Stage 2B has completed its factor-level
feasibility study. The active worktree implements Stage 3A.0, a shadow-only
GNSS source reliability evidence extractor that runs before the first nonlinear
solve and does not change optimization behavior.

---

## Repository state

- Branch: `exp/pseudorange-firstsolve-huber`
- HEAD before the current Stage 3A.0 worktree change: `eb2c545`
  (`research: apply DD pseudorange reliability-aware factor weighting`)
- Validated diagnostics baseline tag: `rrr-diagnostics-baseline-v1` at
  `f5c2125`
- Separate historical experiment branch: `exp/reopt-after-gnss-rejection` at
  `cd42a61`; it is **not** the current branch and its second-optimize code is
  not present in the current worktree.

The user-provided `docs/research/GENERALIZATION_CONTRACT.md` is now a hard
constraint for subsequent design: no online GT/EVO/APE, event-time, location,
route, satellite-ID, or dataset-identity logic; evidence used by the first solve
must be available before that solve; and mechanisms/parameters must eventually
be frozen for external sequence/dataset validation.

No final GNSS reliability/confidence formula, source weighting, covariance
adaptation, temporal trust, quarantine, Vision/IMU reliability, cross-source
weighting, adaptive threshold, second solve, solver change, or ambiguity change
is implemented by Stage 3A.0.

## Phase 1 final summary: Graph-owned loss infrastructure

**Status:** validation completed and the infrastructure was accepted, as
confirmed by the user before Stage 2A began.

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

Baseline mathematics is unchanged: existing factor paths continue to use the
original `addResidualBlock()` API with borrowed loss pointers. Stage 2A also
does not call the owned-loss API.

## Stage 2A final summary: reliability shadow estimation

A new RRR-only option, `estimate_reliability_for_dd_pseudorange`, defaults to
`false` and is mutually exclusive with the historical DD pseudorange Cauchy
option. When enabled, DD pseudorange candidates are directly evaluated at the
current pre-opt pose and extrinsics, grouped by constellation, base satellite,
and four code types, and assigned diagnostics-only peer-consistency metadata.
The estimated weight is logged but `applied_weight` is fixed to 1.0.

Every Stage 2A DD pseudorange factor is still inserted with the existing shared
`HuberLoss(1)` raw pointer. No `ScaledLoss` is constructed, and no owned-loss
API is called. `PseudorangeErrorDD::Evaluate`, Jacobians, information, carrier
phase, Doppler, vision, IMU, motion constraints, rejection, ambiguity
resolution, solver, and marginalization are unchanged.

With the option enabled, a separate
`dd_pseudorange_reliability_diagnostics-<timestamp>.csv` records the direct
residual, the immediate post-insertion `EvaluateResidualBlock(false)` value,
the normal pre-opt Graph value, their differences, peer statistics, estimated
weight, and applied weight. The separate file is not created when the option
is false, leaving existing diagnostic CSV schemas unchanged.

Stage 2A runtime validation was reported complete by the user. The estimated
weight is calibrated to factor-level DD pseudorange post-fit residual/rejection
abnormality, but a single-epoch reliability score has weak simple ROC/AUPRC
ability for predicting future trajectory spikes. Stage 2A therefore supports
a controlled intervention experiment; it must not be described as a trajectory
spike predictor.

## Stage 2B final experimental summary: factor-level feasibility

An RRR-only option, `apply_reliability_weight_for_dd_pseudorange`, defaults to
`false` and requires `estimate_reliability_for_dd_pseudorange=true`. The three
preserved modes are baseline (`false,false`), Stage 2A shadow (`true,false`),
and Stage 2B method (`true,true`). Cauchy is mutually exclusive with both
reliability modes.

The Stage 2A indicator and fixed mapping are unchanged. When application is
enabled and `estimated_weight < 1`, the DD pseudorange factor uses a Graph-owned
`ScaledLoss(HuberLoss(1), estimated_weight)`. Factors with weight 1 continue to
use the original shared `HuberLoss(1)` pointer. The implemented objective is
`0.5 * w_i * rho_Huber(1)(e_i^2)`; residuals, covariance/information, Jacobians,
Huber delta, and the loss-free rejection residual definition are unchanged.
The weight is computed once before insertion and frozen in the factor's loss
for its lifetime.

Diagnostics retain loss-free direct/post-insertion/pre-opt residual semantics.
The reliability CSV records the actual applied weight, and GNSS residual CSVs
identify weighted DD pseudorange factors as `loss_type=scaled_huber`. Carrier
phase and Doppler remain on the shared Huber loss.

Known limitation: a group-wide common-mode DD pseudorange bias can move the
group median without creating a large within-group deviation. Stage 2B records
but does not address this limitation.

Repeated B1/M1, B2/M2, and B3/M3 experiments were reported complete by the
user. The factor-level reliability estimate behaved stably, low-reliability DD
pseudorange factors were downweighted before their first solve, and runtime had
no obvious degradation. However, trajectory-tail improvement was not repeatable
across the three comparisons. Stage 2B therefore establishes factor-level
intervention feasibility, but it is insufficient evidence for system-level or
cross-dataset robustness. Its mathematics and parameters are frozen.

## Stage 3A.0 current worktree: GNSS source evidence shadow

The RRR-only option `estimate_gnss_source_reliability` defaults to `false`.
When enabled, a logger-independent computation enumerates current DD
pseudorange, DD carrier-phase, and Doppler factors immediately before the first
`optimize()`, evaluates their loss-free normalized residuals, and produces
population, DD-pseudorange group shift/scale, insufficiency, used-satellite,
GDOP, and elevation evidence. The semantics are normalized inconsistency
between the predicted multi-sensor state and the current GNSS observations,
not pure GNSS measurement error.

DD pseudorange groups use the exact arranged construction indexes independently
of the Stage 2 options. All groups with finite evidence contribute group-shift
statistics, while MAD scale and separate eligible-shift statistics require at
least four finite factors. Insufficient groups/factors and their ratios remain
explicit evidence. Empty distributions and unavailable metadata are NaN rather
than healthy zeros. SNR remains explicitly invalid in the first version because
the complete source-wide arranged observation association and unit semantics
have not been established.

The evidence can be computed with `log_intermediate_data=false`; CSV logging is
only an optional consumer. No evidence is applied to the Graph, residuals,
losses, covariance, rejection, AR, solver, marginalization, Vision, IMU, or
Motion. Stage 3A.0 has not been compiled, runtime tested, dataset tested, or
experimentally validated.

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
- Stage 2A shadow-mode runtime validation was reported complete by the user;
  its weight has factor-level anomaly calibration but weak simple future-spike
  prediction ability.
- Stage 2B B1/M1, B2/M2, and B3/M3 runtime experiments were reported complete
  by the user. Factor-level behavior was stable, but trajectory-tail benefit was
  not repeatable.
- Stage 3A.0 implementation has undergone source-level/static review only.

## Validation not yet performed

- Compilation of the Stage 3A.0 worktree.
- Runtime verification that option=false reproduces the frozen Stage 2B code
  path and option=true changes only evidence computation/logging.
- CSV schema/row-count, finite/failure accounting, NaN, ratio, exact grouping,
  GDOP-validity, and elevation-validity checks.
- Runtime cost of source evidence with logging disabled and enabled.
- Cross-sequence/dataset calibration of the recorded evidence distributions.

Do not describe Stage 3A.0 as compiled, runtime tested, dataset tested, or
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

## Current research hypothesis and implementation

Stage 2B showed that factor-local DD pseudorange reliability can be estimated
and applied before the first solve, but the resulting trajectory-tail benefit
was not repeatable. The current hypothesis is therefore narrower: population
inconsistency, group/common shift, group dispersion, geometry, and evidence
sufficiency may provide a more complete and generalizable description of GNSS
source reliability than a single DD-pseudorange factor-local score.

Stage 3A.0 only records those quantities. It does not claim that they form a
validated GNSS source reliability estimator and does not define or apply a
source reliability/confidence value.

## Next experimental plan

Compile Stage 3A.0 in the user's container, then compare identical runs with
`estimate_gnss_source_reliability=false/true`. First verify optimization,
rejection, AR, and trajectory invariance and validate the evidence CSV schema.
Then perform offline normal/failure-window inspection under the Generalization
Contract. Do not construct `R_G`, `C_G`, source weights, temporal logic, or
cross-source trust until the shadow evidence has been evaluated.

---

## Completion checklist

- [x] factor-level GNSS, Vision, IMU, Motion, rejection, and epoch diagnostics
  implemented in the validated diagnostics baseline
- [x] pre-opt/loss/summary/timing diagnostics committed at `696300a`
- [x] current `git diff --check`
- [x] GNSS CSV repair and offline field-count checker committed at `f5edd11`
- [x] RRR-only, default-false DD pseudorange Cauchy(1) option implemented
- [x] diagnostics distinguish Huber and Cauchy loss pointers
- [x] Phase 1 Graph-owned loss infrastructure accepted
- [x] Stage 2A shadow reliability implementation and user-run validation
- [x] Stage 2B factor-level weighting implemented at `eb2c545`
- [x] Stage 2B B1/M1 through B3/M3 experiments reported complete
- [x] Stage 2B classified as a factor-level feasibility study
- [x] Generalization Contract adopted as a hard design constraint
- [x] Stage 3A.0 shadow evidence implemented in the current worktree
- [x] current `git diff --check`
- [ ] Stage 3A.0 compilation
- [ ] Stage 3A.0 option=false/true invariance run
- [ ] Stage 3A.0 evidence CSV sanity and timing checks
- [ ] Stage 3A.0 offline evidence assessment
- [ ] cross-dataset evidence calibration/validation
