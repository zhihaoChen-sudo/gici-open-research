# Stage 3A.1b-1b.4c-E Multi-Session Calibration Prototype

- ExecutionIntegrity: **PASS**
- ScientificOutcome: **PARTIAL**
- Primary physical sequences: 11
- Acquisition-date clusters: 3
- Correction rows eligible for normative review: 0/114
- 99% rows meeting support-only upgrade prerequisites: 10/38; all remain DiagnosticOnly pending all stability criteria.
- F_SB is an equal-sequence development-panel estimand, not a universal healthy distribution.
- Real-data occupancy is an outcome descriptor, not calibration coverage or a transfer correctness target.
- No empirical mismatch ratio was promoted to a normative correction.

## Nominal-reference fidelity

- Full: 4 base coordinates
- ApproximateMechanics: 3 base coordinates

## Tail status

- Doppler alpha=0.01 DiagnosticOnly: 27 rows
- Doppler alpha=0.05 Eligible: 27 rows
- Doppler alpha=0.1 Eligible: 27 rows
- PR alpha=0.01 DiagnosticOnly: 8 rows
- PR alpha=0.05 Eligible: 6 rows
- PR alpha=0.05 Partial: 2 rows
- PR alpha=0.1 Eligible: 8 rows
- Phase alpha=0.01 DiagnosticOnly: 3 rows
- Phase alpha=0.05 Eligible: 3 rows
- Phase alpha=0.1 Eligible: 3 rows

## Repeat sensitivity

- Available repeat artifacts: 4/6
- Computed nested-repeat coordinate rows: 39
- Missing repeat artifacts were left NotAssessed; no substitution was made.

## Boundaries

- 5.1 weight influence freezes full-panel support boundaries and S0 reference, then removes only 5.1 sequence weight.
- 5.1 refit influence removes 5.1 and rebuilds training support strata/reference/candidate.
- LOSO/LDO rebuild training-only boundaries and apply frozen candidates to targets without target refit.
- Full CalibrationApplicability remains unresolved beyond prototype support-domain applicability.
- 5.2, GT/APE, AR/FIX, online C++, temporal trust, and factor weighting were not used.
