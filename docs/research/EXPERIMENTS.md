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

Implemented at `2e25400` and statically reviewed. The first user-side compile
attempt exposed a local declaration mismatch: `inspectAmbiguityValueProvenance()`
returns `AmbiguityValueProvenanceResult`, but two callers declared the returned
objects as `AmbiguityValueProvenance`. Commit `0a732d6` applies the minimal
type-only correction. The user reported that the post-fix compile passed and
OFF/C0/C1/C2 were completed and formally analyzed.

**Decision: PARTIAL PASS.** Implementation sanity passed and conditioning has
clear semantic/decontamination value, but the hypothesis that provenance
conditioning improves global phase-rank repeatability was not supported.
Stage 3A.1b has not been implemented or experimentally entered.

The user reports that the compile and runs occurred after `0a732d6` and before
the later `04909fb` documentation commit, so the experiment's reported
algorithm-source provenance is `0a732d6`, not `04909fb`. No build artifact was
inspected during this documentation sync to independently prove the binary
commit.

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

### Implementation sanity result

- Phase category count closure was exact.
- Phase ratio closure was exact.
- `unknown_count` was zero in C0/C1/C2.
- `continuity_conditioned_count <= both_continued_count` held.
- Doppler per-system count closure was exact.
- Overall phase provenance was approximately 94.5% both-continued/no-slip,
  0.7% both-new, 1.7% mixed, 3.0% any-slip, and 0% unknown.

### Phase repeatability and tail result

Raw phase P90 pairwise Spearman was approximately 0.9938 for C0/C1, 0.9461
for C0/C2, and 0.9418 for C1/C2. Continuity-conditioned phase P90 was lower:
approximately 0.9896, 0.9169, and 0.9137, respectively. The hypothesis that
provenance conditioning improves global phase-rank repeatability is therefore
not supported, and the conditioner must not be tuned to improve 4.1
correlation.

Conditioning nevertheless strongly removed nuisance-driven extreme tails.
Raw phase P90 had a median of about 1.66, P99 about 170, and maximum about
1050 sigma; conditioned phase P90 had a median about 1.33, P99 about 3.2--3.3,
and maximum about 7 sigma. This supports semantic/decontamination value, while
conditioned phase remains state/path coupled.

### Ambiguity-transition and Doppler result

Ambiguity-transition P90 was repeatable, with Spearman approximately
0.986--0.992, but was not strongly elevated at 135/165/213/219 s. Retain it as
explanatory ambiguity-state metadata; it must not enter channel/source quality
calibration, temporal coordination, or factor control.

Doppler repeatability remained high. Raw P90 pairwise Spearman was
approximately 0.9994/0.9887/0.9887; per-system center was approximately
0.9989/0.9757/0.9761; and per-system scale was approximately
0.9998/0.9929/0.9930. There is no current evidence for a more complex nuisance
projection. Doppler-system evidence remains shadow-only.

### Offline event interpretation

- 135 s: conditioned phase was much less abnormal than raw phase; geometry/
  GDOP remained the stronger issue.
- 165 s: conditioned phase was not strongly abnormal; satellite support,
  GDOP, and insufficiency dominated.
- 213 s: phase was not abnormal; PR insufficiency remained dominant.
- 219 s: conditioned phase P90 was strongly elevated, at approximately the
  86--88 percentile, while PR group shift/scale were also high and GDOP was
  ordinary. This is the strongest current source-level GNSS degradation case.

These event times are offline mechanism probes only and must never enter
online rules. GT/APE must not be used to tune evidence or thresholds.

### Channel interpretation and next decision

On dataset 4.1, PR population/group evidence is the currently strongest
structurally stable evidence family. This result must not be generalized into
a permanent PR-primary hierarchy. The architecture under review is instead:

`factor evidence -> channel calibrated assessment -> canonical structured
source assessment S_G -> future temporal coordination -> future
channel/factor-specific factor management -> the same single nonlinear FGO`

The pseudorange, carrier-phase, and Doppler channels remain distinct. Mandatory
scalar or interval `(R_G,C_G)` is rejected. A future source-level compression
is optional and task-specific, and is allowed only with explicit
identifiability, calibration-domain, and information-loss semantics. It must
not replace the canonical channel state or become a uniform GNSS factor scale.

Candidate dependency groups are PR population/group shift/group scale; phase
conditioned inconsistency/continuity coverage/provenance; Doppler raw/per-system
center/per-system scale/system support; and geometry/sufficiency satellite
support/GDOP/elevation/evidence validity. Components within a group are not
assumed independent. Neither uncalibrated `max()` aggregation nor unconditional
`min()` source-confidence aggregation is approved.

**Stage 3A.1b-0 — Reliability Semantic Interface Shadow: DESIGN PASS.** The
channel semantics, validity/confidence separation, dependency groups,
monotonic direction, conflict semantics, and future common multisource
interface passed design review. No generic runtime interface or reliability/
confidence scalar was implemented.

## Stage 3A.1b-0T: 4.1 to 4.2 Cross-Sequence Evidence Transfer Audit

### Status and decision

The user completed and formally analyzed 4.2 T0/T1/T2 with the Stage 3A
evidence definitions frozen from 4.1. **Decision: PARTIAL PASS.** Implementation
and schema passed; cross-sequence semantic transfer passed; within-4.2
structural repeatability passed; phase-provenance transfer passed;
conditioned-phase semantic transfer passed; PR/group repeatability passed; and
Doppler transfer passed. Evidence availability showed a domain shift, so the
overall result is partial rather than a full pass.

No further 4.2 repeats are required. Dataset 4.1 remains development/mechanism-
discovery evidence. Because 4.2 results are now inspected and inform mapping
design, 4.2 is development/transfer evidence and is not a pristine final
hold-out. Dataset 5.2 remains a future internal hold-out candidate only.

### Implementation, schema, and availability

- Each run contained 2340 GNSS-evidence epochs.
- Each run contained exactly 48929 PR factors and 36898 phase factors.
- All evaluation-failure counts were zero.
- No-eligible-PR-group epochs were exactly 474/2340 (20.26%) in T0/T1/T2.
- Median PR insufficient-factor ratio was exactly 0.642857 in all runs.

The stable lack of eligible PR groups in one fifth of the epochs is a genuine
availability-domain shift. It must lower or invalidate assessment confidence;
it must not be converted into low measurement reliability.

### Phase transfer

Phase provenance was approximately 94.0% continued, 0.4--0.5% new, 2.78%
mixed, 2.70% slip, and 0% unknown. Raw phase P90 remained heavily contaminated
by extreme provenance/path tails: P99 was approximately 885--1075 sigma and
maximum approximately 1801--1812 sigma. Continuity-conditioned phase P90 had
P99 approximately 4.16--4.30 sigma and maximum approximately 14.92--14.94
sigma.

Conditioning therefore transferred semantically as a strong decontamination
step, but it again did not improve rank repeatability. It remains corroborative
evidence and remains state/path coupled.

### Structural repeatability

Pairwise T0/T1/T2 Spearman values were:

- PR P90: 0.9966 / 0.9987 / 0.9931;
- all-group PR shift P90: 0.9963 / 0.9981 / 0.9927;
- eligible-group PR shift: 0.9934 / 0.9979 / 0.9903;
- PR group scale: 0.9774 / 0.9912 / 0.9695;
- raw phase P90: 0.9882 / 0.9948 / 0.9864;
- continuity-conditioned phase P90: 0.9770 / 0.9869 / 0.9766;
- ambiguity-transition P90: 0.9476 / 0.9804 / 0.9301; and
- raw Doppler P90: 0.9976 / 0.9982 / 0.9958.

Ambiguity transition remains explanatory-only and must not enter channel or
source reliability.

### Offline trajectory and AR context

T0/T1/T2 APE RMSE was 1.1976/1.1720/1.2319 m, with mean 1.2005 m and sample
standard deviation 0.0301 m. Maximum error remained run-dependent at
4.298/3.623/4.843 m. Post-AR-success counts were 1025/909/1021; T1 had the
fewest successes but the lowest RMSE. This further supports excluding
FIX/FLOAT/AR status from all reliability/confidence mappings.

APE and AR are offline explanatory context only and are prohibited from
mapping or parameter selection.

### Offline 133--134 s mechanism probe

Around the common large-error episode, PR insufficiency was one, eligible PR
groups were zero, satellite support was about 5--7, GDOP was extremely poor or
invalid, phase was unavailable, and PR inconsistency itself was not extreme.
This supports the semantic separation between low source-assessment confidence/
sufficiency and low measurement quality. The timestamp must never enter an
online rule.

## Stage 3A.1b-1: Reliability Mapping / Calibration

### Status

**DESIGN REVIEW ONLY.** No calibration code, weighting, covariance adaptation,
gating, conflict threshold, or temporal trust is implemented. Calibration may
not use 4.1/4.2 APE, event times, route identity, PRN-specific priors/rules, or
AR/FIX/FLOAT. Satellite identity remains available for measurement
association, DD grouping/reference bookkeeping, ambiguity continuity/slip
tracking, factor indexing, and diagnostics. Because 4.2 has been inspected and
its results influence this design, it is development/transfer evidence rather
than final hold-out evidence.

### Stage 3A.1b-1a: Structured Assessment Mathematical Contract

**Status: FROZEN.** The accepted pipeline is:

`factor evidence -> channel calibrated assessment -> canonical S_G -> future
temporal coordination -> future channel/factor-specific factor management ->
the same single nonlinear FGO`

Channel quality uses a typed assessment variant: scalar conformity intervals
are allowed only when a valid scalar nonconformity and total ordering exist;
multivariate calibrated regions and partial-order assessments retain their
native mathematical types; and unsupported or out-of-domain calibration can
remain `NotAssessed`. `EvidenceValidity` (Valid/Insufficient/Unavailable) is
separate from `CalibrationApplicability`
(InDomain/Partial/OutOfDomain/Unknown). OutOfDomain does not mean insufficient
raw evidence. Geometry is shared `S_G` context rather than duplicated in every
channel confidence record.

`R_PR` is calibrated consistency between current PR observations and the
current first-solve predicted state under the declared model/domain, not a
pure pseudorange-error probability. Ambiguity transition is explanatory-only;
AR/FIX/FLOAT, GT/APE, event/route identity, and identity-specific satellite
priors or rules are forbidden calibration/control inputs. Mandatory `(R_G,C_G)`
is rejected; optional task-specific compression must declare identifiability,
domain, and information loss and cannot replace channel state or become a
uniform factor scale.

### Stage 3A.1b-1b: Channel Calibration Protocol

The Analytic/Empirical/Hybrid comparison passed design review. **Hybrid is the
preferred prototype direction, not the final calibrator selection.** The
nominal analytic layer owns measurement-model structure, covariance
normalization, dependency/support semantics, and monotonic direction. A robust
empirical layer may correct finite-support behavior, realistic model mismatch,
block/session variation, and contamination sensitivity. It may not use
GT/APE, event filtering, route-specific normalization, satellite-specific
corrections, or silently normalize large/unstable model mismatch into healthy
behavior. Datasets 4.1 and 4.2 can support prototype development only; 5.2
remains untouched internal hold-out evidence.

### Stage 3A.1b-1b.1: Channel Calibration Representation Review

**DESIGN PASS WITH ONE MATHEMATICAL REVISION.** PR and Doppler use
multivariate calibrated-region assessments with partial-order/dominance as an
auxiliary relation; phase conditionally uses a scalar conformity interval only
after a single monotone continuity-conditioned nonconformity is frozen. For a
multivariate channel, current evidence `x_c(t)`, conditional calibrated
reference region `K_{c,alpha}(Z)`, and current assessment `A_c(t)` are distinct
objects. The reference region must not be documented as the current channel
assessment, and any optional joint scalar must preserve coordinate attribution.
Nominal region coverage is a finite-sample/Monte-Carlo target, not an exact
identity: report target `1-alpha`, achieved synthetic coverage, tolerance, and
Monte-Carlo uncertainty; a conservative method may instead guarantee coverage
at least `1-alpha`. PR and Doppler one-sided badness regions must be
downward-closed, so a component-wise no-worse point cannot become low quality
merely for being atypically small. Small-residual behavior is a model/
covariance-applicability diagnostic. Phase uses an upper-tail, one-sided
conditioned-P90 assessment. Doppler quality uses absolute or calibrated
two-sided center excursion while retaining the signed center direction for
attribution. Real 4.1/4.2 rates are reference-region membership/occupancy, not
calibration coverage without an additional reference-like assumption.

### Stage 3A.1b-1b.2: Offline Calibration Prototype Specification

**DESIGN PASS WITH SEMANTIC REFINEMENTS; FROZEN.** The frozen specification
separates current evidence, nominal and empirically corrected reference
objects, and current assessments; defines fixed schemas, a controlled
synthetic nominal anchor, minimal channel prototypes, cross-session prototype
stability, criteria, and required offline inputs; and includes the final
coverage, monotonicity, phase, Doppler-center, and real-data terminology
refinements above.

### Active substage

**Stage 3A.1b-1b.3 — Offline Calibration Prototype Execution: PARTIAL.** The
pre-registration remains frozen. The final revision removes real-data occupancy from
transfer PASS criteria; treats source/nominal upper-quantile ratios only as
empirical-correction candidates; conditions every empirical tail on effective
tail-cluster support; freezes max-t simultaneous block-bootstrap mathematics,
including paired repeat comparisons and source-only candidate uncertainty; and
marks every numeric traffic-light threshold as a prototype diagnostic with
`not_runtime_parameter=true`. A ratio CI containing one has neutral/
indeterminate direction. Contamination envelopes are constructed inside each
block-bootstrap replicate before simultaneous endpoint uncertainty is formed.
The frozen `validate -> audit -> synthetic-s0 -> 4.1-to-4.2 ->
4.2-to-4.1 -> report` sequence completed using only the existing 4.1 C0/C1/C2
and 4.2 T0/T1/T2 shadow artifacts. Online C++, GICI configuration, GT/APE,
Docker/ROS/EVO, and dataset 5.2 were not used.

Input/schema validation passed. PR pairwise coordinate incomparability was
about 29.0%--31.8%; the diagnostic max-marginal-rank scalar forced an ordering
for about 90.2%--93.3% of those incomparable pairs, supporting retention of
multivariate coordinate attribution. The fixed Doppler schema observed systems
`C/E/G/R` with explicit masks and no zero filling. The fixed Fisher clipping
guard was `0.999999999999`; clipping count was zero.

Synthetic S0 passed 59/60 nominal-coverage tolerance checks and all 60
downward-closure checks. The retained miss was Phase support 14 at
`alpha=0.10`: achieved membership 0.90332 versus target 0.90 and frozen
tolerance 0.003. All physically directed perturbation checks passed. This
validates nominal mechanics only, not a real healthy-world distribution. Exact
PR natural-group and factor-level conditioned-Phase mechanics remain limited by
the available aggregate artifacts.

In 4.1-to-4.2, 60/60 nominal-mismatch ratios were strictly positive and finite;
58 tails were Eligible, one Partial, and one DiagnosticOnly, yielding 59
correction candidates and one NotAssessed. In 4.2-to-4.1, 57/57 ratios were
numerically valid; 50 tails were Eligible, four Partial, and three
DiagnosticOnly, yielding 54 candidates and three NotAssessed. The ratios remain
`nominal_mismatch_ratio` / `empirical_correction_candidate` objects only. Their
CI-direction agreement across matched ordinal support strata was about 56.6%,
which is insufficient to approve a normative empirical correction. Real-data
occupancy gaps are reported only as reference-membership/degradation outcomes.

Contamination sensitivity was material: at epsilon 0.10 the median compatible
candidate-envelope fold width was about 2.03 for 4.1-to-4.2 and 1.82 for
4.2-to-4.1; at epsilon 0.20 it was about 3.36 and 2.79. All ratio and envelope
endpoint guards were valid without epsilon insertion. The final Doppler
per-system bootstrap keeps all systems from the same timestamp in the same
10/30/60-epoch temporal block.

Three implementation defects were found and corrected before final artifacts:
a zero-variance support-1 Doppler scale coordinate was initially treated as
valid instead of unavailable; raw Doppler P90 nominal mechanics were initially
omitted; and Doppler system rows were initially blocked by row rather than
unique epoch. None changed the frozen alpha grid, draw counts, seeds,
thresholds, block sizes, bootstrap mathematics, contamination grid, or
statistics. They are recorded in the generated decision artifact. No
additional implementation deviation was recorded at that point. The later 3R
review supersedes the original `pre-registration deviation = none` claim: the
pooled repeat hierarchy was one preregistration deviation and was corrected by
the 3R execution.

Artifacts are under `output/stage3a_1b_1b_3/v1/`; the frozen manifest and tool
are `tools/research/stage3a_1b_1b_3_manifest.yaml` and
`tools/research/gnss_calibration_prototype.py`. This prototype does not select a
final calibrator, create runtime parameters, or authorize weighting, temporal
trust, or hold-out access.

### Stage 3A.1b-1b.3R: Corrective Transfer Rerun

**Corrective execution integrity: PASS. Scientific calibration-prototype
outcome: PARTIAL.** Artifact review found that the initial transfer pooled
C0/C1/C2 or T0/T1/T2 as one source block population. That contradicted the
frozen contract that these are nested repeats, not independent sessions. The
earlier `preregistration deviation = none` statement is therefore withdrawn:
the pooled repeat hierarchy was a preregistration deviation. The original
representation audit and Synthetic S0 remain valid, but original transfer
block counts, tail eligibility, simultaneous CIs, candidate directions,
applicability inference, and contamination inference are superseded.

The 3R run changed only repeat hierarchy. Each source repeat was fitted
separately, its source bootstrap drew blocks only from that repeat, and the
frozen result was applied separately to all three target repeats. Each
direction therefore has a 3x3 nested-repeat application matrix. The nine pairs
are not treated as nine independent session samples; summaries report only
median, range, and run sensitivity. No representation, alpha, block size,
bootstrap method/count, contamination grid, tail threshold, synthetic model,
seed policy, or quality semantic changed. Synthetic S0 was not rerun.

At the primary 30-epoch block size, 4.1 source repeats had 130--131 effective
blocks rather than the pooled maximum 393. The 4.2 source repeats had 62--78
effective blocks rather than the pooled maximum 234. The corrected 4.1-to-4.2
per-source-repeat assessments comprised 180 rows: 129 Eligible, 36 Partial, 12
DiagnosticOnly, and 3 NotAssessed; 165 remained correction candidates and 15
were NotAssessed. The corrected 4.2-to-4.1 per-source-repeat assessments
comprised 171 rows: 88
Eligible, 38 Partial, 36 DiagnosticOnly, and 9 NotAssessed; 126 were candidates
and 45 NotAssessed. All ratios and contamination endpoints passed the frozen
strict-positive/finite guard without epsilon insertion.

The 99% tail changed most strongly. Before correction, pooled 4.1-to-4.2 had
18/20 Eligible, 1 Partial, and 1 DiagnosticOnly; after per-repeat fitting it
had 15/60 Eligible, 30 Partial, 12 DiagnosticOnly, and 3 NotAssessed. Pooled
4.2-to-4.1 had 12/19 Eligible, 4 Partial, and 3 DiagnosticOnly; corrected 3R
had 0/57 Eligible, 15 Partial, 33 DiagnosticOnly, and 9 NotAssessed. Thus the
pooled execution materially overstated empirical 99% tail support.

Uncertainty also increased. Median simultaneous-CI fold width changed from
about 2.18 to 3.94 for 4.1-to-4.2 and from about 2.82 to 6.85 for
4.2-to-4.1. At 99%, reverse-direction median width changed from about 9.05 to
22.86. Candidate fractions changed from 0.983 to 0.917 and from 0.947 to
0.737, respectively. Nevertheless, source-repeat direction mode was unanimous
in 115/117 matched coordinate/alpha/ordinal-stratum cells. This is repeat-run
sensitivity, not independent-session validation, and it does not rescue the
insufficient tail support or approve a normative correction.

Contamination conclusions remain materially similar but are now computed per
source repeat. At epsilon 0.10, median envelope fold width across repeats was
about 2.03 for 4.1 sources and 1.82 for 4.2 sources; at epsilon 0.20 it was
about 3.34 and 2.80. Prototype support-domain applicability was recomputed for
every repeat pair and is reported by coordinate as median/range, without a
nine-sample independence claim. Current `InDomain`/`OutOfDomain` labels mean
only that target support lies inside/outside the corresponding source-repeat
support range. They do not constitute complete `CalibrationApplicability`.
Full applicability remains unresolved across receiver/platform/model,
covariance applicability, prediction-state applicability, system/frequency
coverage, support regime, and schema/model version.

The former `pr_tradeoff_incomparability.csv` values of about 29.0%--31.8%
were confirmed to be random within-run epoch-state pairs. They are retained as
`within_run_state_pair_incomparability`, supporting partial-order state-space
incomparability only. The new same-timestamp nested-repeat metric was about
0.077%--0.256% in 4.1 and 3.27%--9.75% in 4.2. It is the appropriate repeat
disagreement/tradeoff metric.

Corrective artifacts are under `output/stage3a_1b_1b_3r/v1/`, with manifest
`tools/research/stage3a_1b_1b_3r_manifest.yaml`. Dataset 5.2, GT/APE, online
C++, and GICI configuration remained untouched. Overall stays PARTIAL, no
final calibrator is selected, and no runtime parameter or control law is
authorized. The 180/171 rows are per-source-repeat assessment rows, not
independent rows.

### Stage 3A.1b-1b.4: Independent-Session Panel Metadata Audit

**Status: DATA ROLE / METADATA AUDIT COMPLETE; DATA-ROLE SPLIT FROZEN.** This
audit used only the dataset catalog, raw-stream file/tag metadata, current RRR
YAMLs, calibration metadata, and Git/config provenance. It did not read new
reliability residual outcomes, trajectory performance, GT/APE, AR/FIX results,
event-specific locations/times, or any 5.2 directory/config/outcome content.
Dataset 5.2 appears below only through the public dataset catalog and its
previously frozen hold-out role.

The catalog documents one common collection platform: Tersus David30
multi-frequency GNSS receiver, Bosch BMI088 IMU, and Onsemi MT9V034 camera.
For every inspected sequence from 1.1 through 5.1, the required RRR inputs
`gnss_rover`, `gnss_reference`, `gnss_ephemeris`, `imu`, and `camera` and their
replay tags are present and non-empty. The rover/IMU/camera tag durations agree
within 0.039 s for every sequence. Duration is the last replay-tag tick and is
therefore stream metadata, not a solution outcome.

| Sequence | Catalog coverage | Date | Tag duration | RRR input metadata | Current per-sequence RRR YAML | Frozen data role |
|---|---|---:|---:|---|---|---|
| 1.1 | open-sky, short | 2023-03-20 | 197.3 s | complete; tag structure valid | absent | development/calibration panel candidate; config required |
| 1.2 | open-sky, short | 2023-03-27 | 150.0 s | complete; tag structure valid | absent | development/calibration panel candidate; config required |
| 2.1 | tree-lined, short | 2023-03-20 | 402.0 s | complete; tag structure valid | historical; Stage 3A shadow/log fields absent | development/calibration panel candidate; do not use YAML as-is |
| 2.2 | tree-lined, short | 2023-03-27 | 180.0 s | complete; tag structure valid | historical; Stage 3A shadow/log fields absent | development/calibration panel candidate; do not use YAML as-is |
| 3.1 | typical urban, short | 2023-03-27 | 491.0 s | complete; tag structure valid | archived shadow run config user-confirmed; current visible YAML belongs to a later DD-PR weighting rerun | development/calibration panel candidate |
| 3.2 | typical urban, short | 2023-03-27 | 417.9 s | complete; tag structure valid | absent | development/calibration panel candidate; config required |
| 3.3 | typical urban, short | 2023-03-27 | 572.0 s | complete; tag structure valid | absent | development/calibration panel candidate; config required |
| 4.1 | dense urban, short | 2023-05-21 | 406.0 s | complete; tag structure valid | executed Stage 3A development config | development/mechanism; already inspected |
| 4.2 | dense urban, short | 2023-03-27 | 239.0 s | complete; tag structure valid | executed Stage 3A transfer config | development/transfer; already inspected |
| 4.3 | dense urban, short | 2023-03-27 | 475.0 s | complete; tag structure valid | archived shadow run config user-confirmed; not artifact-bound | development/calibration panel candidate |
| 5.1 | long-duration, multiple catalog scene classes | 2023-05-21 | 2389.0 s | complete; tag structure valid | absent | separately stratified long-duration development candidate; config required |
| 5.2 | long-duration | 2023-05-21 | not inspected | not inspected in this audit | not inspected | untouched internal hold-out |

The sequences are separate, non-overlapping acquisition runs according to
their replay-tag intervals. They are not repetitions of one saved session.
However, the panel has only three acquisition-date clusters (2023-03-20,
2023-03-27, and 2023-05-21) and one documented receiver/platform. Session,
date-cluster, and receiver/platform levels must therefore remain explicit in
all later resampling and uncertainty statements. The long 5.1 sequence must
not dominate the panel merely by contributing many temporal blocks.

At the frozen 30-evidence-epoch block size and the approximately 10 Hz GNSS
evidence cadence observed in 4.1/4.2, the nine added sessions provide a gross
duration-based upper estimate of about 1,754 additional full blocks: 65, 49,
134, 60, 163, 139, 190, 158, and 796 for 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3,
4.3, and 5.1 respectively. Including 4.1/4.2 gives about 1,963 gross blocks.
These are planning estimates only; initialization, missing channels, support
eligibility, masks, and schema validity will reduce channel-specific effective
support. The independent-session increment is nine, not 1,754, and the
independent receiver/platform increment is zero.

On gross support alone, 90% and 95% tails are plausible for a same-platform
prototype panel after config/provenance readiness and actual effective-support
checks. A 99% tail would have only about 20 nominal block exceedances across
the whole panel, is vulnerable to within-session dependence and domination by
5.1, and spans only three date clusters. It therefore remains
Partial/DiagnosticOnly for normative empirical calibration unless the frozen
effective-tail criteria are satisfied with support distributed across
sessions; gross block count cannot promote it to a stable calibrated tail.

The frozen development/calibration panel is 1.1, 1.2, 2.1, 2.2, 3.1, 3.2,
3.3, 4.1, 4.2, 4.3, and 5.1. Selection is based only on common-platform
provenance, distinct acquisition sessions, duration, stream completeness, and
catalog environment coverage. Leave-one-session/date-cluster-out analyses
within this panel remain development analyses; once used to design or choose a
calibrator, none of these sequences is a pristine final hold-out. Dataset 5.2
remains the untouched internal hold-out and must not be opened before the
calibrator, applicability checks, and evaluation protocol are frozen.

This audit establishes only **same-platform calibration-domain candidacy**.
It does not establish complete `CalibrationApplicability`. The RRR configs
declare Tersus raw input and exclude GLONASS (`system_exclude: [R]`), but
actual per-sequence constellation/frequency participation was not decoded in
this metadata-only pass. Receiver/platform/model, covariance applicability,
prediction-state applicability, system/frequency coverage, support regime,
and schema/model version remain required applicability dimensions.

Config/provenance blockers before panel execution are:

- generate frozen, identity-only Stage 3A configs for 1.1, 1.2, 2.1, 2.2,
  3.2, 3.3, and 5.1; the historical 2.1/2.2 YAMLs must not be reused as-is;
- record code/config hashes, input paths/dates, output isolation, and the
  unchanged Stage 3A flags before any run;
- resolve or explicitly freeze the GNSS lever-arm provenance discrepancy:
  the dataset calibration file records `[-0.029, 0.354, -0.042]` m, whereas
  every inspected RRR YAML uses `[-0.035, 0.354, -0.042]` m; no value is
  selected by this audit;
- record the applicability/provenance of the shared 2022-named DCB file and
  the exact RTK reference source/station metadata rather than inferring them
  from path names; and
- retain the current covariance/noise, IMU, camera, solver, loss, rejection,
  AR, window, and evidence definitions without outcome-driven changes.

Even after this same-platform panel is complete, claims about receiver/model
transfer, covariance-model transfer, alternative constellation/frequency
mixes, different camera/IMU prediction quality, different sensor calibration,
and external-site/platform generalization will still require cross-receiver
and external validation. Dataset 5.2 can test an internal held-out session but
cannot by itself provide those external-domain claims.

### Stage 3A.1b-1b.4b: Development Panel Evidence Sanity Audit

**Status: FULL-PANEL SANITY FAIL; STAGE 4c NOT STARTED.** The audit used the
frozen `S3A1b1b4b-v1` whitelist: source-reliability evidence, Doppler-system
evidence, preopt GNSS factor diagnostics, current configs, and raw-input
metadata/tag fingerprints. It did not read 5.2, GT/APE, solution/trajectory,
post-fit residual, rejection events, or AR/FIX/FLOAT diagnostics, and it
performed no calibration or fitting.

| Sequence | Decision | Evidence epochs per run | PR factors per run | Phase factors per run | Doppler factors per run | Reason |
|---|---|---|---|---|---|---|
| 1.1 | EligibleForPanel | 1797 | 100865 | 82981 | 143582 | structural sanity PASS; metadata-linked config |
| 1.2 | EligibleForPanel | 1446 | 55392 | 48107 | 83997 | structural sanity PASS; metadata-linked config |
| 2.1 | EligibleForPanel | 3863 | 172521 | 138669 | 226577 | structural sanity PASS; metadata-linked config |
| 2.2 | EligibleForPanel | 1618 | 52323 | 43203 | 71390 | structural sanity PASS; metadata-linked config |
| 3.1 | EligibleForPanel | 4715 | 125547 | 108033 | 186053 | correct frozen shadow runtime config confirmed by user; current DD-PR weighting config is a later separate run; provenance is not artifact-bound |
| 3.2 | EligibleForPanel | 4075 | 86000 | 71841 | 126924 | structural sanity PASS; metadata-linked config |
| 3.3 | EligibleForPanel | 5093 | 177522 | 145396 | 242574 | structural sanity PASS; metadata-linked config |
| 4.1 | EligibleForPanel | 3928/3928/3928 | 87809/87809/87809 | 71617/71617/71617 | 123037/123037/123045 | three nested repeats; prior user-reported provenance retained |
| 4.2 | EligibleForPanel | 2340/2340/2340 | 48929/48929/48929 | 36898/36898/36898 | 66111/66109/66103 | three nested repeats; prior user-reported provenance retained |
| 4.3 | EligibleForPanel | 4200 | 70197 | 60862 | 120098 | correct frozen shadow runtime config confirmed by user; provenance is not artifact-bound |
| 5.1 | Reject | 22073 complete summary rows | 845459 | 717221 | 1091682 | all three allowed CSVs end in truncated rows; 27 source epochs lack Doppler-system rows and six timestamps occur only in preopt |

Across every structurally complete run, CSV headers are identical by file
type, row widths are exact, timestamps are ordered, PR factor/group partitions
and ratios close exactly, phase provenance counts/ratios close exactly,
`conditioned_count <= both_continued_count`, Doppler per-system counts close
exactly, factor rows agree with epoch summaries, and all evaluation-failure
counts are zero. The 5.1 failures are confined to its inconsistent truncated
tail and prevent full-panel acceptance; the audit did not invent an epsilon,
silently drop the tail, or create an after-the-fact prefix rule.

Phase `unknown_count` is zero in all complete rows. Overall continued-phase
composition ranges from about 88.6% (4.3) to 98.1% (3.3); conditioned-phase
assessment availability ranges from about 89.5% in 4.2 to 99.9% in 2.2. This
is availability/provenance description only, not channel-quality calibration.

The PR coordinate masks are only `111` (population/shift/scale valid) and
`110` (scale unavailable); both already occur in 4.1/4.2. No new PR validity
mask appears. Full PR-coordinate availability ranges from 51.6% in 4.3 and
79.7% in 4.2 to 100% in 1.1/1.2/2.2. Missing scale remains a support/eligible-
group condition, not a zero-filled quality coordinate.

Actual factor-level participation is CEGR for DD pseudorange and Doppler, and
CEG for DD phase, in every inspected run. Most Doppler epoch masks were already
seen in 4.1/4.2. New but rare masks are EGR (one epoch in 3.1, one in 3.2, six
in 3.3, and six complete epochs in 5.1) and GR (14 complete 5.1 epochs). They
must remain valid-mask/subspace cases; missing systems are not filled with zero.

The 4.1/4.2 prototype support ranges are PR factors 1--42, PR groups 1--10,
eligible PR groups 0--7, phase factors and conditioned support 0--38, Doppler
factors 0--56, Doppler systems 0--4, and used satellites 3--28. The expanded
panel contains substantial higher-support regimes, especially 1.1, 2.1, 3.3,
and 5.1. These are desired support-domain expansion descriptors and do not
cause rejection. Current applicability remains prototype support-domain only,
not complete `CalibrationApplicability`.

GDOP validity is explicit. Invalid epochs use the existing finite sentinel
`gdop=100`; the final audit uses `gdop_valid` rather than treating that sentinel
as a nonfinite/schema failure. Elevation metadata is valid in every complete
summary row. Satellite/GDOP/elevation values were used only as shared support
context, never as event or trajectory labels.

All 45 allowed evidence files have recorded SHA-256 hashes, and all 55 raw RRR
inputs exist with tag hashes/metadata fingerprints. However, no run artifact
cryptographically binds the actual executable hash to an evidence directory.
The currently visible executable is only a candidate. This limitation applies
panel-wide; `MetadataLinked` and prior user-reported provenance must not be
described as artifact-verified binary provenance.

Artifacts are under `output/stage3a_1b_1b_4b/v1/`; the audit tool and frozen
manifest are `tools/research/gnss_development_panel_sanity.py` and
`tools/research/stage3a_1b_1b_4b_manifest.yaml`. Before 4c, 5.1 needs complete
mutually aligned evidence artifacts (normally a clean rerun or recovery of
complete original logs). The 3.1/4.3 user-reported frozen-shadow run
provenance is accepted for panel eligibility, while its non-artifact-bound
limitation remains explicit. This was the original 4b blocker and was resolved
by the R1 audit below without changing the structural rules.

### Stage 3A.1b-1b.4b-R1: 5.1 Rerun Admission Audit

**Decision: `5.1 = EligibleForPanel`; final Stage 4b panel = PASS.** The new
artifact under `/home/czh/Projects/gici-data/实验_raw/5.1` supersedes the old
rejected 5.1 artifact. The old aggregate audit is retained for provenance but
must not be used as calibration input. Stage 4c was not started.

The new run has 22664 source-evidence epochs, 87711 Doppler-system rows, and
2719185 preopt factor rows. PR/Phase/Doppler totals are 865838, 734889, and
1118458 and sum exactly to the preopt row count. All three files have the
frozen headers, exact row widths, ordered timestamps, no duplicate epoch or
within-epoch factor keys, no malformed/truncated rows, zero evaluation
failures, zero unexpected nonfinite values, and exact attempt/success/failure,
PR partition/ratio, phase provenance/ratio, Doppler-system, and factor-summary
closure. All share start timestamp 1684646150.1 and terminal timestamp
1684648423.9. Source and preopt timestamp sets are identical. Eighty-four
source epochs have no Doppler-system row, but every one has Doppler
attempt/success/failure/system-count `(0,0,0,0)`; no nonzero-support epoch is
missing its Doppler-system evidence. No row or epoch was filtered.

The old run had 22073 complete source rows and 33 structural/alignment failures;
R1 has 22664 rows and zero failures. Aggregate conditioned-phase availability
is 0.98550 versus 0.98606, complete PR-coordinate-mask rate is 0.97898 versus
0.97953, and CEGR Doppler-mask rate is 0.91012 versus 0.90762. Phase provenance,
support, masks, GDOP, and elevation descriptors are similarly close at
aggregate level, while the old malformed tail and endpoint disagreements are
absent. The old per-epoch CSVs are no longer present, so same-timestamp
old/new evidence repeatability is `NotAssessed`; aggregate similarity must not
be presented as a same-timestamp correlation result. This comparison is
diagnostic and is not an admission requirement.

The current config SHA-256 is
`99283f282f8ee14576f20cb970b61b3cf905b1dd00f01491fcd66205cf1b858b`;
the currently visible executable SHA-256 is
`fec7ac5f7e297f43a377cc69f0ed98636bbc6ae8883799dcaa9448867cf8742c`;
and audit HEAD is `04909fb8c7e8bca5fa5ffda7cf043b0f7ed8414a`. The filename
run token is `20260830-094329`, and the current config records GNSS lever arm
`[-0.035, 0.354, -0.042]` m. The config postdates the evidence and no run
manifest binds the executable/config/commit to the output, so **binary binding
cannot be proven retrospectively**. These are current candidate records plus
user-reported run provenance, not cryptographic run binding.

The canonical `ambiguity_resolution_options.system_exclude: [R]` applies to
ambiguity-resolution candidate selection only; it is not the GNSS-common
system filter used to form measurement factors. R1 contains 49005 R DD-PR
factors and 87620 R Doppler factors, so their presence is expected and does
not conflict with the AR exclusion. DD phase contains C/E/G counts
354752/206073/174064 and no R factor. DD phase formation requires valid,
matched rover/reference phase and code plus natural-base pairing. The allowed
artifacts do not identify the narrower upstream condition that prevented R
phase pairing; the verified result is measurement-type-specific availability,
not a config/provenance inconsistency.

R1 artifacts are under `output/stage3a_1b_1b_4b_r1/v1/`. The no-fit manifest
and offline tools are `tools/research/stage3a_1b_1b_4b_r1_manifest.yaml`,
`tools/research/gnss_development_panel_sanity.py`, and
`tools/research/gnss_5_1_rerun_admission.py`.

### Stage 3A.1b-1b.4c-P/E: Multi-Session Calibration Prototype

**Pre-registration: FROZEN (`S3A1b1b4cP-v1`). ExecutionIntegrity: PASS.
ScientificOutcome: PARTIAL.** The execution used one primary realization from
each of 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 4.1/C0, 4.2/T0, 4.3, and
5.1-R1. Primary estimation is an equal-physical-sequence development-panel
mixture across acquisition-date clusters 2023-03-20, 2023-03-27, and
2023-05-21. This `F_SB` is not a universal healthy distribution. The 30-epoch
inferential universe contains 1857 temporal blocks; trailing blocks shorter
than 15 epochs remain descriptive-only. Repeats do not add panel weight.

The final semantic freeze records exact current coordinate, primary support,
secondary context, S0 construction, nominal-quantile rule, and
`NominalReferenceFidelity`. PR population P90 and Doppler raw/per-system
center/scale statistics are `Full` only with respect to the declared
conditional-i.i.d. standardized-Gaussian S0, not real healthy-world behavior.
PR natural-group shift/scale are `ApproximateMechanics` because exact natural
DD group membership and group sizes are absent from epoch summaries. The
conditioned-Phase P90 is also `ApproximateMechanics` because factor-level
conditioning selection and shared state/path dependence cannot be reconstructed.
Approximate or unavailable S0 coordinates cannot enter normative review.

PR within-run state-pair incomparability ranges from 0.26287 to 0.50700
(median 0.29405); a scalar diagnostic forcibly orders 0.78267--0.98939 of
those incomparable pairs. This supports keeping PR population, group shift,
and group scale as a coordinate-preserving multivariate assessment. It is not
a same-timestamp repeat-disagreement result. All 15 nonempty fixed C/E/G/R
Doppler masks occur somewhere in the panel; missing systems remain invalid
slots and are never filled with zero.

Full-panel effective-tail status is:

- 90%: all 38 coordinate/support rows Eligible;
- 95%: 36 Eligible, with two PR rows Partial;
- 99%: all 38 DiagnosticOnly. Ten rows satisfy the support-only prerequisites
  for a future upgrade review, but none is upgraded because all stability and
  applicability requirements are not met.

The 90% empirical mismatch candidates remain coordinate/support dependent.
PR population ratios range 0.697--2.226, PR group-shift ratios 1.006--3.032,
and eligible-group-scale ratios 0.655--1.271. Conditioned-Phase ratios range
1.025--1.292. Doppler raw P90 ratios are 0.493--0.620, while most per-system
center/scale ratios are also below one. Under the frozen one-sided quality
contract, unexpectedly small normalized residual statistics are not called
better quality; they are covariance/model-applicability diagnostics. Real-data
membership/occupancy is descriptive and is not calibration coverage.

All LOSO 90/95 training folds are Assessable and have no explicit direction
reversal relative to the full-panel direction. Leave-date-cluster-out exposes
the smaller independent-domain base: at 90%, 113/114 rows are Assessable and
one is Partial; at 95%, 76 are Assessable, 33 Partial, and five DiagnosticOnly.
One 95% PR group-shift row has a date-fold direction reversal. Support-range
checks are reported only as `prototype_support_domain_applicability`; complete
`CalibrationApplicability` remains Unknown across receiver/platform/model,
covariance, prediction state, system/frequency, support, and schema version.

Block-weighted and equal-date-cluster sensitivity have no explicit candidate
direction reversal, but respectively three and one rows leave the frozen
`[0.5,2]` inner ratio band. Removing only 5.1 weight keeps full-panel support
boundaries and nominal reference fixed; deleting and fully refitting 5.1
rebuilds training-only strata/reference/candidates. Neither analysis has an
explicit direction reversal. At the primary 90% tail, 34/38 rows pass the
5.1 dominance heuristic, three are Partial, and the high-support conditioned
Phase row Fails because 5.1 contributes 0.79128 of its tail-containing blocks.

Contamination sensitivity remains the main blocker. At 90%, only four of 38
rows satisfy both frozen epsilon=0.10 and epsilon=0.20 combined-envelope width
heuristics; no Doppler row does. No empirical mismatch ratio is promoted:
0/114 rows are `EligibleForNormativeReview`. Besides fidelity and tail/fold
limitations, all rows retain unresolved full CalibrationApplicability, and
the current repeat panel is incomplete because 4.2 T1/T2 CSVs are no longer
available. Their repeat sensitivity is `NotAssessed` with no substitute or
rerun. The paired 4.1 repeat analysis used the frozen 30-epoch, 2000-replicate
block bootstrap, simultaneous 95% Fisher-scale CI, fixed rho clipping
`0.999999999999`, and recorded zero clipping events. Strict-positive finite
log-ratio guards added no epsilon.

Artifacts are under `output/stage3a_1b_1b_4c/v1/`; the frozen manifest and
offline-only tool are `tools/research/stage3a_1b_1b_4c_manifest.yaml` and
`tools/research/gnss_multisession_calibration.py`. No 5.2, GT/APE/EVO,
AR/FIX/FLOAT, post-fit residual, target refit, online C++, GICI configuration,
temporal trust, or factor weighting was used. The first repeat-audit output
omitted paired-bootstrap CIs; it was superseded before final reporting by a
rerun using the already frozen method and constants. No result-driven rule,
threshold, alpha, block size, bootstrap, contamination grid, or representation
change was made.

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
