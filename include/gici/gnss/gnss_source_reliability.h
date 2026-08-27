/**
* @Function: First-solve-before GNSS source reliability evidence
*
* Copyright (C) 2026, All rights reserved.
**/
#pragma once

#include <cstddef>
#include <cstdint>
#include <limits>
#include <map>
#include <memory>
#include <vector>

#include "gici/gnss/gnss_types.h"

namespace gici {

class Graph;
struct State;

// Exact phase-code SD ambiguity parameter values captured immediately after
// current-epoch ambiguity construction and before any relative-ambiguity
// connection can overwrite them with a previous value. Values are in meters.
using GnssAmbiguityInitializerMap = std::map<uint64_t, double>;

// Loss-free normalized-residual population evidence. A failed evaluation or a
// non-finite residual is counted as an evaluation failure. Empty-population
// statistics remain NaN rather than representing a healthy population.
struct GnssResidualPopulationEvidence {
  size_t evaluation_attempt_count = 0;
  size_t finite_success_count = 0;
  size_t evaluation_failure_count = 0;
  double median_abs_normalized = std::numeric_limits<double>::quiet_NaN();
  double p90_abs_normalized = std::numeric_limits<double>::quiet_NaN();
  double max_abs_normalized = std::numeric_limits<double>::quiet_NaN();
  double fraction_gt3 = std::numeric_limits<double>::quiet_NaN();
  double fraction_gt5 = std::numeric_limits<double>::quiet_NaN();
};

// DD pseudorange group evidence. Groups use constellation, the DD reference
// satellite, and the four arranged construction code types as their key.
// Eligibility requires at least four finite residuals. Eligible-factor counts
// include only finite residuals in eligible groups; all remaining inserted
// factors are explicitly insufficient.
struct GnssDdPseudorangeGroupEvidence {
  size_t group_count = 0;
  size_t eligible_group_count = 0;
  size_t insufficient_group_count = 0;
  size_t factor_count = 0;
  size_t eligible_factor_count = 0;
  size_t insufficient_factor_count = 0;
  double eligible_group_ratio = std::numeric_limits<double>::quiet_NaN();
  double eligible_factor_ratio = std::numeric_limits<double>::quiet_NaN();
  double insufficient_group_ratio = std::numeric_limits<double>::quiet_NaN();
  double insufficient_factor_ratio = std::numeric_limits<double>::quiet_NaN();

  double shift_all_p50 = std::numeric_limits<double>::quiet_NaN();
  double shift_all_p90 = std::numeric_limits<double>::quiet_NaN();
  double shift_all_max = std::numeric_limits<double>::quiet_NaN();
  double shift_eligible_p50 = std::numeric_limits<double>::quiet_NaN();
  double shift_eligible_p90 = std::numeric_limits<double>::quiet_NaN();
  double shift_eligible_max = std::numeric_limits<double>::quiet_NaN();
  double scale_eligible_p50 = std::numeric_limits<double>::quiet_NaN();
  double scale_eligible_p90 = std::numeric_limits<double>::quiet_NaN();
  double scale_eligible_max = std::numeric_limits<double>::quiet_NaN();
};

// First-solve-before DD carrier-phase provenance and the loss-free normalized
// residual population conditioned on both ambiguity values having actually
// been copied through relative-ambiguity connections, with no slip on any of
// the four observations. This is continuity-conditioned phase inconsistency,
// not pure carrier-phase measurement error or reliability.
struct GnssPhaseConditionalEvidence {
  size_t total_count = 0;
  size_t both_continued_count = 0;
  double both_continued_ratio = std::numeric_limits<double>::quiet_NaN();
  size_t both_new_count = 0;
  double both_new_ratio = std::numeric_limits<double>::quiet_NaN();
  size_t mixed_count = 0;
  double mixed_ratio = std::numeric_limits<double>::quiet_NaN();
  size_t any_slip_count = 0;
  double any_slip_ratio = std::numeric_limits<double>::quiet_NaN();
  size_t unknown_count = 0;
  double unknown_ratio = std::numeric_limits<double>::quiet_NaN();

  size_t continuity_conditioned_count = 0;
  double continuity_conditioned_median_abs_normalized =
    std::numeric_limits<double>::quiet_NaN();
  double continuity_conditioned_p90_abs_normalized =
    std::numeric_limits<double>::quiet_NaN();
  double continuity_conditioned_max_abs_normalized =
    std::numeric_limits<double>::quiet_NaN();
  double continuity_conditioned_fraction_gt3 =
    std::numeric_limits<double>::quiet_NaN();
  double continuity_conditioned_fraction_gt5 =
    std::numeric_limits<double>::quiet_NaN();
};

// Difference between the exact current phase-code SD initializer captured
// before overwrite and the previous ambiguity value reached by the actual
// relative-ambiguity connection. This unnormalized quantity is in meters and
// is ambiguity-state transition evidence only.
struct GnssAmbiguityTransitionEvidence {
  size_t count = 0;
  double median_abs_m = std::numeric_limits<double>::quiet_NaN();
  double p90_abs_m = std::numeric_limits<double>::quiet_NaN();
  double max_abs_m = std::numeric_limits<double>::quiet_NaN();
};

// Per-constellation grouping of loss-free normalized Doppler residuals. The
// center is the signed median and the scale is 1.4826*MAD without a floor.
// Since factor information can differ, these fields do not claim exact removal
// of a raw receiver-frequency common offset.
struct GnssDopplerSystemGroupEvidence {
  char system = '\0';
  size_t factor_count = 0;
  size_t finite_count = 0;
  size_t evaluation_failure_count = 0;
  double center_normalized = std::numeric_limits<double>::quiet_NaN();
  double scale_normalized = std::numeric_limits<double>::quiet_NaN();
};

// Epoch-level summaries of per-system Doppler center/dispersion evidence.
// These are frequency/velocity-conditioned Doppler evidence, not source
// reliability and not a nuisance-state projection.
struct GnssDopplerConditionalEvidence {
  size_t system_count = 0;
  size_t minimum_system_support = 0;
  double median_system_support = std::numeric_limits<double>::quiet_NaN();
  double system_center_abs_p50 = std::numeric_limits<double>::quiet_NaN();
  double system_center_abs_p90 = std::numeric_limits<double>::quiet_NaN();
  double system_center_abs_max = std::numeric_limits<double>::quiet_NaN();
  double system_scale_p50 = std::numeric_limits<double>::quiet_NaN();
  double system_scale_p90 = std::numeric_limits<double>::quiet_NaN();
  double system_scale_max = std::numeric_limits<double>::quiet_NaN();
  std::vector<GnssDopplerSystemGroupEvidence> systems;
};

// Evidence describing normalized inconsistency between the predicted
// multi-sensor state and current GNSS observations before the first solve.
// This structure deliberately contains no final reliability or confidence.
struct GnssSourceReliabilityEvidence {
  bool computed = false;
  double timestamp = std::numeric_limits<double>::quiet_NaN();
  GnssResidualPopulationEvidence pseudorange;
  GnssResidualPopulationEvidence phaserange;
  GnssResidualPopulationEvidence doppler;
  GnssDdPseudorangeGroupEvidence pseudorange_groups;
  GnssPhaseConditionalEvidence phase_conditional;
  GnssAmbiguityTransitionEvidence ambiguity_transition;
  GnssDopplerConditionalEvidence doppler_conditional;

  // Offline explanatory metadata only. It is deliberately excluded from any
  // current or future reliability/confidence rule in Stage 3A.1a because it is
  // dependent on the previous solver and ambiguity-resolution path.
  bool last_gnss_solution_status_valid = false;
  GnssSolutionStatus last_gnss_solution_status = GnssSolutionStatus::None;

  // Unique rover-side satellites actually used by current GNSS factors,
  // including DD reference satellites. The de-duplication key is
  // (constellation, PRN).
  size_t unique_used_satellite_count = 0;

  double gdop = std::numeric_limits<double>::quiet_NaN();
  bool gdop_valid = false;

  // Observation::SNR is scaled by 1e-3 during input integration. The exact
  // upstream unit/CN0 semantics and complete factor-to-arranged-observation
  // association are not yet established, so Stage 3A.0 leaves these invalid.
  size_t snr_sample_count = 0;
  bool snr_valid = false;
  double snr_p10 = std::numeric_limits<double>::quiet_NaN();
  double snr_median = std::numeric_limits<double>::quiet_NaN();

  size_t elevation_sample_count = 0;
  bool elevation_valid = false;
  double elevation_p10_deg = std::numeric_limits<double>::quiet_NaN();
  double elevation_median_deg = std::numeric_limits<double>::quiet_NaN();
};

// Read-only first-solve-before computation. Residuals are evaluated with
// apply_loss_function=false. The function does not solve, mutate Graph
// parameters, or change residual/loss ownership.
GnssSourceReliabilityEvidence computeGnssSourceReliabilityEvidence(
  const std::shared_ptr<Graph>& graph, const State& state,
  const State& last_gnss_state, const GnssMeasurement& measurement_rov,
  double gdop, const GnssAmbiguityInitializerMap& ambiguity_initializers);

}  // namespace gici
