# Stage 3A.1b-1b.4b-R1 — 5.1 Rerun Admission Audit

## Decision

- `5.1 = EligibleForPanel`
- Final Stage 4b panel result: **PASS** (11 Eligible, 0 Partial, 0 Reject).
- Stage 4c started: **no**.
- New artifact `/home/czh/Projects/gici-data/实验_raw/5.1` supersedes the old rejected 5.1 artifact. The old
  aggregate audit remains retained and is not a calibration input.

## New-run integrity

- Source epochs: 22664; Doppler-system rows:
  87711; preopt factor rows: 2719185.
- PR/Phase/Doppler factor totals: 865838 / 734889 /
  1118458; their sum equals the preopt row count.
- Malformed/truncated rows, duplicate epoch/factor keys, evaluation failures,
  unexpected nonfinite values, and closure failures: all zero.
- All files are timestamp ordered and share start 1684646150.1
  and terminal 1684648423.9.
- Source and preopt timestamp sets are identical. All Doppler-system timestamps
  are source timestamps. The 84 source epochs without Doppler-system rows all
  have attempt/success/failure/system-count `(0,0,0,0)`; no nonzero-support
  epoch is missing a Doppler-system row.
- No row or epoch was removed or filtered.

## Old/new diagnostic comparison

- Old/new evidence epochs: 22073 / 22664.
- Old/new closure failures: 33 / 0.
- Aggregate conditioned-phase availability:
  0.9855026502967427 / 0.9860571831980233.
- Aggregate complete-PR mask rate:
  0.9789788429302768 / 0.9795270031768444.
- Aggregate CEGR Doppler-mask rate:
  0.9101174756397413 / 0.9076173604960142.
- Phase provenance, PR masks, Doppler masks, satellite support, GDOP, and
  elevation descriptors are close at aggregate level; the old malformed-tail
  and cross-file-alignment failures are absent in R1.
- The old per-epoch CSVs are no longer present, so same-timestamp evidence
  repeatability is `NotAssessed`. Aggregate similarity is not represented as a
  same-timestamp correlation result and is not needed for admission.

## Provenance boundary

- Current config: `/home/czh/Projects/gici-data/5.1/post_estimation_RTK_RRR.yaml`; SHA-256 `99283f282f8ee14576f20cb970b61b3cf905b1dd00f01491fcd66205cf1b858b`.
- Audit source HEAD: `04909fb8c7e8bca5fa5ffda7cf043b0f7ed8414a`; run commit
  binding is unproven.
- Current executable: `/home/czh/Projects/gici-open/ros_wrapper/devel/lib/gici_ros/gici_ros_main`; SHA-256
  `fec7ac5f7e297f43a377cc69f0ed98636bbc6ae8883799dcaa9448867cf8742c`.
- **binary binding cannot be proven retrospectively**. The current config also
  postdates the evidence and is accepted as user-reported run provenance, not
  as artifact-bound proof.
- Filename run token: `20260830-094329`.
- GNSS lever arm recorded by the current config: `[-0.035, 0.354, -0.042]` m.
- Stage 3A flags are frozen shadow-only; covariance/rejection and GNSS common
  values are recorded in `rerun_provenance.json`.

## GLONASS/R semantics

- `ambiguity_resolution_options.system_exclude: [R]` is loaded into
  `AmbiguityResolutionOptions` and filters ambiguity-resolution candidates. It
  is not the GNSS-common system filter used to construct PR/Phase/Doppler
  measurement factors.
- New 5.1 factor counts by system are:
  PR C/E/G/R = 386699/234017/
  196117/49005;
  Phase C/E/G/R = 354752/206073/
  174064/0;
  Doppler C/E/G/R = 512493/277299/
  241046/87620.
- Therefore R in PR/Doppler is expected and does not contradict AR exclusion.
  DD phase has stricter rover/reference phase-plus-code pairing and natural-base
  requirements; the artifact contains no R phase factor. The allowed artifacts
  do not identify which upstream R phase-validity/pairing condition failed, so
  that narrower cause remains unobserved. The verified behavior is
  measurement-type-specific availability, not a config/provenance conflict.
