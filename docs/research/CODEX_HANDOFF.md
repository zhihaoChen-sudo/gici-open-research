# Codex Handoff

This file records only the current active state. Research history and detailed
constraints remain in the other documents under `docs/research/`.

## 1. Repository state

- Branch: `exp/pseudorange-firstsolve-huber`
- HEAD: `0a732d67de9a561a9cc3dca4ddaf4b02355fc74b`
  (`fix: correct ambiguity provenance result type`)
- Worktree: not clean after preparing this handoff. The only expected
  uncommitted files are documentation updates to `CODEX_HANDOFF.md`,
  `TASK_STATUS.md`, and `EXPERIMENTS.md`; they record the current handoff and
  do not change estimator behavior.
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

The active stage is **Stage 3A.1a — Conditional GNSS Evidence Shadow**.
Stage 3A.0 completed E0/E1/E2 repeatability validation and is frozen.
Stage 3A.1a is implemented, but successful compile and runtime validation are
still pending. No final `R_G`/`C_G`, source weighting, or temporal trust has
been entered.

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
unchanged. **Compile validation after this fix is pending.**

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

1. The user recompiles in Docker.
2. If compilation still fails, apply only the smallest compile fix.
3. After a successful build, run Stage 3A.1a in this order: `OFF -> C0 -> C1
   -> C2`.

For OFF, set `estimate_gnss_source_reliability=false`. For C0/C1/C2, set it
to `true`. Keep code, binary, dataset, all other YAML fields, and solver
settings identical.

## 9. Stage 3A.1a validation targets

- Phase category count/ratio closure and unknown ratio.
- `continuity_conditioned_count <= both_continued_count`.
- Ambiguity-transition validity and units.
- Doppler per-system count closure.
- OFF/ON optimizer invariance.
- Raw-phase versus continuity-conditioned-phase repeatability.
- Provenance repeatability.
- Doppler conditioned-evidence repeatability.
- Epochs 135/165/213/219 are for offline mechanism analysis only.

APE improvement is not a Stage 3A.1a PASS criterion.

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
- Dataset-4.1-specific thresholds are prohibited.
