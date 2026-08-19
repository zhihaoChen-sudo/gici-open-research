# RRR / Robust GNSS Fusion Research Plan

## Overall objective

Improve robustness of RTK/IMU/Camera tightly-coupled positioning in
challenging GNSS environments.

## Research principle

Diagnose first.
Modify the algorithm only after the failure mechanism is supported by
evidence.

---

## Stage 1 - Baseline reproduction

Goal:

Establish reproducible baseline behavior of the original estimator.

Record:

- dataset
- configuration
- positioning accuracy
- RTK fix rate
- ambiguity behavior
- GNSS residual statistics
- runtime behavior

---

## Stage 2 - Diagnostics

Investigate:

- pre-optimization GNSS residuals
- post-fit GNSS residuals
- normalized residuals
- robust loss behavior
- Doppler consistency
- ambiguity fixing
- ambiguity unfix/reset
- GNSS observation quality
- optimization timing

No algorithm changes in this stage unless necessary for instrumentation.

---

## Stage 3 - Failure mechanism analysis

Determine whether degradation is primarily caused by:

- incorrect GNSS weighting
- outliers
- robust loss interaction
- ambiguity contamination
- delayed fault detection
- Doppler inconsistency
- poor observation geometry
- RRR trigger behavior
- interaction between GNSS and IMU/camera factors

---

## Stage 4 - Algorithm design

Potential directions:

- adaptive GNSS weighting
- residual-based variance scaling
- observation-quality-aware weighting
- robust loss adaptation
- ambiguity protection
- RRR trigger redesign

Every algorithm modification must have a corresponding hypothesis.

---

## Stage 5 - Controlled experiments

Compare:

1. original baseline
2. diagnostics-only version
3. individual algorithm modifications
4. combined method

Avoid changing multiple mechanisms simultaneously unless individual
effects have already been established.

---

## Stage 6 - Evaluation

Evaluate:

- position RMSE
- position maximum error
- fix rate
- ambiguity recovery behavior
- continuity
- convergence/recovery time
- GNSS residual distributions
- robustness under degraded observations
- computational cost
