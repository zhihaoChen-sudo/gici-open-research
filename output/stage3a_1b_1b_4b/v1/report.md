# Stage 3A.1b-1b.4b Development Panel Evidence Sanity Audit

- Overall: **FAIL**
- Calibrator fitting: **not performed**
- 5.2 / GT / APE / AR-FIX / solution inputs read: **no**

## Sequence decisions

| Sequence | Decision | Runs | Epochs per run | PR per run | Phase per run | Doppler per run | Max failures/run | Max closure/run | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1.1 | EligibleForPanel | 1 | 1797 | 100865 | 82981 | 143582 | 0 | 0 |  |
| 1.2 | EligibleForPanel | 1 | 1446 | 55392 | 48107 | 83997 | 0 | 0 |  |
| 2.1 | EligibleForPanel | 1 | 3863 | 172521 | 138669 | 226577 | 0 | 0 |  |
| 2.2 | EligibleForPanel | 1 | 1618 | 52323 | 43203 | 71390 | 0 | 0 |  |
| 3.1 | EligibleForPanel | 1 | 4715 | 125547 | 108033 | 186053 | 0 | 0 |  |
| 3.2 | EligibleForPanel | 1 | 4075 | 86000 | 71841 | 126924 | 0 | 0 |  |
| 3.3 | EligibleForPanel | 1 | 5093 | 177522 | 145396 | 242574 | 0 | 0 |  |
| 4.1 | EligibleForPanel | 3 | 3928;3928;3928 | 87809;87809;87809 | 71617;71617;71617 | 123037;123037;123045 | 0 | 0 |  |
| 4.2 | EligibleForPanel | 3 | 2340;2340;2340 | 48929;48929;48929 | 36898;36898;36898 | 66111;66109;66103 | 0 | 0 |  |
| 4.3 | EligibleForPanel | 1 | 4200 | 70197 | 60862 | 120098 | 0 | 0 |  |
| 5.1 | Reject | 1 | 22073 | 845459 | 717221 | 1091682 | 0 | 33 | source_row_width=1; doppler_row_width=1; preopt_row_width=1; factor_summary_disagreement={"doppler_system_missing_epoch": 27, "preopt_extra_timestamp": 6}; config_provenance_unbound |

## Run-level availability and shared context

| Sequence/run | PR complete mask | Phase conditioned | Doppler CEGR mask | Satellites min/median/max | GDOP valid rate/median/max | Elevation valid rate/P10 median |
|---|---:|---:|---:|---|---|---|
| 1.1/S0 | 1.0000 | 0.9972 | 1.0000 | 32/40/44 | 1.0000/1.13784037688674/1.44799022408525 | 1.0000/17.0831881530606 |
| 1.2/S0 | 1.0000 | 0.9924 | 0.9343 | 22/30/35 | 1.0000/1.613485073296605/2.29313406060793 | 1.0000/27.0934052948653 |
| 2.1/S0 | 0.9992 | 0.9964 | 0.9573 | 13/32/42 | 1.0000/1.30013288903912/4.17807629710859 | 1.0000/21.2223721352243 |
| 2.2/S0 | 1.0000 | 0.9994 | 0.9963 | 17/24/35 | 1.0000/2.043020834921565/4.13291872696502 | 1.0000/33.3276795798402 |
| 3.1/S0 | 0.9949 | 0.9949 | 0.9856 | 2/20/27 | 0.9996/2.30251073537182/11.6289346822276 | 1.0000/31.8244552534471 |
| 3.2/S0 | 0.9296 | 0.9784 | 0.9748 | 2/16/24 | 0.9948/2.581408336700795/178.078867461898 | 1.0000/37.5636872042631 |
| 3.3/S0 | 0.9857 | 0.9919 | 0.9777 | 2/24/34 | 0.9990/2.14092129920665/79.3191818225312 | 1.0000/28.9906423678871 |
| 4.1/C0 | 0.9944 | 0.9987 | 0.9277 | 9/18/27 | 1.0000/2.19243372680222/14.8491082984783 | 1.0000/35.49970435543305 |
| 4.1/C1 | 0.9944 | 0.9985 | 0.9277 | 9/18/27 | 1.0000/2.19243372786426/14.8491083032323 | 1.0000/35.4997043391255 |
| 4.1/C2 | 0.9944 | 0.9987 | 0.9290 | 9/18/27 | 1.0000/2.192433729051265/14.8491083394844 | 1.0000/35.4995643433894 |
| 4.2/T0 | 0.7974 | 0.8962 | 0.7203 | 3/14/28 | 0.9637/2.70122202621965/368.351276987089 | 1.0000/31.7077294810483 |
| 4.2/T1 | 0.7974 | 0.8949 | 0.7203 | 3/14/28 | 0.9637/2.70122202589254/368.35151807935 | 1.0000/31.7077294903832 |
| 4.2/T2 | 0.7974 | 0.8953 | 0.7203 | 3/14/28 | 0.9637/2.70122202601182/368.351131922322 | 1.0000/31.707729478998452 |
| 4.3/S0 | 0.5164 | 0.9748 | 0.9694 | 2/14/30 | 0.9876/2.99905827192429/261.163590269763 | 1.0000/15.5069966994046 |
| 5.1/S0 | 0.9790 | 0.9855 | 0.9101 | 2/26/40 | 0.9963/1.61216520626497/4964.40999854431 | 1.0000/24.828487726317 |

## Unseen valid patterns relative to 4.1/4.2

| Sequence/run | Kind | Mask | Count | Rate |
|---|---|---|---:|---:|
| 3.1/S0 | doppler_system_mask | EGR | 1 | 0.000212 |
| 3.2/S0 | doppler_system_mask | EGR | 1 | 0.000247 |
| 3.3/S0 | doppler_system_mask | EGR | 6 | 0.001183 |
| 5.1/S0 | doppler_system_mask | EGR | 6 | 0.000273 |
| 5.1/S0 | doppler_system_mask | GR | 14 | 0.000637 |

## Phase provenance composition

| Sequence/run | Continued | New | Mixed | Slip | Unknown count |
|---|---:|---:|---:|---:|---:|
| 1.1/S0 | 0.969427 | 0.002808 | 0.009219 | 0.018546 | 0 |
| 1.2/S0 | 0.979026 | 0.004261 | 0.013304 | 0.003409 | 0 |
| 2.1/S0 | 0.942287 | 0.005538 | 0.017675 | 0.034499 | 0 |
| 2.2/S0 | 0.891906 | 0.003796 | 0.033516 | 0.070782 | 0 |
| 3.1/S0 | 0.977951 | 0.003480 | 0.009414 | 0.009155 | 0 |
| 3.2/S0 | 0.949820 | 0.001810 | 0.018931 | 0.029440 | 0 |
| 3.3/S0 | 0.980667 | 0.001149 | 0.010523 | 0.007662 | 0 |
| 4.1/C0 | 0.945627 | 0.007093 | 0.017454 | 0.029825 | 0 |
| 4.1/C1 | 0.945348 | 0.007359 | 0.017468 | 0.029825 | 0 |
| 4.1/C2 | 0.945990 | 0.007107 | 0.017384 | 0.029518 | 0 |
| 4.2/T0 | 0.941135 | 0.004011 | 0.027806 | 0.027048 | 0 |
| 4.2/T1 | 0.939915 | 0.005176 | 0.027806 | 0.027102 | 0 |
| 4.2/T2 | 0.941000 | 0.004038 | 0.027888 | 0.027075 | 0 |
| 4.3/S0 | 0.886415 | 0.008166 | 0.081907 | 0.023512 | 0 |
| 5.1/S0 | 0.969365 | 0.002176 | 0.015285 | 0.013173 | 0 |

## Support outside the 4.1/4.2 prototype range

| Sequence/run | Support field | Outside count | Rate | Observed min/max | Reference min/max |
|---|---|---:|---:|---|---|
| 1.1/S0 | pr_finite_success_count | 1797 | 1.000000 | 46.0/64.0 | 1.0/42.0 |
| 1.1/S0 | pr_group_eligible_count | 1430 | 0.795771 | 4.0/9.0 | 0.0/7.0 |
| 1.1/S0 | phase_finite_success_count | 1782 | 0.991653 | 32.0/51.0 | 0.0/38.0 |
| 1.1/S0 | phase_continuity_conditioned_count | 1753 | 0.975515 | 0.0/50.0 | 0.0/38.0 |
| 1.1/S0 | doppler_finite_success_count | 1794 | 0.998331 | 55.0/96.0 | 0.0/56.0 |
| 1.1/S0 | unique_used_satellite_count | 1797 | 1.000000 | 32.0/44.0 | 3.0/28.0 |
| 1.2/S0 | pr_finite_success_count | 684 | 0.473029 | 14.0/50.0 | 1.0/42.0 |
| 1.2/S0 | phase_finite_success_count | 374 | 0.258645 | 13.0/42.0 | 0.0/38.0 |
| 1.2/S0 | phase_continuity_conditioned_count | 267 | 0.184647 | 0.0/42.0 | 0.0/38.0 |
| 1.2/S0 | doppler_finite_success_count | 917 | 0.634163 | 25.0/73.0 | 0.0/56.0 |
| 1.2/S0 | unique_used_satellite_count | 895 | 0.618949 | 22.0/35.0 | 3.0/28.0 |
| 2.1/S0 | pr_finite_success_count | 2447 | 0.633446 | 11.0/62.0 | 1.0/42.0 |
| 2.1/S0 | pr_group_eligible_count | 1081 | 0.279834 | 0.0/9.0 | 0.0/7.0 |
| 2.1/S0 | phase_finite_success_count | 2039 | 0.527828 | 5.0/51.0 | 0.0/38.0 |
| 2.1/S0 | phase_continuity_conditioned_count | 1822 | 0.471654 | 0.0/51.0 | 0.0/38.0 |
| 2.1/S0 | doppler_finite_success_count | 2224 | 0.575718 | 11.0/89.0 | 0.0/56.0 |
| 2.1/S0 | unique_used_satellite_count | 2600 | 0.673052 | 13.0/42.0 | 3.0/28.0 |
| 2.2/S0 | pr_finite_success_count | 181 | 0.111867 | 16.0/50.0 | 1.0/42.0 |
| 2.2/S0 | phase_finite_success_count | 89 | 0.055006 | 10.0/42.0 | 0.0/38.0 |
| 2.2/S0 | phase_continuity_conditioned_count | 65 | 0.040173 | 0.0/41.0 | 0.0/38.0 |
| 2.2/S0 | doppler_finite_success_count | 262 | 0.161928 | 21.0/73.0 | 0.0/56.0 |
| 2.2/S0 | unique_used_satellite_count | 317 | 0.195921 | 17.0/35.0 | 3.0/28.0 |
| 3.1/S0 | doppler_finite_success_count | 1 | 0.000212 | 0.0/57.0 | 0.0/56.0 |
| 3.1/S0 | unique_used_satellite_count | 1 | 0.000212 | 2.0/27.0 | 3.0/28.0 |
| 3.2/S0 | unique_used_satellite_count | 11 | 0.002699 | 2.0/24.0 | 3.0/28.0 |
| 3.3/S0 | pr_finite_success_count | 1008 | 0.197919 | 1.0/56.0 | 1.0/42.0 |
| 3.3/S0 | pr_group_eligible_count | 1 | 0.000196 | 0.0/8.0 | 0.0/7.0 |
| 3.3/S0 | phase_finite_success_count | 852 | 0.167288 | 0.0/48.0 | 0.0/38.0 |
| 3.3/S0 | phase_continuity_conditioned_count | 812 | 0.159435 | 0.0/48.0 | 0.0/38.0 |
| 3.3/S0 | doppler_finite_success_count | 914 | 0.179462 | 0.0/72.0 | 0.0/56.0 |
| 3.3/S0 | unique_used_satellite_count | 945 | 0.185549 | 2.0/34.0 | 3.0/28.0 |
| 4.3/S0 | pr_finite_success_count | 6 | 0.001429 | 1.0/44.0 | 1.0/42.0 |
| 4.3/S0 | phase_finite_success_count | 7 | 0.001667 | 0.0/41.0 | 0.0/38.0 |
| 4.3/S0 | phase_continuity_conditioned_count | 6 | 0.001429 | 0.0/40.0 | 0.0/38.0 |
| 4.3/S0 | doppler_finite_success_count | 19 | 0.004524 | 0.0/64.0 | 0.0/56.0 |
| 4.3/S0 | unique_used_satellite_count | 33 | 0.007857 | 2.0/30.0 | 3.0/28.0 |
| 5.1/S0 | pr_finite_success_count | 8566 | 0.388076 | 1.0/68.0 | 1.0/42.0 |
| 5.1/S0 | pr_group_eligible_count | 1573 | 0.071264 | 0.0/9.0 | 0.0/7.0 |
| 5.1/S0 | phase_finite_success_count | 7056 | 0.319667 | 0.0/61.0 | 0.0/38.0 |
| 5.1/S0 | phase_continuity_conditioned_count | 6537 | 0.296154 | 0.0/61.0 | 0.0/38.0 |
| 5.1/S0 | doppler_finite_success_count | 7893 | 0.357586 | 0.0/88.0 | 0.0/56.0 |
| 5.1/S0 | unique_used_satellite_count | 7267 | 0.329226 | 2.0/40.0 | 3.0/28.0 |

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
