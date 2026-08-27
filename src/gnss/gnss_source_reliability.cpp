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

enum class AmbiguityValueProvenance {
  New,
  Continued,
  Unknown
};

struct AmbiguityValueProvenanceResult {
  AmbiguityValueProvenance provenance = AmbiguityValueProvenance::Unknown;
  double initializer = std::numeric_limits<double>::quiet_NaN();
  double previous_value = std::numeric_limits<double>::quiet_NaN();
};

enum class PhaseFactorProvenance {
  BothContinuedNoSlip,
  BothNew,
  TargetContinuedBaseNew,
  TargetNewBaseContinued,
  AnySlip,
  Unknown
};

struct DopplerSystemAccumulator {
  size_t factor_count = 0;
  std::vector<double> finite_normalized_residuals;
};

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

AmbiguityValueProvenanceResult inspectAmbiguityValueProvenance(
  const std::shared_ptr<Graph>& graph, const uint64_t ambiguity_id,
  const GnssAmbiguityInitializerMap& ambiguity_initializers)
{
  AmbiguityValueProvenanceResult result;
  const auto initializer = ambiguity_initializers.find(ambiguity_id);
  if (initializer == ambiguity_initializers.end() ||
      !std::isfinite(initializer->second) ||
      !graph->parameterBlockExists(ambiguity_id)) {
    return result;
  }
  result.initializer = initializer->second;

  const auto current_parameter = graph->parameterBlockPtr(ambiguity_id);
  if (!current_parameter || current_parameter->dimension() != 1) return result;
  const double current_value = current_parameter->parameters()[0];
  if (!std::isfinite(current_value)) return result;

  std::set<uint64_t> connected_ambiguity_ids;
  for (const auto& residual : graph->residuals(ambiguity_id)) {
    if (!residual.error_interface_ptr ||
        residual.error_interface_ptr->typeInfo() !=
          ErrorType::kRelativeAmbiguityError) {
      continue;
    }
    const auto parameters = graph->parameters(residual.residual_block_id);
    if (parameters.size() != 2) return result;
    for (const auto& parameter : parameters) {
      if (parameter.first != ambiguity_id &&
          BackendId(parameter.first).type() == IdType::gAmbiguity) {
        connected_ambiguity_ids.insert(parameter.first);
      }
    }
  }

  if (connected_ambiguity_ids.empty()) {
    // The current value has remained exactly at the captured construction
    // initializer, and no relative ambiguity connection can have overwritten
    // it. This is the actual value provenance used by the first solve.
    if (current_value == result.initializer) {
      result.provenance = AmbiguityValueProvenance::New;
    }
    return result;
  }
  if (connected_ambiguity_ids.size() != 1) return result;

  const uint64_t previous_id = *connected_ambiguity_ids.begin();
  if (!graph->parameterBlockExists(previous_id)) return result;
  const auto previous_parameter = graph->parameterBlockPtr(previous_id);
  if (!previous_parameter || previous_parameter->dimension() != 1) return result;
  result.previous_value = previous_parameter->parameters()[0];
  if (!std::isfinite(result.previous_value)) return result;

  // addRelativeAmbiguityResidualBlock() copies the previous value into the
  // current parameter. Require that exact copied value as well as the actual
  // relative connection; a matching ambiguity identity alone is insufficient.
  if (current_value == result.previous_value) {
    result.provenance = AmbiguityValueProvenance::Continued;
  }
  return result;
}

PhaseFactorProvenance classifyPhaseFactorProvenance(
  const std::shared_ptr<Graph>& graph,
  const Graph::ResidualBlockSpec& residual_block,
  const std::shared_ptr<PhaserangeErrorDD<7, 3, 1, 1>>& error,
  const GnssAmbiguityInitializerMap& ambiguity_initializers)
{
  if (!error) return PhaseFactorProvenance::Unknown;
  if (error->hasAnyConstructionObservationSlip()) {
    return PhaseFactorProvenance::AnySlip;
  }

  const auto parameters = graph->parameters(residual_block.residual_block_id);
  if (parameters.size() != 4 ||
      BackendId(parameters[2].first).type() != IdType::gAmbiguity ||
      BackendId(parameters[3].first).type() != IdType::gAmbiguity) {
    return PhaseFactorProvenance::Unknown;
  }

  const AmbiguityValueProvenanceResult target = inspectAmbiguityValueProvenance(
    graph, parameters[2].first, ambiguity_initializers);
  const AmbiguityValueProvenanceResult base = inspectAmbiguityValueProvenance(
    graph, parameters[3].first, ambiguity_initializers);
  if (target.provenance == AmbiguityValueProvenance::Continued &&
      base.provenance == AmbiguityValueProvenance::Continued) {
    return PhaseFactorProvenance::BothContinuedNoSlip;
  }
  if (target.provenance == AmbiguityValueProvenance::New &&
      base.provenance == AmbiguityValueProvenance::New) {
    return PhaseFactorProvenance::BothNew;
  }
  if (target.provenance == AmbiguityValueProvenance::Continued &&
      base.provenance == AmbiguityValueProvenance::New) {
    return PhaseFactorProvenance::TargetContinuedBaseNew;
  }
  if (target.provenance == AmbiguityValueProvenance::New &&
      base.provenance == AmbiguityValueProvenance::Continued) {
    return PhaseFactorProvenance::TargetNewBaseContinued;
  }
  return PhaseFactorProvenance::Unknown;
}

}  // namespace

GnssSourceReliabilityEvidence computeGnssSourceReliabilityEvidence(
  const std::shared_ptr<Graph>& graph, const State& state,
  const State& last_gnss_state, const GnssMeasurement& measurement_rov,
  const double gdop,
  const GnssAmbiguityInitializerMap& ambiguity_initializers)
{
  GnssSourceReliabilityEvidence evidence;
  evidence.computed = true;
  evidence.timestamp = state.timestamp;
  evidence.last_gnss_solution_status_valid =
    last_gnss_state.id != BackendId(0) && last_gnss_state.timestamp != 0.0;
  if (evidence.last_gnss_solution_status_valid) {
    evidence.last_gnss_solution_status = last_gnss_state.status;
  }
  evidence.gdop = gdop;
  // Existing computeDops paths use 100 as a failure sentinel and may return
  // zero when the receiver position is unavailable.
  evidence.gdop_valid = std::isfinite(gdop) && gdop > 0.0 && gdop != 100.0;

  std::vector<double> pseudorange_absolute_residuals;
  std::vector<double> phaserange_absolute_residuals;
  std::vector<double> doppler_absolute_residuals;
  std::vector<double> continuity_conditioned_phase_absolute_residuals;
  std::map<DdPseudorangeGroupKey, std::vector<double>>
    pseudorange_group_finite_residuals;
  std::map<char, DopplerSystemAccumulator> doppler_system_accumulators;
  std::set<UsedSatelliteKey> used_satellites;

  const auto residual_blocks = graph->residuals(state.id_in_graph.asInteger());
  for (const auto& residual_block : residual_blocks) {
    if (!residual_block.error_interface_ptr) continue;
    const ErrorType type = residual_block.error_interface_ptr->typeInfo();

    GnssResidualPopulationEvidence* population = nullptr;
    std::vector<double>* absolute_residuals = nullptr;
    DdPseudorangeGroupKey pseudorange_group_key;
    bool has_pseudorange_group_key = false;
    PhaseFactorProvenance phase_provenance = PhaseFactorProvenance::Unknown;
    bool is_phase_factor = false;
    char doppler_system = '\0';

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
      is_phase_factor = true;
      evidence.phase_conditional.total_count++;
      const auto error = std::dynamic_pointer_cast<PhaserangeErrorDD<7, 3, 1, 1>>(
        residual_block.error_interface_ptr);
      if (error) {
        const GnssMeasurementDDIndexPair& index =
          error->constructionArrangedMeasurementIndex();
        addUsedSatellite(index.rov.prn, used_satellites);
        addUsedSatellite(index.rov_base.prn, used_satellites);
      }
      phase_provenance = classifyPhaseFactorProvenance(
        graph, residual_block, error, ambiguity_initializers);
      switch (phase_provenance) {
        case PhaseFactorProvenance::BothContinuedNoSlip:
          evidence.phase_conditional.both_continued_count++;
          break;
        case PhaseFactorProvenance::BothNew:
          evidence.phase_conditional.both_new_count++;
          break;
        case PhaseFactorProvenance::TargetContinuedBaseNew:
        case PhaseFactorProvenance::TargetNewBaseContinued:
          evidence.phase_conditional.mixed_count++;
          break;
        case PhaseFactorProvenance::AnySlip:
          evidence.phase_conditional.any_slip_count++;
          break;
        case PhaseFactorProvenance::Unknown:
          evidence.phase_conditional.unknown_count++;
          break;
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
        if (!index.prn.empty()) {
          doppler_system = index.prn[0];
          doppler_system_accumulators[doppler_system].factor_count++;
        }
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
    if (is_phase_factor &&
        phase_provenance == PhaseFactorProvenance::BothContinuedNoSlip) {
      continuity_conditioned_phase_absolute_residuals.push_back(
        std::fabs(normalized_residual));
    }
    if (doppler_system != '\0') {
      doppler_system_accumulators[doppler_system].
        finite_normalized_residuals.push_back(normalized_residual);
    }
    if (has_pseudorange_group_key) {
      pseudorange_group_finite_residuals[pseudorange_group_key].push_back(
        normalized_residual);
    }
  }

  finalizePopulation(evidence.pseudorange, pseudorange_absolute_residuals);
  finalizePopulation(evidence.phaserange, phaserange_absolute_residuals);
  finalizePopulation(evidence.doppler, doppler_absolute_residuals);

  GnssPhaseConditionalEvidence& phase = evidence.phase_conditional;
  phase.both_continued_ratio = ratioOrNan(
    phase.both_continued_count, phase.total_count);
  phase.both_new_ratio = ratioOrNan(phase.both_new_count, phase.total_count);
  phase.mixed_ratio = ratioOrNan(phase.mixed_count, phase.total_count);
  phase.any_slip_ratio = ratioOrNan(phase.any_slip_count, phase.total_count);
  phase.unknown_ratio = ratioOrNan(phase.unknown_count, phase.total_count);
  phase.continuity_conditioned_count =
    continuity_conditioned_phase_absolute_residuals.size();
  if (!continuity_conditioned_phase_absolute_residuals.empty()) {
    phase.continuity_conditioned_median_abs_normalized = percentile(
      continuity_conditioned_phase_absolute_residuals, 0.5);
    phase.continuity_conditioned_p90_abs_normalized = percentile(
      continuity_conditioned_phase_absolute_residuals, 0.9);
    phase.continuity_conditioned_max_abs_normalized = *std::max_element(
      continuity_conditioned_phase_absolute_residuals.begin(),
      continuity_conditioned_phase_absolute_residuals.end());
    size_t count_gt3 = 0, count_gt5 = 0;
    for (const double residual :
         continuity_conditioned_phase_absolute_residuals) {
      if (residual > 3.0) count_gt3++;
      if (residual > 5.0) count_gt5++;
    }
    phase.continuity_conditioned_fraction_gt3 = ratioOrNan(
      count_gt3, continuity_conditioned_phase_absolute_residuals.size());
    phase.continuity_conditioned_fraction_gt5 = ratioOrNan(
      count_gt5, continuity_conditioned_phase_absolute_residuals.size());
  }

  std::vector<double> ambiguity_transition_absolute_innovations_m;
  for (const auto& initializer : ambiguity_initializers) {
    const AmbiguityValueProvenanceResult provenance =
      inspectAmbiguityValueProvenance(
        graph, initializer.first, ambiguity_initializers);
    if (provenance.provenance != AmbiguityValueProvenance::Continued) continue;
    const double innovation = provenance.initializer - provenance.previous_value;
    if (std::isfinite(innovation)) {
      ambiguity_transition_absolute_innovations_m.push_back(
        std::fabs(innovation));
    }
  }
  evidence.ambiguity_transition.count =
    ambiguity_transition_absolute_innovations_m.size();
  setDistributionSummary(ambiguity_transition_absolute_innovations_m,
    evidence.ambiguity_transition.median_abs_m,
    evidence.ambiguity_transition.p90_abs_m,
    evidence.ambiguity_transition.max_abs_m);

  std::vector<double> doppler_system_support;
  std::vector<double> doppler_system_center_abs;
  std::vector<double> doppler_system_scales;
  for (const auto& system : doppler_system_accumulators) {
    GnssDopplerSystemGroupEvidence system_evidence;
    system_evidence.system = system.first;
    system_evidence.factor_count = system.second.factor_count;
    system_evidence.finite_count =
      system.second.finite_normalized_residuals.size();
    system_evidence.evaluation_failure_count =
      system_evidence.factor_count - system_evidence.finite_count;
    doppler_system_support.push_back(system_evidence.factor_count);

    if (!system.second.finite_normalized_residuals.empty()) {
      system_evidence.center_normalized = percentile(
        system.second.finite_normalized_residuals, 0.5);
      std::vector<double> absolute_deviations;
      absolute_deviations.reserve(
        system.second.finite_normalized_residuals.size());
      for (const double residual : system.second.finite_normalized_residuals) {
        absolute_deviations.push_back(
          std::fabs(residual - system_evidence.center_normalized));
      }
      system_evidence.scale_normalized =
        1.4826 * percentile(absolute_deviations, 0.5);
      doppler_system_center_abs.push_back(
        std::fabs(system_evidence.center_normalized));
      doppler_system_scales.push_back(system_evidence.scale_normalized);
    }
    evidence.doppler_conditional.systems.push_back(system_evidence);
  }
  evidence.doppler_conditional.system_count =
    evidence.doppler_conditional.systems.size();
  if (!doppler_system_support.empty()) {
    evidence.doppler_conditional.minimum_system_support =
      static_cast<size_t>(*std::min_element(
        doppler_system_support.begin(), doppler_system_support.end()));
    evidence.doppler_conditional.median_system_support = percentile(
      doppler_system_support, 0.5);
  }
  setDistributionSummary(doppler_system_center_abs,
    evidence.doppler_conditional.system_center_abs_p50,
    evidence.doppler_conditional.system_center_abs_p90,
    evidence.doppler_conditional.system_center_abs_max);
  setDistributionSummary(doppler_system_scales,
    evidence.doppler_conditional.system_scale_p50,
    evidence.doppler_conditional.system_scale_p90,
    evidence.doppler_conditional.system_scale_max);

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
