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

Status: implementation complete at `f5edd11`. A repaired GNSS diagnostic CSV
must still be runtime-revalidated before factor-level values from that repair
are used as experimental evidence.

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

Current handoff hypothesis: persistent DD-pseudorange gross inconsistency can
enter the first nonlinear solve. The already recorded first candidate is a
DD-pseudorange-only redescending robust loss; it is not implemented or
validated. Keep carrier phase, Doppler, Vision, IMU, Motion, and the AR
pipeline unchanged for the first controlled comparison.

Potential directions:

- adaptive GNSS weighting
- residual-based variance scaling
- observation-quality-aware weighting
- robust loss adaptation
- ambiguity protection
- RRR trigger redesign

Every algorithm modification must have a corresponding hypothesis.
Do not redesign the research direction or introduce additional algorithms
until the controlled result for the recorded candidate is available.

---

## Stage 5 - Controlled experiments

Next experiment sequence:

1. compile and run the committed diagnostics baseline;
2. validate repaired GNSS CSV field counts, residual pairing, loss fields, and
   timing with one unchanged baseline configuration;
3. use that configuration as the comparator for the single recorded candidate;
4. analyze position, residual, rejection, AR, and timing outcomes before any
   further design decision.

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
