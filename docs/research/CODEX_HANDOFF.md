# Codex Handoff

This file records only the current active state. Research history and detailed
constraints remain in the other documents under `docs/research/`.

## 1. Repository state

- Branch: `exp/pseudorange-firstsolve-huber`
- HEAD before the current documentation sync:
  `04909fb8c7e8bca5fa5ffda7cf043b0f7ed8414a`
  (`docs: hand off Stage 3A.1a validation state`).
- Worktree: not clean. Expected changes are the three research documents,
  offline-only tooling under `tools/research/`, and generated artifacts under
  `output/stage3a_1b_1b_*/v1/`; no estimator source, header, option, or GICI
  configuration file is modified.
- Relevant recent commits:
  - `0a732d6`: minimal Stage 3A.1a ambiguity-provenance compile fix
  - `2e25400`: Stage 3A.1a conditional GNSS reliability evidence shadow
  - `944ab6c`: Stage 3A.0 GNSS source reliability evidence shadow

## 2. Research objective

The final objective is generalizable multi-source reliability-aware
GNSS/Vision/IMU fusion. Dataset 4.1 is only a development and
mechanism-validation dataset. Online logic must not use GT, route, time, or
satellite-specific rules, and reliability used by the first solve must remain
first-solve-before while preserving a single main nonlinear optimization.
Detailed hard constraints are in
[`GENERALIZATION_CONTRACT.md`](GENERALIZATION_CONTRACT.md).

## 3. Current research stage

Stage 3A.1a is closed as a PARTIAL PASS. Stage 3A.1b-0 semantic architecture
completed DESIGN PASS. Stage 3A.1b-0T completed 4.2 T0/T1/T2 and is closed as
a PARTIAL PASS: semantic transfer and structural repeatability passed, while
evidence availability showed a domain shift. The latest completed calibration execution is
**Stage 3A.1b-1b.3 — Offline Calibration Prototype Execution**, executed under
the frozen `S3A1b1b3-v1` manifest and is classified **PARTIAL**. Validation
passed; synthetic nominal mechanics passed 59/60 frozen coverage checks; PR
multivariate attribution was supported; and dual-direction real-data analysis
did not justify promoting empirical mismatch ratios to normative corrections.
Subsequent artifact review found that the transfer pooled nested repeats.
**Stage 3A.1b-1b.3R — Corrective Transfer Rerun** is complete and remains
scientifically **PARTIAL**, while **3R corrective execution integrity is
PASS**. Each source repeat is now fitted independently and applied to the
three target repeats; the two 3x3 matrices are nested-repeat descriptors, not
independent-session samples. Original transfer inference is superseded, while
the representation audit and unchanged Synthetic S0 remain valid. The earlier
`preregistration deviation = none` claim is withdrawn and replaced by one
corrected repeat-hierarchy deviation.
The 180/171 results are per-source-repeat assessment rows, not independent
rows. Current `InDomain`/`OutOfDomain` results are prototype support-domain
applicability only; complete `CalibrationApplicability` remains unresolved
across receiver/platform/model, covariance and prediction-state applicability,
system/frequency coverage, support regime, and schema/model version.
Stage 3A.1b-1b.2 completed DESIGN PASS WITH SEMANTIC
REFINEMENTS and is FROZEN. Stage 3A.1b-1b.1 completed DESIGN PASS WITH ONE MATHEMATICAL REVISION:
for multivariate channels, current evidence `x_c(t)`, conditional reference
region `K_{c,alpha}(Z)`, and current assessment `A_c(t)` are distinct objects.
Stage 3A.1b-1a is FROZEN, and the Analytic/Empirical/Hybrid comparison accepted
Hybrid only as the preferred prototype direction, not as the final calibrator
selection. Mandatory scalar or interval `R_G`/`C_G` is rejected;
it may exist only as a future task-specific optional compression with explicit
identifiability, domain, and information-loss semantics. No online calibration
implementation, source weighting, covariance adaptation, conflict threshold,
or temporal trust has been entered.

The active stage is **Stage 3A.1b-1b.4 — Independent-Session Calibration Panel
Expansion**. Its metadata-only data-role audit is complete and the split is
frozen. Sequences 1.1--5.1 excluding 5.2 form the same-platform
development/calibration panel; 5.1 is a separately stratified long-duration
development session. Dataset 5.2 remains the untouched internal hold-out. That
metadata audit did not read reliability outcomes or 5.2; subsequent 4b/R1
sanity work used only the frozen pre-solve evidence whitelist.

Stage **3A.1b-1b.4b-R1 — 5.1 Rerun Admission Audit** completed with
`5.1 = EligibleForPanel`. The new 5.1 artifact supersedes the retained old
rejected artifact, and final Stage 4b panel status is **PASS**: eleven Eligible,
zero Partial, zero Reject. The new run has exact schema, timestamp, closure,
cross-file alignment, and nonfinite/failure sanity. No row was filtered.
Executable/config/HEAD hashes are recorded, but binary binding cannot be
proven retrospectively.

Stage **3A.1b-1b.4c-P** is now **FROZEN** under
`S3A1b1b4cP-v1`. Stage **3A.1b-1b.4c-E** completed with
**ExecutionIntegrity PASS** and **ScientificOutcome PARTIAL**. One primary
realization per physical sequence gives eleven equal-weight development
sequences in three acquisition-date clusters. Full-panel 90% support is
Eligible for all 38 rows; 95% is 36 Eligible and two PR Partial; all 99% rows
remain DiagnosticOnly. LOSO 90/95 is assessable without explicit direction
reversal, but leave-date-cluster-out is weaker and has one 95% PR group-shift
direction reversal. Contamination sensitivity is substantial: only 4/38 90%
rows pass both frozen envelope-width heuristics. No mismatch candidate was
promoted (0/114 `EligibleForNormativeReview`). PR natural-group and
factor-level conditioned-Phase S0 fidelity remains `ApproximateMechanics`, and
complete CalibrationApplicability remains Unknown. Current 4.2 T1/T2 CSVs are
unavailable, so that repeat-sensitivity portion is NotAssessed without
substitution. No 5.2 or prohibited outcome data was read.

Stage 3A.1b-1b.2 freezes finite-sample/Monte-Carlo-compatible nominal coverage
semantics, downward-closed quality regions for one-sided badness coordinates,
upper-tail-only phase quality, two-sided Doppler-center badness with signed
direction retained, and `membership/occupancy` terminology for unlabeled real
4.1/4.2 data. Synthetic nominal coverage must not be presented as a real-world
healthy-distribution claim.

## 4. Completed work

- Stage 2B factor-level DD-pseudorange weighting is complete. Its trajectory
  benefit was not repeatable, so it is retained only as a feasibility study.
- Stage 3A.0 GNSS source-evidence infrastructure is complete.
- Stage 3A.0 E0/E1/E2 repeatability passed: PR population, group shift, group
  scale, insufficiency, and GDOP evidence were stable.
- Raw phase evidence was found to have ambiguity/solver-path coupling.
- Stage 3A.1a implemented phase ambiguity provenance,
  continuity-conditioned phase inconsistency, ambiguity transition
  innovation, and per-system Doppler evidence.
- Stage 3A.1a post-fix compilation, OFF/C0/C1/C2 runs, and formal analysis were
  completed and classified PARTIAL PASS.
- Stage 3A.1b-0 semantic architecture completed DESIGN PASS.
- Stage 3A.1b-0T 4.2 T0/T1/T2 completed formal transfer analysis and was
  classified PARTIAL PASS. No more 4.2 repeats are required.
- Stage 3A.1b-1a Structured Assessment Mathematical Contract is FROZEN.
- The Stage 3A.1b-1b Analytic/Empirical/Hybrid comparison passed design
  review. Hybrid is the preferred prototype direction only.
- Stage 3A.1b-1b.1 completed DESIGN PASS WITH ONE MATHEMATICAL REVISION. A
  calibrated multivariate reference region is not itself a current channel
  assessment; coordinate attribution must survive any optional joint scalar.
- Stage 3A.1b-1b.3 executed `validate`, representation audit, synthetic S0,
  both frozen cross-session directions, and report. The result is PARTIAL; no
  final calibrator or runtime parameter was produced.
- Stage 3A.1b-1b.3R corrected pooled source repeats. At 30 epochs, per-repeat
  source blocks are 130--131 for 4.1 and 62--78 for 4.2. Corrected 99% tail
  support is substantially weaker, including zero Eligible reverse-direction
  rows. Corrective execution integrity passed; the scientific outcome remains
  PARTIAL.
- Stage 3A.1b-1b.4 inventoried nine additional development sequence sessions
  using metadata/config/provenance only. All have complete RRR input streams
  and aligned replay-tag durations, but the full panel spans only three dates
  and one documented receiver/platform. Current Stage 3A-form YAML exists for
  3.1 and 4.3; 2.1/2.2 have historical incompatible YAMLs; 1.1/1.2/3.2/3.3/5.1
  need frozen per-sequence configs before execution.
- Calibration provenance has an unresolved static conflict: the dataset
  calibration file gives GNSS lever arm `[-0.029, 0.354, -0.042]` m, while
  inspected RRR YAMLs use `[-0.035, 0.354, -0.042]` m. Do not silently change
  or choose either value.

## 5. Latest compile issue and fix

The first Stage 3A.1a compile attempt found that
`inspectAmbiguityValueProvenance()` returns
`AmbiguityValueProvenanceResult`, while `target` and `base` had incorrectly
been declared as `AmbiguityValueProvenance`. Commit `0a732d6` applies only this
minimal static-type correction:

```cpp
const AmbiguityValueProvenanceResult target =
  inspectAmbiguityValueProvenance(...);
const AmbiguityValueProvenanceResult base =
  inspectAmbiguityValueProvenance(...);
```

The provenance classification semantics and all estimator mathematics are
unchanged. The user subsequently reported successful post-fix compilation and
completed Stage 3A.1a and 3A.1b-0T runs. The repository history alone does not
independently prove the experiment binary-to-commit association.

## 6. Stage 3A.1a implementation invariants

- Shadow evidence only; no `R_G`/`C_G`, weighting, covariance adaptation, or
  temporal trust.
- No residual, Jacobian, information, loss, rejection, AR, solver, or
  marginalization changes.
- No Vision, IMU, or Motion changes.
- All evidence is available before the first `optimize()` and residuals are
  read with `EvaluateResidualBlock(..., false, ...)`.
- No GT/EVO/APE and no route, time, location, or satellite-blacklist logic.

## 7. Current configuration

For a Stage 3A.1a ON shadow run, use these exact YAML locations and values:

```yaml
estimate:
- estimator:
    log_intermediate_data: true
    rtk_imu_camera_rrr_options:
      use_cauchy_loss_for_dd_pseudorange: false
      estimate_reliability_for_dd_pseudorange: false
      apply_reliability_weight_for_dd_pseudorange: false
      estimate_gnss_source_reliability: true
```

`log_intermediate_data` is directly under `estimate[].estimator`; the four
research flags are under
`estimate[].estimator.rtk_imu_camera_rrr_options`. Tracked RRR example YAMLs
retain `estimate_gnss_source_reliability: false` by default, so the ON value is
an experiment override, not a changed repository default.

## 8. Immediate next action

Stop after reporting the completed 4c-E prototype and wait for scientific
review. The accepted panel provenance remains partly user-reported rather than
artifact-bound. Do not promote empirical ratios to normative corrections,
implement online mapping/control, enter temporal trust/factor weighting, or
read 5.2. The immediate unresolved issues are date-cluster diversity,
contamination sensitivity, complete CalibrationApplicability, exact PR/Phase
S0 fidelity, and missing 4.2 repeat artifacts—not a request to tune the frozen
evidence definitions or prototype thresholds.

## 9. Current experimental interpretation

- 4.1 is development/mechanism-discovery evidence.
- Inspected 4.2 is development/transfer evidence, not a pristine hold-out.
- 5.2 remains only a future internal hold-out candidate.
- The development/calibration panel is 1.1--5.1 excluding 5.2. This provides
  eleven sequence sessions but only three date clusters and one documented
  receiver/platform; sequence count must not be presented as independent
  receiver/platform support.
- Stage 3A.1b-1b.4c-E is a PARTIAL calibration prototype, not a final
  calibrator. Its equal-sequence `F_SB` is a development-panel estimand rather
  than a universal healthy distribution, real-data occupancy is descriptive,
  and empirical mismatch ratios remain candidates only.
- PR multivariate representation remains justified: within-run state-pair
  incomparability spans 26.287%--50.700% across the panel. Conditioned Phase
  remains state/path coupled, and unexpectedly small Doppler normalized
  statistics remain model/covariance applicability diagnostics rather than
  automatic evidence of high quality.
- Stage 3A.1b-0T implementation/schema and semantic transfer passed.
- 4.2 had a stable availability-domain shift: 474/2340 epochs had no eligible
  PR group, and median PR insufficient-factor ratio was 0.642857.
- Continuity conditioning again removed extreme phase tails but did not
  improve rank repeatability; conditioned phase remains corroborative.
- Ambiguity transition remains explanatory-only.
- AR/FIX/FLOAT and APE are offline context only and cannot enter mapping.
- The 133--134 s 4.2 episode is an offline mechanism probe only: low support,
  poor/invalid geometry, and unavailable phase demonstrate low assessment
  confidence without extreme PR inconsistency.

## 10. Known scientific cautions

- A pre-opt residual is inconsistency between the predicted multi-sensor state
  and an observation, not pure measurement error.
- Raw phase residuals are strongly coupled to ambiguity state.
- A both-new phase residual is not pure phase quality.
- Previous FIX/FLOAT status is offline explanatory metadata only and must not
  enter reliability.
- Subtracting a normalized Doppler center cannot be claimed to exactly remove
  a raw receiver-frequency offset.
- Evidence insufficiency does not mean healthy.
- Evidence insufficiency also does not mean bad; it lowers or invalidates
  assessment confidence rather than directly lowering measurement quality.
- Dataset-4.1-specific thresholds are prohibited.
- Dataset-4.2-specific mapping, event thresholds, or noise-model tuning are
  prohibited.
- Satellite identity remains allowed for measurement association, DD
  grouping/reference bookkeeping, ambiguity continuity/provenance, factor
  indexing, and diagnostics. PRN-specific reliability priors, blacklists,
  thresholds, calibration corrections, and control laws remain prohibited.
