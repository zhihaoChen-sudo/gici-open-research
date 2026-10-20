# Current Task Status

Last reconciled: 2026-09-10

## Current objective

Develop a generalizable multi-source reliability-aware fusion framework without
further robust-loss replacement. Stage 3A.0 repeatability validation has passed
and is frozen. Stage 3A.1a is closed as a **PARTIAL PASS**. Stage 3A.1b-0
semantic architecture passed design review, and Stage 3A.1b-0T completed the
4.1-to-4.2 transfer audit with a **PARTIAL PASS**: semantic transfer and
within-4.2 repeatability passed, while evidence availability showed a domain
shift. The active work remains **Stage 3A.1b-1 — Reliability Mapping /
Calibration**, with offline prototypes only and no authorized runtime mapping
or control. **Stage 3A.1b-1b.3 — Offline Calibration Prototype
Execution** completed under the frozen `S3A1b1b3-v1` manifest and is classified
**PARTIAL**. Input/schema validation passed, the representation audit supported
multivariate PR attribution, and synthetic nominal mechanics passed 59/60
coverage checks with zero downward-closure violations. Cross-session empirical
correction candidates were not stable enough to approve as normative
calibration. A repeat-hierarchy review then found that the original transfer
pooled C0/C1/C2 or T0/T1/T2 as one source block population. **Stage
3A.1b-1b.3R — Corrective Transfer Rerun** is now complete: every source repeat
was fitted independently and applied to all three target repeats, forming two
3x3 nested-repeat matrices. **3R corrective execution integrity = PASS**;
**Stage 3A.1b-1b calibration-prototype scientific outcome = PARTIAL**. The original
transfer block counts, tail eligibility, bootstrap CIs, candidate directions,
support-domain applicability inference, and contamination inference are superseded by 3R.
The previous claim `preregistration deviation = none` is withdrawn; the pooled
repeat hierarchy was one preregistration deviation, corrected by 3R. Stage
3A.1b-1b.2 completed DESIGN PASS WITH SEMANTIC REFINEMENTS and is FROZEN. Stage 3A.1b-1b.1 completed DESIGN PASS WITH ONE
MATHEMATICAL REVISION: current multivariate evidence, its conditional
calibrated reference region, and the resulting current assessment are distinct
objects. Stage 3A.1b-1a is FROZEN. Hybrid is the preferred prototype calibration
direction but is not a final calibrator selection.
Mandatory scalar or interval `R_G`/`C_G` is rejected; source compression is
optional and task-specific. No online calibration implementation, weighting,
covariance adaptation, gating, or temporal trust is authorized.

The active stage is **Stage 3A.1b-1b.4 — Independent-Session Calibration
Panel Expansion**. Its metadata-only data-role audit is complete and the
data-role split is frozen: 1.1--5.1 excluding untouched 5.2 form the
same-platform development/calibration panel, with 5.1 retained as a separately
stratified long-duration development session; 5.2 remains the untouched
internal hold-out. That data-role decision used metadata/config/provenance
only; its audit did not read reliability CSVs, trajectory outcomes, GT/APE,
AR/FIX results, or 5.2 content. The subsequent 4b/R1 sanity audits read only
the frozen pre-solve evidence whitelist.

**Stage 3A.1b-1b.4b-R1 — 5.1 Rerun Admission Audit** is complete. The new 5.1
artifact is `EligibleForPanel`, supersedes the old rejected 5.1 artifact, and
makes the final Stage 4b panel result **PASS**: all eleven sequences are
`EligibleForPanel`, with no `Partial` or `Reject`. The old artifact remains
retained for provenance but is not a calibration input. The current
executable/config hashes are recorded, but no run
artifact binds them retrospectively; binary binding remains unproven. This is
an evidence-integrity/provenance decision, not a trajectory or
reliability-quality judgment.

**Stage 3A.1b-1b.4c-P is FROZEN under `S3A1b1b4cP-v1`, and Stage
3A.1b-1b.4c-E has completed. ExecutionIntegrity = PASS; ScientificOutcome =
PARTIAL.** The primary realization is sequence-balanced across eleven physical
sequences and three acquisition-date clusters; C1/C2 and T1/T2 never add panel
weight. All 90% tail rows are Eligible. At 95%, 36/38 rows are Eligible and two
PR rows are Partial. All 38 99% rows remain DiagnosticOnly; ten meet only the
support prerequisites for possible upgrade review, not the complete stability
requirements. LOSO 90/95 folds are assessable without explicit direction
reversal. Leave-date-cluster-out is weaker: at 95% it has 76 Assessable, 33
Partial, and five DiagnosticOnly rows, with one PR group-shift direction
reversal. Contamination sensitivity is the dominant statistical limitation;
only 4/38 primary 90% rows satisfy both frozen epsilon=0.10/0.20 envelope-width
heuristics. No empirical mismatch ratio is normative and 0/114 rows are
EligibleForNormativeReview. Current full CalibrationApplicability also remains
unknown beyond prototype support-domain descriptors. The unavailable 4.2 T1/T2
CSV artifacts make the current 4.2 repeat-sensitivity part NotAssessed; no
substitute, rerun, or parameter change was made.

---

## Repository state

- Branch: `exp/pseudorange-firstsolve-huber`
- Current documentation HEAD before this sync: `04909fb`
  (`docs: hand off Stage 3A.1a validation state`)
- Stage 3A.1a compile/run algorithm-source candidate: `0a732d6`
  (`fix: correct ambiguity provenance result type`). The user reports that the
  successful rebuild and OFF/C0/C1/C2 runs occurred after this fix and before
  the `04909fb` documentation commit. The repository history alone does not
  independently prove the binary-to-commit association, so this provenance
  remains user-reported rather than artifact-verified.
- Stage 3A.1a implementation: `2e25400`
  (`research: add conditional GNSS reliability evidence shadow`)
- Stage 3A.0 implementation: `944ab6c`
  (`research: add GNSS source reliability evidence shadow`)
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

No final channel calibrator, GNSS reliability/confidence formula, source weighting, covariance
adaptation, temporal trust, quarantine, Vision/IMU reliability, cross-source
weighting, adaptive threshold, second solve, solver change, or ambiguity change
is implemented by Stage 3A.1a.

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

## Stage 3A.0 frozen validation: GNSS source evidence shadow

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
Motion.

The user completed E0/E1/E2 repeatability runs and reported Stage 3A.0 PASS.
PR population, DD-PR group shift/scale, insufficiency, and GDOP evidence were
highly repeatable. Group-shift all/eligible P90 pairwise Spearman was about
0.99997--0.99999, group-scale eligible P90 about 0.996--0.999, insufficiency
ratios were identical, and the 219 s group-shift/scale anomaly repeated in all
three runs. Trajectory output still had substantial run-to-run variability, so
GT/APE must not be used to tune online reliability.

Raw carrier-phase evidence was materially more solver/path dependent: phase
P90 pairwise Spearman was about 0.945--0.974 and some epoch differences were
large. Source inspection attributes this to current pose and, especially, to
whether each ambiguity value is a current phase-code initializer or a value
copied through an actual relative-ambiguity connection. Raw phase evidence is
therefore conditional inconsistency, not pure carrier-phase source quality.

## Stage 3A.1a final experiment: conditional GNSS evidence shadow

Stage 3A.1a reuses `estimate_gnss_source_reliability`; no new option or apply
path is added. It records only first-solve-before shadow evidence:

- DD carrier-phase factors are classified as both continued/no-slip, both new,
  either mixed direction, any slip, or unknown. Continued requires an actual
  `RelativeAmbiguityError` connection and the current parameter value to equal
  the connected previous value; matching identity alone is insufficient.
- Only the both-continued/no-slip subset contributes the loss-free normalized
  continuity-conditioned phase-inconsistency population.
- Exact current SD phase-code ambiguity initializers are captured before the
  existing relative-ambiguity path can overwrite them. For actual continued
  ambiguities, initializer-minus-previous-value absolute innovations are
  summarized in meters as ambiguity-state transition evidence only.
- Previous GNSS FIX/FLOAT status is logged solely as offline explanatory
  metadata and does not enter any reliability/confidence rule.
- Loss-free normalized Doppler residuals are grouped by constellation. Each
  system records support, signed median center, and `1.4826*MAD` scale, followed
  by epoch summaries. Because factor information can differ, this is called
  per-system frequency/velocity-conditioned Doppler evidence, not exact raw
  receiver-frequency cancellation.

The implementation adds no `R_G`, `C_G`, source weighting, temporal trust,
nuisance projection, or optimizer intervention. The first user-side compile
attempt found that two variables receiving
`inspectAmbiguityValueProvenance()` were declared as the enum rather than its
actual `AmbiguityValueProvenanceResult` return type. Commit `0a732d6` applies
only that declaration correction. The user subsequently reported a successful
rebuild and completed OFF/C0/C1/C2 runs and formal analysis.

**Decision: PARTIAL PASS.** Phase category and ratio closure were exact,
unknown count was zero in C0/C1/C2,
`continuity_conditioned_count <= both_continued_count`, and Doppler per-system
count closure was exact. Overall phase provenance was approximately 94.5%
both-continued/no-slip, 0.7% both-new, 1.7% mixed, 3.0% any-slip, and 0%
unknown.

Conditioning did not improve global phase P90 rank repeatability. Raw phase
pairwise Spearman was approximately 0.9938/0.9461/0.9418 for C0/C1, C0/C2,
and C1/C2, while continuity-conditioned phase was approximately
0.9896/0.9169/0.9137. Do not tune the conditioner to improve dataset-4.1
correlation. Conditioning nevertheless strongly removed nuisance-driven
extreme tails: raw phase P90 had median about 1.66, P99 about 170, and maximum
about 1050 sigma, versus conditioned median about 1.33, P99 about 3.2--3.3,
and maximum about 7 sigma. This supports semantic/decontamination value, not
pure phase quality; conditioned phase remains state/path coupled.

Ambiguity-transition P90 was repeatable (Spearman approximately 0.986--0.992)
but was not strongly elevated at 135/165/213/219 s. It remains explanatory
ambiguity-state metadata and must not enter `R_G` directly. Doppler raw P90,
per-system center, and per-system scale were repeatable, respectively about
0.9994/0.9887/0.9887, 0.9989/0.9757/0.9761, and
0.9998/0.9929/0.9930. No more complex nuisance projection is justified by the
current evidence; Doppler system evidence remains shadow-only.

Offline event interpretation is: 135 s is more strongly a geometry/GDOP issue;
165 s is dominated by satellite support/GDOP/insufficiency; 213 s is dominated
by PR insufficiency; and 219 s combines strongly elevated conditioned phase
P90 (about the 86--88 percentile) with high PR group shift/scale under ordinary
GDOP, making it the strongest current source-level GNSS degradation case.
These times are offline mechanism probes only and are prohibited from online
rules.

## Stage 3A.1b-0T final experiment: 4.1 to 4.2 evidence transfer

Stage 3A.1b-0 semantic architecture completed **DESIGN PASS** before the
transfer audit. Its frozen channel/validity/dependency semantics remain design
only; no generic runtime `SourceEvidence` interface or reliability scalar was
implemented.

The user completed and formally analyzed 4.2 T0/T1/T2 under frozen Stage 3A
evidence definitions. **Stage 3A.1b-0T decision: PARTIAL PASS.** Implementation
and schema, cross-sequence semantic transfer, within-4.2 structural
repeatability, phase-provenance transfer, conditioned-phase semantic transfer,
PR/group repeatability, and Doppler transfer passed. Evidence availability was
a domain shift and therefore partial rather than a failure.

Across T0/T1/T2 there were 2340 GNSS-evidence epochs, exactly 48929 PR factors,
exactly 36898 phase factors, and zero evaluation failures. No-eligible-PR-group
epochs were exactly 474/2340 (20.26%) in each run, and the median PR
insufficient-factor ratio was exactly 0.642857. This stable insufficiency is
evidence about availability/confidence, not measurement badness.

Phase provenance transferred with approximately 94.0% continued, 0.4--0.5%
new, 2.78% mixed, 2.70% slip, and 0% unknown. Raw phase P90 retained extreme
tails (P99 approximately 885--1075 sigma, maximum approximately 1801--1812
sigma), while continuity conditioning reduced them to P99 approximately
4.16--4.30 sigma and maximum approximately 14.92--14.94 sigma. Conditioning
again had semantic/decontamination value but did not improve rank
repeatability; it remains corroborative and state/path coupled.

Pairwise T0/T1/T2 Spearman values were approximately
0.9966/0.9987/0.9931 for PR P90, 0.9963/0.9981/0.9927 for all-group PR shift,
0.9934/0.9979/0.9903 for eligible-group shift, 0.9774/0.9912/0.9695 for group
scale, 0.9882/0.9948/0.9864 for raw phase P90,
0.9770/0.9869/0.9766 for conditioned-phase P90, and
0.9976/0.9982/0.9958 for raw Doppler P90. Ambiguity-transition P90 was less
stable at 0.9476/0.9804/0.9301 and remains explanatory-only.

APE is offline trajectory context only: T0/T1/T2 RMSE was
1.1976/1.1720/1.2319 m (mean 1.2005 m, sample standard deviation 0.0301 m),
with run-dependent maxima of 4.298/3.623/4.843 m. Post-AR-success counts were
1025/909/1021; T1 had the fewest successes but the lowest RMSE. AR/FIX/FLOAT
status is therefore further excluded from all reliability/confidence mapping.

Around the common 133--134 s offline error episode, PR insufficiency was one,
eligible PR groups were zero, satellite support was only about 5--7, GDOP was
extremely poor or invalid, phase was unavailable, and PR inconsistency itself
was not extreme. This supports separating low source-assessment confidence/
sufficiency from low measurement quality. The timestamp is an offline mechanism
probe only and is prohibited from online rules.

Dataset roles are now frozen: 4.1 is development/mechanism-discovery evidence;
4.2 is inspected development/transfer evidence and is not a pristine final
hold-out. 5.2 remains only a future internal hold-out candidate.

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
- Stage 3A.0 E0/E1/E2 repeatability validation was reported PASS by the user;
  the PR/group/insufficiency/GDOP evidence was highly repeatable, while raw
  carrier-phase evidence showed material ambiguity/solver-path coupling.
- The first Stage 3A.1a compile attempt failed on an ambiguity-provenance
  return-type mismatch; the minimal correction is committed at `0a732d6`.
- The user reported that the post-fix compile passed, OFF/C0/C1/C2 completed,
  and formal Stage 3A.1a analysis completed with a PARTIAL PASS decision.
- Stage 3A.1a implementation sanity passed for phase category/ratio closure,
  zero unknown count in C0/C1/C2, the conditioned-count bound, and Doppler
  per-system count closure.
- Stage 3A.1a conditioning strongly removed extreme phase tails, but the
  hypothesis that it improves global phase-rank repeatability was not
  supported.
- Stage 3A.1b-0 semantic architecture completed DESIGN PASS.
- Stage 3A.1b-0T 4.2 T0/T1/T2 completed formal analysis with a PARTIAL PASS:
  semantic transfer/repeatability passed and evidence availability shifted.
- Stage 3A.1b-1a Structured Assessment Mathematical Contract completed design
  review and is FROZEN.
- Stage 3A.1b-1b Analytic/Empirical/Hybrid calibration comparison passed;
  Hybrid is the preferred prototype direction, not a final selection.
- Stage 3A.1b-1b.1 representation review completed DESIGN PASS WITH ONE
  MATHEMATICAL REVISION. Multivariate reference regions are not current
  channel assessments, and optional joint scalars cannot remove coordinate
  attribution.
- The final Stage 3A.1b-1b.2 semantic refinements require finite-sample/MC
  coverage tolerance, downward-closed acceptance for one-sided badness,
  upper-tail-only phase quality, two-sided Doppler-center badness with signed
  attribution, and the term occupancy rather than coverage for unlabeled real
  4.1/4.2 membership rates.
- The final Stage 3A.1b-1b.3 pre-registration removes real-data occupancy from
  transfer PASS criteria, treats empirical quantile ratios only as correction
  candidates, adds effective tail-cluster eligibility, freezes simultaneous
  max-t block-bootstrap mathematics, and marks all numeric traffic-light
  thresholds `not_runtime_parameter=true`.
- Stage 3A.1b-1b.3R corrected the transfer hierarchy without changing any
  representation, alpha, block size, bootstrap, contamination grid, tail
  threshold, synthetic model, or quality semantic. The nine repeat pairs per
  direction are nested applications, not nine independent session samples.
- The 180 and 171 corrected rows are **per-source-repeat assessment rows**;
  they are not independent rows or independent sessions.
- Current `InDomain`/`OutOfDomain` values check target support against the
  source-repeat support range only. They are **prototype support-domain
  applicability**, not complete `CalibrationApplicability`. Full applicability
  must additionally cover receiver/platform/model, covariance applicability,
  prediction-state applicability, system/frequency coverage, support regime,
  and schema/model version.
- The old PR tradeoff file sampled random epoch-state pairs within each run.
  It is now explicitly named `within_run_state_pair_incomparability`; a
  separate `same_timestamp_repeat_pair_tradeoff` metric was executed.
- Stage 3A.1b-1b.4 metadata audit found nine additional development sequence
  sessions beyond 4.1/4.2: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 4.3, and 5.1.
  All have non-empty rover/reference/ephemeris, IMU, and camera files with
  structurally valid replay tags. Their rover/IMU/camera tag durations agree
  within 0.039 s. They are distinct acquisition runs, but span only three
  collection dates and one documented receiver/platform, so they must not be
  treated as eleven independent receiver/platform validations.
- Dataset documentation identifies the common hardware as a Tersus David30
  multi-frequency receiver, Bosch BMI088 IMU, and Onsemi MT9V034 camera. This
  supports a same-platform-domain candidacy claim only. Per-sequence observed
  constellation/frequency participation and complete calibration
  applicability have not been established by this metadata audit.
- At the metadata-audit snapshot, per-sequence Stage 3A-compatible YAML existed
  for 3.1, 4.1, 4.2, and 4.3. The currently visible 3.1 YAML was subsequently
  reused for a separate DD-PR estimation/weighting rerun and must not be
  retroactively assigned to the archived shadow evidence. The user reports
  that the archived 3.1/4.3 evidence used the correct frozen shadow runtime
  configurations, but no run artifact binds those configs to the CSVs.
  Historical 2.1/2.2 YAMLs omit current Stage 3A shadow/log options and must
  not be used as-is. No per-sequence RRR YAML was found for 1.1, 1.2, 3.2,
  3.3, or 5.1 at that snapshot.
- Calibration provenance is not fully resolved. The dataset's canonical
  calibration file records GNSS lever arm `[-0.029, 0.354, -0.042]` m, while
  all inspected RRR YAMLs use `[-0.035, 0.354, -0.042]` m. The data-directory
  YAMLs and raw binary files are outside a local checksum/version manifest,
  the exact RTK reference-station provenance is not encoded in those YAMLs,
  and actual constellation/frequency participation remains unverified. Do not
  silently choose either lever arm or infer full domain applicability.

## Validation not yet performed

- Artifact-level independent verification of which Git commit produced the
  OFF/C0/C1/C2 binary; `0a732d6` is the user-reported algorithm provenance.
- Transfer beyond the already inspected 4.2 development sequence, including
  environment-stratified and future hold-out validation.
- Independent development data beyond 4.1/4.2 for calibrator selection and
  final validation; the completed Stage 3A.1b-1b.3 prototype is not final
  calibration validation.
- Independent confirmation of the corrected 3R transfer protocol beyond the
  two inspected development sequences. Dataset 5.2 remains untouched.
- Artifact-level executable/config/commit binding for the admitted 5.1 R1 run.
  Current hashes are recorded, but binary binding cannot be proven
  retrospectively.
- Full `CalibrationApplicability` across receiver/platform/model, covariance,
  prediction state, system/frequency coverage, support regime, and
  schema/model version. Stage 3A.1b-1b.4 only established metadata-level
  same-platform candidacy and prototype support-domain readiness.

Describe Stage 3A.1a as a user-run, formally analyzed PARTIAL PASS, not a full
experimental PASS or a validated reliability/weighting method.

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

The architecture under review is explicitly channel-level rather than a
permanent PR-first hierarchy:

`factor evidence -> channel calibrated assessment -> canonical S_G -> future
temporal coordination -> future channel/factor-specific factor management ->
the same single nonlinear FGO`

The GNSS channels are pseudorange, carrier phase, and Doppler. Their calibrated
assessments feed canonical structured source assessment `S_G`; mandatory
scalar or interval `(R_G,C_G)` is rejected. Any future source compression must
be task-specific and declare identifiability, calibration domain, and
information loss. It cannot replace channel state or become a uniform GNSS
factor scale. On dataset 4.1, PR population/group evidence is the currently
strongest structurally stable evidence family; this is an experiment-specific
finding, not a permanent cross-dataset source hierarchy.

Assessment validity and cross-channel agreement are separate semantics.
`AssessmentValidity` is valid, insufficient, or unavailable.
`CrossChannelState` is concordant, conflicting, or unknown. Conflicting means
that available valid channels disagree; it is not invalidity or missing data.

Candidate dependency groups are retained without assuming independence:

- PR family: PR population, PR group shift, and PR group scale;
- phase family: continuity-conditioned phase, phase-continuity coverage, and
  slip/new/mixed provenance;
- Doppler family: raw Doppler, per-system center, per-system scale, and system
  support; and
- geometry/sufficiency family: satellite support, GDOP, elevation, and
  evidence validity.

No family aggregation is approved. In particular, uncalibrated components
must not be combined with `max()`, because they do not yet share a proven
badness scale or null distribution. Source confidence must not be computed by
an unconditional `min()` across channel confidences, because an optional
channel's insufficiency must not destroy otherwise supported GNSS confidence.

Stage 3A.1b-1a freezes a typed channel-quality assessment. A scalar conformity
interval is legal only when a scalar nonconformity and total ordering are
justified. Multivariate calibrated regions and partial-order assessments retain
their native types; OutOfDomain calibration can remain `NotAssessed` even when
raw evidence is valid. `EvidenceValidity`
(Valid/Insufficient/Unavailable) and `CalibrationApplicability`
(InDomain/Partial/OutOfDomain/Unknown) are orthogonal. GDOP, elevation, and
satellite geometry are shared `S_G` context rather than duplicated in every
channel confidence record.

Satellite identity is allowed for measurement association, DD grouping and
reference bookkeeping, ambiguity continuity/slip/provenance tracking, factor
indexing, and diagnostics. PRN-specific reliability priors, blacklists,
thresholds, calibration corrections, and control laws are prohibited.

## Next research plan

Stage 3A.1b is split into explicitly separate stages and substages:

- **Stage 3A.1b-0 — Reliability Semantic Interface Shadow: DESIGN PASS.** Its
  channel, validity, confidence-component, dependency, monotonicity, conflict,
  and future common-interface semantics are frozen at design level. No generic
  runtime interface was implemented.
- **Stage 3A.1b-0T — Cross-Sequence Evidence Transfer Audit: PARTIAL PASS.**
  4.1 is development/mechanism discovery; inspected 4.2 T0/T1/T2 are transfer
  evidence and no longer pristine hold-out evidence.
- **Stage 3A.1b-1 — Reliability Mapping / Calibration: DESIGN REVIEW ONLY.**
  - **Stage 3A.1b-1a — Structured Assessment Mathematical Contract: FROZEN.**
    The canonical output is structured `S_G`; mandatory `(R_G,C_G)` is
    rejected.
  - **Stage 3A.1b-1b — Channel Calibration Protocol: DESIGN REVIEW.** The
    Analytic/Empirical/Hybrid comparison passed. Hybrid is the preferred
    prototype direction only.
  - **Stage 3A.1b-1b.1 — Channel Calibration Representation Review: DESIGN
    PASS WITH ONE MATHEMATICAL REVISION.** Current evidence, conditional
    reference regions, and current assessments are distinct objects.
  - **Stage 3A.1b-1b.2 — Offline Calibration Prototype Specification: DESIGN
    PASS WITH SEMANTIC REFINEMENTS; FROZEN.**
  - **Stage 3A.1b-1b.3 — Offline Calibration Prototype Execution: PARTIAL.**
    The frozen `validate -> audit -> synthetic-s0 -> 4.1-to-4.2 ->
    4.2-to-4.1 -> report` sequence completed without online C++, config,
    GT/APE, or 5.2 access. No final calibrator or runtime parameter was approved.
  - **Stage 3A.1b-1b.3R — Corrective Transfer Rerun: execution integrity
    PASS; scientific outcome PARTIAL.** Per-repeat source fits and 3x3
    nested-repeat target applications supersede the pooled transfer inference.
    Synthetic S0 and representation definitions were not changed.
  - **Stage 3A.1b-1b.4 — Independent-Session Calibration Panel Expansion:
    DATA ROLE / METADATA AUDIT COMPLETE; DATA-ROLE SPLIT FROZEN.** Development
    panel: 1.1--5.1 except 5.2, with sequence/date/platform clustering retained
    and 5.1 separately stratified. Untouched internal hold-out: 5.2. No new
    calibrator fitting has begun.
    - **Stage 3A.1b-1b.4b — Development Panel Evidence Sanity Audit: FULL
      PANEL FAIL; 4c HOLD.** All non-rejected complete rows have exact schema,
      timestamp ordering, PR/phase/Doppler closure, and zero evaluation
      failures. Dataset 5.1 has one truncated row in each of its three allowed
      CSVs, 27 evidence epochs without Doppler-system rows, and six preopt-only
      timestamps. The user confirmed correct frozen shadow runtime configs for
      archived 3.1/4.3 evidence, so both are `EligibleForPanel`; this provenance
      is accepted as user-reported, not artifact-bound. The currently visible
      3.1 weighting config is a later separate run. No calibration was fitted.
    - **Stage 3A.1b-1b.4b-R1 — 5.1 Rerun Admission Audit: PASS.** The new 5.1
      run has 22664 source epochs and 865838/734889/1118458 PR/Phase/Doppler
      factors. Headers and row widths are exact; timestamps are ordered and
      nonduplicated; all count/ratio/factor-summary closures are exact; all
      evaluation-failure and unexpected-nonfinite counts are zero; source and
      preopt timestamps align exactly; and the 84 source epochs without
      Doppler-system rows all have explicit zero Doppler support. The new run
      supersedes the retained old rejected artifact. Final Stage 4b panel:
      eleven Eligible, zero Partial, zero Reject.
    - **Stage 3A.1b-1b.4c-P — Multi-Session Calibration Prototype
      Pre-registration: FROZEN.** Coordinate-specific S0 construction,
      coordinate-specific primary support, full-panel versus fold tail status,
      inferential/bootstrap universe, simultaneous-CI families, contamination
      hierarchy, and distinct 5.1 weight/refit sensitivities are fixed in
      `S3A1b1b4cP-v1`. PR natural-group shift/scale and factor-level conditioned
      Phase S0 are `ApproximateMechanics`; they cannot enter normative review.
    - **Stage 3A.1b-1b.4c-E — Multi-Session Calibration Prototype:
      ExecutionIntegrity PASS; ScientificOutcome PARTIAL.** Eleven primary
      physical sequences contribute equal sequence weight; 5.1 does not gain
      primary weight from duration. PR state-pair incomparability is
      0.26287--0.50700 across sequences, supporting the frozen multivariate
      representation. Full-panel 90% support is Eligible for all 38 rows;
      95% is 36 Eligible and two PR Partial; 99% remains DiagnosticOnly.
      LOSO is structurally strong at 90/95, but date-cluster and contamination
      sensitivity prevent empirical correction promotion. SB/BW/date-balanced
      comparisons have no explicit direction reversal, although four rows
      leave the frozen [0.5,2] inner sensitivity band. The 5.1 weight/refit
      analyses also have no direction reversal; at 90%, 34 rows PASS, three
      are PARTIAL, and the high-support conditioned-Phase row FAILS the 5.1
      dominance traffic light. No final calibrator, runtime parameter, or
      normative correction was produced.

All stages remain bound by the Generalization Contract: no dataset-4.1-fitted
coefficients, event thresholds, GT/APE, route/location rules, PRN-specific
reliability priors/thresholds/control laws, or fixed weighted sum selected on
this dataset. Satellite identity remains available for required association,
grouping, continuity, indexing, and diagnostics. All evidence used by the
first solve must be available before that solve. No code, weighting,
covariance adaptation, gating, or temporal trust is authorized yet.

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
- [x] Stage 3A.0 shadow evidence implemented at `944ab6c`
- [x] Stage 3A.0 E0/E1/E2 repeatability validation reported PASS
- [x] Stage 3A.1a conditional evidence shadow implemented at `2e25400`
- [x] ambiguity-provenance result-type compile fix committed at `0a732d6`
- [x] successful Stage 3A.1a post-fix compilation reported by the user
- [x] Stage 3A.1a OFF/C0/C1/C2 runs completed
- [x] Stage 3A.1a implementation-sanity and repeatability analysis completed
- [x] Stage 3A.1a classified as PARTIAL PASS
- [x] current `git diff --check`
- [x] Stage 3A.1b-0 semantic architecture DESIGN PASS
- [x] Stage 3A.1b-0T 4.2 T0/T1/T2 formal analysis completed
- [x] Stage 3A.1b-0T classified as PARTIAL PASS
- [x] Stage 3A.1b-1a Structured Assessment Mathematical Contract FROZEN
- [x] Stage 3A.1b-1b Analytic/Empirical/Hybrid comparison accepted
- [x] Stage 3A.1b-1b.1 channel representation review completed with revision
- [x] Stage 3A.1b-1b.2 offline calibration prototype specification FROZEN
- [x] Stage 3A.1b-1b.3 offline prototype pre-registration FROZEN
- [x] Stage 3A.1b-1b.3 offline prototype execution and analysis: PARTIAL
- [x] Stage 3A.1b-1b.3R corrective execution integrity: PASS
- [x] Stage 3A.1b calibration-prototype scientific outcome retained: PARTIAL
- [x] Stage 3A.1b-1b.4 metadata-only inventory and data-role split frozen
- [x] Stage 3A.1b-1b.4b no-fit sanity/provenance/support audit executed
- [x] accept user-confirmed 3.1/4.3 frozen-shadow run provenance while retaining
  the explicit non-artifact-bound limitation
- [x] Stage 3A.1b-1b.4b-R1 new 5.1 admission: EligibleForPanel
- [x] retain old 5.1 as superseded and obtain final Stage 4b panel PASS
- [x] Stage 3A.1b-1b.4c-P multi-session prototype preregistration FROZEN
- [x] Stage 3A.1b-1b.4c-E execution integrity: PASS
- [x] Stage 3A.1b-1b.4c-E scientific outcome: PARTIAL
- [ ] environment-stratified and future hold-out validation
