/**
* @Function: First-solve-before GNSS source reliability evidence
*
* Copyright (C) 2026, All rights reserved.
**/
#pragma once

#include <cstddef>
#include <limits>
#include <memory>

namespace gici {

class Graph;
struct GnssMeasurement;
struct State;

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
  const GnssMeasurement& measurement_rov, double gdop);

}  // namespace gici
