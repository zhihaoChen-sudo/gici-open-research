# Current Task Status

Last updated: 2026-08-19

## Current objective

Improve diagnostics for the RTK/IMU/Camera RRR estimator in order to
understand abnormal GNSS residual behavior, robust loss behavior,
ambiguity fixing/unfixing behavior, and the causes of RRR-related
performance degradation.

The current phase is diagnostics first.

Do not modify estimator behavior unless explicitly requested.

---

## Completed work

### GNSS factor-level residual diagnostics

Implemented GNSS factor-level diagnostics around optimization.

Existing diagnostics include information related to:

- GNSS residual blocks
- raw residuals
- normalized residuals
- sigma
- robust loss
- loss type
- loss delta
- rho0
- rho1
- rho2

Pre-opt and post-fit diagnostics share the same residual enumeration
and observation lookup logic where possible.

### Current modified files

Known modified files include:

- `include/gici/gnss/gnss_estimator_base.h`
- `src/gnss/gnss_estimator_base_logger.cpp`
- `include/gici/fusion/rtk_imu_camera_rrr_estimator.h`
- `src/fusion/rtk_imu_camera_rrr_estimator.cpp`

### Validation performed

- implementation performed
- `git diff --check` passed

### Validation NOT yet performed

- compilation
- runtime execution
- dataset validation
- numerical result validation

Do not describe the current implementation as compiled or tested.

---

## Current work in progress

Additional diagnostics are being added around RRR and ambiguity behavior.

Important quantities include:

- Doppler trigger/rejection behavior
- ambiguity resolution attempts
- post-AR solution status
- post-AR success/failure
- RRR ambiguity unfix/reset events

---

## Hard constraints

1. Diagnostics only unless explicitly instructed otherwise.
2. Do not change estimator behavior.
3. Logging must not mutate optimization state.
4. Reuse existing GNSS residual enumeration.
5. Reuse safe observation lookup logic.
6. Keep pre-opt and post-fit definitions consistent.
7. Clearly distinguish robust-loss residual quantities.
8. Do not claim compilation or runtime testing unless actually performed.

---

## Important previous lessons

### Lesson 1

Do not mix implementation status with validation status.

For example:

`git diff --check` passing does NOT mean the code compiles.

### Lesson 2

Do not introduce a second independent residual enumeration path unless
there is a strong technical reason.

Different enumeration logic can make pre-opt/post-fit diagnostics
incomparable.

### Lesson 3

Diagnostic logging should not alter the algorithm simply to make
logging easier.

---

## Next step

Before making further changes:

1. inspect current `git status`
2. inspect full `git diff`
3. reconcile the implementation with this document
4. determine exactly which requested diagnostic fields remain incomplete
5. continue only from the confirmed repository state

---

## Completion checklist

- [ ] all requested diagnostic fields implemented
- [ ] `git diff --check`
- [ ] compilation
- [ ] runtime execution
- [ ] diagnostic CSV inspection
- [ ] numerical sanity check
- [ ] dataset comparison
- [ ] experimental conclusions
