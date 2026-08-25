/**
* @Function: First-solve-before GNSS source reliability evidence
*
* Copyright (C) 2026, All rights reserved.
**/
#include "gici/gnss/gnss_source_reliability.h"

#include <algorithm>
#include <cmath>
#include <map>
#include <set>
#include <string>
#include <tuple>
#include <vector>

#include "gici/estimate/estimator_types.h"
#include "gici/estimate/graph.h"
#include "gici/gnss/doppler_error.h"
#include "gici/gnss/gnss_common.h"
#include "gici/gnss/phaserange_error_dd.h"
#include "gici/gnss/pseudorange_error_dd.h"
#include "gici/utility/common.h"
#include "gici/utility/global_variable.h"

namespace gici {

namespace {

using DdPseudorangeGroupKey =
  std::tuple<char, std::string, int, int, int, int>;
using UsedSatelliteKey = std::pair<char, std::string>;

// Deterministic linear-interpolation percentile: sort x, set
// h=(n-1)*p, then interpolate between floor(h) and ceil(h).
double percentile(std::vector<double> values, const double probability)
{
  if (values.empty()) return std::numeric_limits<double>::quiet_NaN();
  std::sort(values.begin(), values.end());
  const double h = (values.size() - 1) * probability;
  const size_t lower = static_cast<size_t>(std::floor(h));
  const size_t upper = static_cast<size_t>(std::ceil(h));
  const double fraction = h - lower;
  return values[lower] + fraction * (values[upper] - values[lower]);
}

double ratioOrNan(const size_t numerator, const size_t denominator)
{
  if (denominator == 0) return std::numeric_limits<double>::quiet_NaN();
  return static_cast<double>(numerator) / static_cast<double>(denominator);
}

void setDistributionSummary(
  const std::vector<double>& values, double& p50, double& p90, double& maximum)
{
  if (values.empty()) return;
  p50 = percentile(values, 0.5);
  p90 = percentile(values, 0.9);
  maximum = *std::max_element(values.begin(), values.end());
}

void finalizePopulation(
  GnssResidualPopulationEvidence& evidence,
  const std::vector<double>& absolute_residuals)
{
  evidence.finite_success_count = absolute_residuals.size();
  evidence.evaluation_failure_count = evidence.evaluation_attempt_count -
    evidence.finite_success_count;
  if (absolute_residuals.empty()) return;

  evidence.median_abs_normalized = percentile(absolute_residuals, 0.5);
  evidence.p90_abs_normalized = percentile(absolute_residuals, 0.9);
  evidence.max_abs_normalized = *std::max_element(
    absolute_residuals.begin(), absolute_residuals.end());
  size_t count_gt3 = 0, count_gt5 = 0;
  for (const double residual : absolute_residuals) {
    if (residual > 3.0) count_gt3++;
    if (residual > 5.0) count_gt5++;
  }
  evidence.fraction_gt3 = ratioOrNan(count_gt3, absolute_residuals.size());
  evidence.fraction_gt5 = ratioOrNan(count_gt5, absolute_residuals.size());
}

void addUsedSatellite(
  const std::string& prn, std::set<UsedSatelliteKey>& used_satellites)
{
  if (prn.empty()) return;
  used_satellites.insert(std::make_pair(prn[0], prn));
}

}  // namespace

GnssSourceReliabilityEvidence computeGnssSourceReliabilityEvidence(
  const std::shared_ptr<Graph>& graph, const State& state,
  const GnssMeasurement& measurement_rov, const double gdop)
{
  GnssSourceReliabilityEvidence evidence;
  evidence.computed = true;
  evidence.timestamp = state.timestamp;
  evidence.gdop = gdop;
  // Existing computeDops paths use 100 as a failure sentinel and may return
  // zero when the receiver position is unavailable.
  evidence.gdop_valid = std::isfinite(gdop) && gdop > 0.0 && gdop != 100.0;

  std::vector<double> pseudorange_absolute_residuals;
  std::vector<double> phaserange_absolute_residuals;
  std::vector<double> doppler_absolute_residuals;
  std::map<DdPseudorangeGroupKey, std::vector<double>>
    pseudorange_group_finite_residuals;
  std::set<UsedSatelliteKey> used_satellites;

  const auto residual_blocks = graph->residuals(state.id_in_graph.asInteger());
  for (const auto& residual_block : residual_blocks) {
    if (!residual_block.error_interface_ptr) continue;
    const ErrorType type = residual_block.error_interface_ptr->typeInfo();

    GnssResidualPopulationEvidence* population = nullptr;
    std::vector<double>* absolute_residuals = nullptr;
    DdPseudorangeGroupKey pseudorange_group_key;
    bool has_pseudorange_group_key = false;

    if (type == ErrorType::kPseudorangeErrorDD) {
      population = &evidence.pseudorange;
      absolute_residuals = &pseudorange_absolute_residuals;
      const auto error = std::dynamic_pointer_cast<PseudorangeErrorDD<7, 3>>(
        residual_block.error_interface_ptr);
      if (error) {
        const GnssMeasurementDDIndexPair& index =
          error->constructionArrangedMeasurementIndex();
        const char constellation = index.rov.prn.empty() ? '\0' : index.rov.prn[0];
        pseudorange_group_key = std::make_tuple(
          constellation, index.rov_base.prn, index.rov.code_type,
          index.ref.code_type, index.rov_base.code_type,
          index.ref_base.code_type);
        pseudorange_group_finite_residuals[pseudorange_group_key];
        has_pseudorange_group_key = true;
        addUsedSatellite(index.rov.prn, used_satellites);
        addUsedSatellite(index.rov_base.prn, used_satellites);
      }
    }
    else if (type == ErrorType::kPhaserangeErrorDD) {
      population = &evidence.phaserange;
      absolute_residuals = &phaserange_absolute_residuals;
      const auto error = std::dynamic_pointer_cast<PhaserangeErrorDD<7, 3, 1, 1>>(
        residual_block.error_interface_ptr);
      if (error) {
        const GnssMeasurementDDIndexPair index = error->getGnssMeasurementIndex();
        addUsedSatellite(index.rov.prn, used_satellites);
        addUsedSatellite(index.rov_base.prn, used_satellites);
      }
    }
    else if (type == ErrorType::kDopplerError) {
      population = &evidence.doppler;
      absolute_residuals = &doppler_absolute_residuals;
      const auto error = std::dynamic_pointer_cast<DopplerError<7, 9, 3, 1>>(
        residual_block.error_interface_ptr);
      if (error) {
        const GnssMeasurementIndex index = error->getGnssMeasurementIndex();
        addUsedSatellite(index.prn, used_satellites);
      }
    }
    else {
      continue;
    }

    population->evaluation_attempt_count++;
    double normalized_residual = std::numeric_limits<double>::quiet_NaN();
    const bool evaluate_success = graph->problem()->EvaluateResidualBlock(
      residual_block.residual_block_id, false, nullptr,
      &normalized_residual, nullptr);
    if (!evaluate_success || !std::isfinite(normalized_residual)) continue;

    absolute_residuals->push_back(std::fabs(normalized_residual));
    if (has_pseudorange_group_key) {
      pseudorange_group_finite_residuals[pseudorange_group_key].push_back(
        normalized_residual);
    }
  }

  finalizePopulation(evidence.pseudorange, pseudorange_absolute_residuals);
  finalizePopulation(evidence.phaserange, phaserange_absolute_residuals);
  finalizePopulation(evidence.doppler, doppler_absolute_residuals);

  GnssDdPseudorangeGroupEvidence& groups = evidence.pseudorange_groups;
  groups.group_count = pseudorange_group_finite_residuals.size();
  groups.factor_count = evidence.pseudorange.evaluation_attempt_count;
  std::vector<double> shifts_all, shifts_eligible, scales_eligible;
  for (const auto& group : pseudorange_group_finite_residuals) {
    if (group.second.empty()) continue;

    std::vector<double> finite_residuals = group.second;
    // Match Stage 2's existing median/MAD helper for the per-group center and
    // scale. Epoch-level P50/P90 summaries use percentile() above.
    const double group_median = getMedian(finite_residuals);
    const double absolute_group_median = std::fabs(group_median);
    shifts_all.push_back(absolute_group_median);

    if (finite_residuals.size() < 4) continue;
    groups.eligible_group_count++;
    groups.eligible_factor_count += finite_residuals.size();
    shifts_eligible.push_back(absolute_group_median);

    std::vector<double> absolute_deviations;
    absolute_deviations.reserve(finite_residuals.size());
    for (const double residual : finite_residuals) {
      absolute_deviations.push_back(std::fabs(residual - group_median));
    }
    const double group_scale = std::max(
      1.0, 1.4826 * getMedian(absolute_deviations));
    scales_eligible.push_back(group_scale);
  }

  groups.insufficient_group_count = groups.group_count -
    groups.eligible_group_count;
  groups.insufficient_factor_count = groups.factor_count -
    groups.eligible_factor_count;
  groups.eligible_group_ratio = ratioOrNan(
    groups.eligible_group_count, groups.group_count);
  groups.eligible_factor_ratio = ratioOrNan(
    groups.eligible_factor_count, groups.factor_count);
  groups.insufficient_group_ratio = ratioOrNan(
    groups.insufficient_group_count, groups.group_count);
  groups.insufficient_factor_ratio = ratioOrNan(
    groups.insufficient_factor_count, groups.factor_count);
  setDistributionSummary(shifts_all, groups.shift_all_p50,
    groups.shift_all_p90, groups.shift_all_max);
  setDistributionSummary(shifts_eligible, groups.shift_eligible_p50,
    groups.shift_eligible_p90, groups.shift_eligible_max);
  setDistributionSummary(scales_eligible, groups.scale_eligible_p50,
    groups.scale_eligible_p90, groups.scale_eligible_max);

  evidence.unique_used_satellite_count = used_satellites.size();

  // Elevation is satellite-level evidence. It is published only when every
  // rover-side satellite used by current GNSS factors is available, avoiding
  // an incomplete sample population masquerading as source-wide evidence.
  std::vector<double> elevations_deg;
  for (const auto& used_satellite : used_satellites) {
    const auto satellite = measurement_rov.satellites.find(used_satellite.second);
    if (satellite == measurement_rov.satellites.end()) continue;
    const double elevation_deg = gnss_common::satelliteElevation(
      satellite->second.sat_position, measurement_rov.position) * R2D;
    if (std::isfinite(elevation_deg)) elevations_deg.push_back(elevation_deg);
  }
  evidence.elevation_sample_count = elevations_deg.size();
  evidence.elevation_valid = !used_satellites.empty() &&
    elevations_deg.size() == used_satellites.size();
  if (evidence.elevation_valid) {
    evidence.elevation_p10_deg = percentile(elevations_deg, 0.1);
    evidence.elevation_median_deg = percentile(elevations_deg, 0.5);
  }

  // SNR remains explicitly unavailable in Stage 3A.0. Input integration
  // stores Observation::SNR after a 1e-3 scale, but the upstream physical-unit
  // semantics and complete arranged-key association for all used factors have
  // not been established. Do not publish a partial source-wide population.

  return evidence;
}

}  // namespace gici
