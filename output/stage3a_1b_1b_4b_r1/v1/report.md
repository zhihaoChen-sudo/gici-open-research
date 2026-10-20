# Stage 3A.1b-1b.4b Development Panel Evidence Sanity Audit

- Overall: **PASS**
- Calibrator fitting: **not performed**
- 5.2 / GT / APE / AR-FIX / solution inputs read: **no**

## Sequence decisions

| Sequence | Decision | Runs | Epochs per run | PR per run | Phase per run | Doppler per run | Max failures/run | Max closure/run | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 4.1 | EligibleForPanel | 3 | 3928;3928;3928 | 87809;87809;87809 | 71617;71617;71617 | 123037;123037;123045 | 0 | 0 |  |
| 4.2 | EligibleForPanel | 3 | 2340;2340;2340 | 48929;48929;48929 | 36898;36898;36898 | 66111;66109;66103 | 0 | 0 |  |
| 5.1 | EligibleForPanel | 1 | 22664 | 865838 | 734889 | 1118458 | 0 | 0 |  |

## Run-level availability and shared context

| Sequence/run | PR complete mask | Phase conditioned | Doppler CEGR mask | Satellites min/median/max | GDOP valid rate/median/max | Elevation valid rate/P10 median |
|---|---:|---:|---:|---|---|---|
| 4.1/C0 | 0.9944 | 0.9987 | 0.9277 | 9/18/27 | 1.0000/2.19243372680222/14.8491082984783 | 1.0000/35.49970435543305 |
| 4.1/C1 | 0.9944 | 0.9985 | 0.9277 | 9/18/27 | 1.0000/2.19243372786426/14.8491083032323 | 1.0000/35.4997043391255 |
| 4.1/C2 | 0.9944 | 0.9987 | 0.9290 | 9/18/27 | 1.0000/2.192433729051265/14.8491083394844 | 1.0000/35.4995643433894 |
| 4.2/T0 | 0.7974 | 0.8962 | 0.7203 | 3/14/28 | 0.9637/2.70122202621965/368.351276987089 | 1.0000/31.7077294810483 |
| 4.2/T1 | 0.7974 | 0.8949 | 0.7203 | 3/14/28 | 0.9637/2.70122202589254/368.35151807935 | 1.0000/31.7077294903832 |
| 4.2/T2 | 0.7974 | 0.8953 | 0.7203 | 3/14/28 | 0.9637/2.70122202601182/368.351131922322 | 1.0000/31.707729478998452 |
| 5.1/R1 | 0.9795 | 0.9861 | 0.9076 | 2/26/40 | 0.9964/1.609447666988515/4964.41034482893 | 1.0000/24.84641306875065 |

## Unseen valid patterns relative to 4.1/4.2

| Sequence/run | Kind | Mask | Count | Rate |
|---|---|---|---:|---:|
| 5.1/R1 | doppler_system_mask | EGR | 6 | 0.000266 |
| 5.1/R1 | doppler_system_mask | GR | 14 | 0.000620 |

## Phase provenance composition

| Sequence/run | Continued | New | Mixed | Slip | Unknown count |
|---|---:|---:|---:|---:|---:|
| 4.1/C0 | 0.945627 | 0.007093 | 0.017454 | 0.029825 | 0 |
| 4.1/C1 | 0.945348 | 0.007359 | 0.017468 | 0.029825 | 0 |
| 4.1/C2 | 0.945990 | 0.007107 | 0.017384 | 0.029518 | 0 |
| 4.2/T0 | 0.941135 | 0.004011 | 0.027806 | 0.027048 | 0 |
| 4.2/T1 | 0.939915 | 0.005176 | 0.027806 | 0.027102 | 0 |
| 4.2/T2 | 0.941000 | 0.004038 | 0.027888 | 0.027075 | 0 |
| 5.1/R1 | 0.968974 | 0.002106 | 0.015669 | 0.013251 | 0 |

## Support outside the 4.1/4.2 prototype range

| Sequence/run | Support field | Outside count | Rate | Observed min/max | Reference min/max |
|---|---|---:|---:|---|---|
| 5.1/R1 | pr_finite_success_count | 8597 | 0.379324 | 1.0/68.0 | 1.0/42.0 |
| 5.1/R1 | pr_group_eligible_count | 1573 | 0.069405 | 0.0/9.0 | 0.0/7.0 |
| 5.1/R1 | phase_finite_success_count | 7071 | 0.311993 | 0.0/61.0 | 0.0/38.0 |
| 5.1/R1 | phase_continuity_conditioned_count | 6538 | 0.288475 | 0.0/61.0 | 0.0/38.0 |
| 5.1/R1 | doppler_finite_success_count | 7980 | 0.352100 | 0.0/88.0 | 0.0/56.0 |
| 5.1/R1 | unique_used_satellite_count | 7283 | 0.321347 | 2.0/40.0 | 3.0/28.0 |

## 4.1/4.2 prototype support ranges

- `pr_finite_success_count`: 1.0 -- 42.0
- `pr_group_count`: 1.0 -- 10.0
- `pr_group_eligible_count`: 0.0 -- 7.0
- `phase_finite_success_count`: 0.0 -- 38.0
- `phase_continuity_conditioned_count`: 0.0 -- 38.0
- `doppler_finite_success_count`: 0.0 -- 56.0
- `doppler_system_count`: 0.0 -- 4.0
- `unique_used_satellite_count`: 3.0 -- 28.0

## Provenance boundary

The evidence CSVs and current configs are hashed, and raw inputs have metadata/tag fingerprints. No run artifact binds an executable hash to an evidence directory, so binary provenance remains unverified. A current config that postdates an output is not treated as proof of the run config.

Support-range and unseen-mask results are prototype support-domain descriptors only. They neither measure complete CalibrationApplicability nor trigger quality rejection.
