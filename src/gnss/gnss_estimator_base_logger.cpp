/**
* @Function: Base class for GNSS estimators
*
* @Author  : Cheng Chi
* @Email   : chichengcn@sjtu.edu.cn
*
* Copyright (C) 2023 by Cheng Chi, All rights reserved.
**/
#include "gici/gnss/gnss_estimator_base.h"

#include <cmath>
#include <limits>

#include "gici/utility/global_variable.h"
#include "gici/gnss/gnss_parameter_blocks.h"
#include "gici/gnss/code_phase_maps.h"
#include "gici/gnss/pseudorange_error.h"
#include "gici/gnss/phaserange_error.h"

namespace gici {

namespace {

bool findDiagnosticObservation(
  const GnssMeasurement& measurement, const GnssMeasurementIndex& index,
  const char* role, const double state_time, const double measurement_rov_time,
  const double measurement_ref_time, const Satellite** satellite,
  const Observation** observation)
{
  const auto satellite_it = measurement.satellites.find(index.prn);
  if (satellite_it == measurement.satellites.end()) {
    LOG(WARNING) << "GNSS residual diagnostics observation unavailable: role="
                 << role << ", state_time=" << state_time
                 << ", measurement_rov_time=" << measurement_rov_time
                 << ", measurement_ref_time=" << measurement_ref_time
                 << ", requested=" << index.prn << " / " << index.code_type
                 << ", available: satellite missing";
    return false;
  }

  const Satellite& found_satellite = satellite_it->second;
  const auto observation_it = found_satellite.observations.find(index.code_type);
  if (observation_it == found_satellite.observations.end()) {
    std::string available;
    for (const auto& item : found_satellite.observations) {
      available += " map_key=" + std::to_string(item.first) +
        " raw_code=" + std::to_string(item.second.raw_code);
    }
    LOG(WARNING) << "GNSS residual diagnostics observation unavailable: role="
                 << role << ", state_time=" << state_time
                 << ", measurement_rov_time=" << measurement_rov_time
                 << ", measurement_ref_time=" << measurement_ref_time
                 << ", requested=" << index.prn << " / " << index.code_type
                 << ", available:" << available;
    return false;
  }

  *satellite = &found_satellite;
  *observation = &observation_it->second;
  return true;
}

}  // namespace

// Create ambiguity logger
void GnssEstimatorBase::createAmbiguityLogger(const std::string& directory)
{
  double time = vk::Timer::getCurrentTime();
  double ep[6];
  char buf[32];
  time2epoch(gnss_common::doubleToGtime(time), ep);
  sprintf(buf, "%04d%02d%02d-%02d%02d%02d", 
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], (int)ep[5]);
  std::string path = directory + "/ambiguity-" + buf + ".log";
  ambiguity_logger_.open(path, std::ios::out | std::ios::trunc);
}

// Create ionosphere logger
void GnssEstimatorBase::createIonosphereLogger(const std::string& directory)
{
  double time = vk::Timer::getCurrentTime();
  double ep[6];
  char buf[32];
  time2epoch(gnss_common::doubleToGtime(time), ep);
  sprintf(buf, "%04d%02d%02d-%02d%02d%02d", 
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], (int)ep[5]);
  std::string path = directory + "/ionosphere-" + buf + ".log";
  ionosphere_logger_.open(path, std::ios::out | std::ios::trunc);
}

// Create pseudorange residual logger
void GnssEstimatorBase::createPseudorangeResidualLogger(const std::string& directory)
{
  double time = vk::Timer::getCurrentTime();
  double ep[6];
  char buf[32];
  time2epoch(gnss_common::doubleToGtime(time), ep);
  sprintf(buf, "%04d%02d%02d-%02d%02d%02d", 
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], (int)ep[5]);
  std::string path = directory + "/pseudorange_residual-" + buf + ".log";
  pseudorange_residual_logger_.open(path, std::ios::out | std::ios::trunc);
}

// Create DD pseudorange residual logger
void GnssEstimatorBase::createDdPseudorangeResidualLogger(const std::string& directory)
{
  double time = vk::Timer::getCurrentTime();
  double ep[6];
  char buf[32];
  time2epoch(gnss_common::doubleToGtime(time), ep);
  sprintf(buf, "%04d%02d%02d-%02d%02d%02d", 
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], (int)ep[5]);
  std::string path = directory + "/dd_pseudorange_residual-" + buf + ".log";
  dd_pseudorange_residual_logger_.open(path, std::ios::out | std::ios::trunc);
}

// Create phaserange residual logger
void GnssEstimatorBase::createPhaserangeResidualLogger(const std::string& directory)
{
  double time = vk::Timer::getCurrentTime();
  double ep[6];
  char buf[32];
  time2epoch(gnss_common::doubleToGtime(time), ep);
  sprintf(buf, "%04d%02d%02d-%02d%02d%02d", 
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], (int)ep[5]);
  std::string path = directory + "/phaserange_residual-" + buf + ".log";
  phaserange_residual_logger_.open(path, std::ios::out | std::ios::trunc);
}

// Create DD phaserange residual logger
void GnssEstimatorBase::createDdPhaserangeResidualLogger(const std::string& directory)
{
  double time = vk::Timer::getCurrentTime();
  double ep[6];
  char buf[32];
  time2epoch(gnss_common::doubleToGtime(time), ep);
  sprintf(buf, "%04d%02d%02d-%02d%02d%02d", 
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], (int)ep[5]);
  std::string path = directory + "/dd_phaserange_residual-" + buf + ".log";
  dd_phaserange_residual_logger_.open(path, std::ios::out | std::ios::trunc);
}

// Create GNSS residual diagnostics logger
void GnssEstimatorBase::createGnssResidualDiagnosticsLogger(const std::string& directory)
{
  double time = vk::Timer::getCurrentTime();
  double ep[6];
  char buf[32];
  time2epoch(gnss_common::doubleToGtime(time), ep);
  sprintf(buf, "%04d%02d%02d-%02d%02d%02d",
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], (int)ep[5]);
  std::string path = directory + "/gnss_residual_diagnostics-" + buf + ".csv";
  gnss_residual_diagnostics_logger_.open(path, std::ios::out | std::ios::trunc);
  std::string preopt_path = directory + "/gnss_preopt_residual_diagnostics-" + buf + ".csv";
  gnss_preopt_residual_diagnostics_logger_.open(
    preopt_path, std::ios::out | std::ios::trunc);
  if (!gnss_residual_diagnostics_logger_.is_open()) return;

  const std::string header =
    "timestamp,measurement_type,residual_uid,rov_prn,base_prn,prn,code_type,"
    "normalized_residual,raw_residual,effective_sigma,"
    "rov_target_elevation_deg,rov_base_elevation_deg,elevation_deg,"
    "rov_target_snr,ref_target_snr,rov_base_snr,ref_base_snr,doppler_snr,"
    "rov_target_slip,ref_target_slip,rov_base_slip,ref_base_slip,doppler_slip,"
    "rov_target_lli,ref_target_lli,rov_base_lli,ref_base_lli,doppler_lli,"
    "loss_type,loss_delta,rho0,rho1,rho2";
  gnss_residual_diagnostics_logger_ << header << '\n';
  if (gnss_preopt_residual_diagnostics_logger_.is_open()) {
    gnss_preopt_residual_diagnostics_logger_ << header << '\n';
  }
}

// Log ambiguity estimate
void GnssEstimatorBase::logAmbiguityEstimate()
{
  // Get ambiguity estimate
  AmbiguityState& ambiguity_state = lastAmbiguityState();
  std::map<std::string, std::map<std::string, double>> ambiguity_estimates;
  for (auto id : ambiguity_state.ids) {
    std::shared_ptr<AmbiguityParameterBlock> block_ptr =
        std::static_pointer_cast<AmbiguityParameterBlock>(
          graph_->parameterBlockPtr(id.asInteger()));
    CHECK(block_ptr != nullptr);
    double value = block_ptr->estimate().x();
    std::string prn = id.gPrn();
    char system = prn[0];
    std::string phase_str;
#define MAP(S, P, PS) \
    if (system == S && id.gPhaseId() == P) { phase_str = PS; }
    PHASE_CHANNEL_TO_STR_MAPS;
#undef MAP
    if (ambiguity_estimates.find(prn) == ambiguity_estimates.end()) {
      ambiguity_estimates.insert(std::make_pair(prn, std::map<std::string, double>()));
    }
    std::map<std::string, double>& phase_to_value = ambiguity_estimates.at(prn);
    phase_to_value.insert(std::make_pair(phase_str, value));
  }

  // Log to file
  double ep[6];
  time2epoch(gnss_common::doubleToGtime(ambiguity_state.timestamp), ep);
  char time_buf[64];
  sprintf(time_buf, "> %04d %02d %02d %02d %02d %10.7lf  %17.7lf",
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], ep[5],
    ambiguity_state.timestamp);
  ambiguity_logger_ << time_buf << std::endl;
  for (auto i : ambiguity_estimates) {
    const std::string& prn = i.first;
    ambiguity_logger_ << prn << " ";
    for (auto j : i.second) {
      const std::string& phase_str = j.first;
      const double& value = j.second;
      ambiguity_logger_ << phase_str << " "
        << std::fixed << std::setprecision(4) << value << " ";
    }
    ambiguity_logger_ << std::endl;
  }
} 

// Log ionosphere estimate
void GnssEstimatorBase::logIonosphereEstimate()
{
  // Get ionosphere estimate
  IonosphereState& ionosphere_state = lastIonosphereState();
  std::map<std::string, double> ionosphere_estimates;
  for (auto id : ionosphere_state.ids) {
    std::shared_ptr<IonosphereParameterBlock> block_ptr =
        std::static_pointer_cast<IonosphereParameterBlock>(
          graph_->parameterBlockPtr(id.asInteger()));
    CHECK(block_ptr != nullptr);
    double value = block_ptr->estimate().x();
    std::string prn = id.gPrn();
    ionosphere_estimates.insert(std::make_pair(prn, value));
  }

  // Log to file
  double ep[6];
  time2epoch(gnss_common::doubleToGtime(ionosphere_state.timestamp), ep);
  char time_buf[64];
  sprintf(time_buf, "> %04d %02d %02d %02d %02d %10.7lf  %17.7lf",
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], ep[5],
    ionosphere_state.timestamp);
  ionosphere_logger_ << time_buf << std::endl;
  for (auto i : ionosphere_estimates) {
    const std::string& prn = i.first;
    const double& value = i.second;
    ionosphere_logger_ << prn << " " 
      << std::fixed << std::setprecision(4) << value << std::endl;
  }
} 

// Log pseudorange residual
void GnssEstimatorBase::logPseudorangeResidual()
{
  // Get residuals
  State& state = lastState();
  const auto& residuals = graph_->residuals(state.id.asInteger());
  std::map<std::string, std::map<std::string, double>> residual_values;
  for (const auto& residual : residuals) {
    const ceres::ResidualBlockId id = residual.residual_block_id;
    const std::shared_ptr<ErrorInterface>& interface = residual.error_interface_ptr;
    if (interface->typeInfo() != ErrorType::kPseudorangeError) continue;

    GnssMeasurementIndex index = 
      getGnssMeasurementIndexFromErrorInterface(interface);
    std::string prn = index.prn;
    std::string code_str = gnss_common::codeTypeToRinexType(prn[0], index.code_type);
    double residual_evaluate[1];
    graph_->problem_->EvaluateResidualBlock(
        id, false, nullptr, residual_evaluate, nullptr);
    interface->deNormalizeResidual(residual_evaluate);
    if (residual_values.find(prn) == residual_values.end()) {
      residual_values.insert(std::make_pair(prn, std::map<std::string, double>()));
    }
    std::map<std::string, double>& code_to_value = residual_values.at(prn);
    code_to_value.insert(std::make_pair(code_str, residual_evaluate[0]));
  }

  // Log to file
  double ep[6];
  time2epoch(gnss_common::doubleToGtime(state.timestamp), ep);
  char time_buf[64];
  sprintf(time_buf, "> %04d %02d %02d %02d %02d %10.7lf  %17.7lf",
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], ep[5],
    state.timestamp);
  pseudorange_residual_logger_ << time_buf << std::endl;
  for (auto i : residual_values) {
    const std::string& prn = i.first;
    pseudorange_residual_logger_ << prn << " ";
    for (auto j : i.second) {
      const std::string& code_str = j.first;
      const double& value = j.second;
      pseudorange_residual_logger_ << code_str << " "
        << std::fixed << std::setprecision(4) << value << " ";
    }
    pseudorange_residual_logger_ << std::endl;
  }
}

// Log DD pseudorange residual
void GnssEstimatorBase::logDdPseudorangeResidual()
{
  // Get residuals
  State& state = lastState();
  const auto& residuals = graph_->residuals(state.id.asInteger());
  std::map<std::pair<std::string, std::string>, 
    std::map<std::string, double>> residual_values;
  for (const auto& residual : residuals) {
    const ceres::ResidualBlockId id = residual.residual_block_id;
    const std::shared_ptr<ErrorInterface>& interface = residual.error_interface_ptr;
    if (interface->typeInfo() != ErrorType::kPseudorangeErrorDD) continue;

    GnssMeasurementDDIndexPair index = 
      getGnssMeasurementDDIndexPairFromErrorInterface(interface);
    std::string prn = index.rov.prn;
    std::string code_str = gnss_common::codeTypeToRinexType(prn[0], index.rov.code_type);
    std::pair<std::string, std::string> prn_pair = 
      std::make_pair(index.rov.prn, index.rov_base.prn);
    double residual_evaluate[1];
    graph_->problem_->EvaluateResidualBlock(
        id, false, nullptr, residual_evaluate, nullptr);
    interface->deNormalizeResidual(residual_evaluate);
    if (residual_values.find(prn_pair) == residual_values.end()) {
      residual_values.insert(std::make_pair(prn_pair, std::map<std::string, double>()));
    }
    std::map<std::string, double>& code_to_value = residual_values.at(prn_pair);
    code_to_value.insert(std::make_pair(code_str, residual_evaluate[0]));
  }

  // Log to file
  double ep[6];
  time2epoch(gnss_common::doubleToGtime(state.timestamp), ep);
  char time_buf[64];
  sprintf(time_buf, "> %04d %02d %02d %02d %02d %10.7lf  %17.7lf",
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], ep[5],
    state.timestamp);
  dd_pseudorange_residual_logger_ << time_buf << std::endl;
  for (auto i : residual_values) {
    const auto& prn_pair = i.first;
    dd_pseudorange_residual_logger_ << prn_pair.second << "-" << prn_pair.first << " ";
    for (auto j : i.second) {
      const std::string& code_str = j.first;
      const double& value = j.second;
      dd_pseudorange_residual_logger_ << code_str << " "
        << std::fixed << std::setprecision(4) << value << " ";
    }
    dd_pseudorange_residual_logger_ << std::endl;
  }
}

// Log phaserange residual
void GnssEstimatorBase::logPhaserangeResidual()
{
  // Get residuals
  State& state = lastState();
  const auto& residuals = graph_->residuals(state.id.asInteger());
  std::map<std::string, std::map<std::string, double>> residual_values;
  for (const auto& residual : residuals) {
    const ceres::ResidualBlockId id = residual.residual_block_id;
    const std::shared_ptr<ErrorInterface>& interface = residual.error_interface_ptr;
    if (interface->typeInfo() != ErrorType::kPhaserangeError) continue;

    GnssMeasurementIndex index = 
      getGnssMeasurementIndexFromErrorInterface(interface);
    std::string prn = index.prn;
    char system = prn[0];
    int phase_id = gnss_common::getPhaseID(system, index.code_type);
    std::string phase_str;
#define MAP(S, P, PS) \
    if (system == S && phase_id == P) { phase_str = PS; }
    PHASE_CHANNEL_TO_STR_MAPS;
#undef MAP
    double residual_evaluate[1];
    graph_->problem_->EvaluateResidualBlock(
        id, false, nullptr, residual_evaluate, nullptr);
    interface->deNormalizeResidual(residual_evaluate);
    if (residual_values.find(prn) == residual_values.end()) {
      residual_values.insert(std::make_pair(prn, std::map<std::string, double>()));
    }
    std::map<std::string, double>& phase_to_value = residual_values.at(prn);
    phase_to_value.insert(std::make_pair(phase_str, residual_evaluate[0]));
  }

  // Log to file
  double ep[6];
  time2epoch(gnss_common::doubleToGtime(state.timestamp), ep);
  char time_buf[64];
  sprintf(time_buf, "> %04d %02d %02d %02d %02d %10.7lf  %17.7lf",
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], ep[5],
    state.timestamp);
  phaserange_residual_logger_ << time_buf << std::endl;
  for (auto i : residual_values) {
    const std::string& prn = i.first;
    phaserange_residual_logger_ << prn << " ";
    for (auto j : i.second) {
      const std::string& phase_str = j.first;
      const double& value = j.second;
      phaserange_residual_logger_ << phase_str << " "
        << std::fixed << std::setprecision(4) << value << " ";
    }
    phaserange_residual_logger_ << std::endl;
  }
}

// Log DD phaserange residual
void GnssEstimatorBase::logDdPhaserangeResidual()
{
  // Get residuals
  State& state = lastState();
  const auto& residuals = graph_->residuals(state.id.asInteger());
  std::map<std::pair<std::string, std::string>, 
    std::map<std::string, double>> residual_values;
  for (const auto& residual : residuals) {
    const ceres::ResidualBlockId id = residual.residual_block_id;
    const std::shared_ptr<ErrorInterface>& interface = residual.error_interface_ptr;
    if (interface->typeInfo() != ErrorType::kPhaserangeErrorDD) continue;

    GnssMeasurementDDIndexPair index = 
      getGnssMeasurementDDIndexPairFromErrorInterface(interface);
    std::string prn = index.rov.prn;
    char system = prn[0];
    int phase_id = gnss_common::getPhaseID(system, index.rov.code_type);
    std::pair<std::string, std::string> prn_pair = 
      std::make_pair(index.rov.prn, index.rov_base.prn);
    std::string phase_str;
#define MAP(S, P, PS) \
    if (system == S && phase_id == P) { phase_str = PS; }
    PHASE_CHANNEL_TO_STR_MAPS;
#undef MAP
    double residual_evaluate[1];
    graph_->problem_->EvaluateResidualBlock(
        id, false, nullptr, residual_evaluate, nullptr);
    interface->deNormalizeResidual(residual_evaluate);
    if (residual_values.find(prn_pair) == residual_values.end()) {
      residual_values.insert(std::make_pair(prn_pair, std::map<std::string, double>()));
    }
    std::map<std::string, double>& phase_to_value = residual_values.at(prn_pair);
    phase_to_value.insert(std::make_pair(phase_str, residual_evaluate[0]));
  }

  // Log to file
  double ep[6];
  time2epoch(gnss_common::doubleToGtime(state.timestamp), ep);
  char time_buf[64];
  sprintf(time_buf, "> %04d %02d %02d %02d %02d %10.7lf  %17.7lf",
    (int)ep[0], (int)ep[1], (int)ep[2], (int)ep[3], (int)ep[4], ep[5],
    state.timestamp);
  dd_phaserange_residual_logger_ << time_buf << std::endl;
  for (auto i : residual_values) {
    const auto& prn_pair = i.first;
    dd_phaserange_residual_logger_ << prn_pair.second << "-" << prn_pair.first << " ";
    for (auto j : i.second) {
      const std::string& phase_str = j.first;
      const double& value = j.second;
      dd_phaserange_residual_logger_ << phase_str << " "
        << std::fixed << std::setprecision(4) << value << " ";
    }
    dd_phaserange_residual_logger_ << std::endl;
  }
}

void GnssEstimatorBase::logGnssPreoptResidualDiagnostics(
  const State& state, const GnssMeasurement& measurement_rov,
  const GnssMeasurement& measurement_ref)
{
  logGnssResidualDiagnostics(state, measurement_rov, measurement_ref, true);
}

// Log GNSS residual diagnostics before outlier rejection
void GnssEstimatorBase::logGnssResidualDiagnostics(
  const State& state, const GnssMeasurement& measurement_rov,
  const GnssMeasurement& measurement_ref, const bool preopt)
{
  std::ofstream& logger = preopt ? gnss_preopt_residual_diagnostics_logger_ :
    gnss_residual_diagnostics_logger_;
  if (preopt) {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    gnss_preopt_residual_summary_ = GnssPreoptResidualSummary();
    gnss_preopt_residual_summary_.pseudorange_max_abs_normalized = nan;
    gnss_preopt_residual_summary_.phaserange_max_abs_normalized = nan;
    gnss_preopt_residual_summary_.doppler_max_abs_normalized = nan;
  }
  if (!logger.is_open()) return;

  const auto& residual_blocks = graph_->residuals(state.id_in_graph.asInteger());
  for (const auto& residual_block : residual_blocks) {
    const auto& interface = residual_block.error_interface_ptr;
    if (!interface) {
      LOG(WARNING) << "Skip GNSS " << (preopt ? "pre-opt" : "post-fit")
                   << " diagnostic residual " << residual_block.residual_block_id
                   << ": error interface is unavailable.";
      continue;
    }
    const ErrorType type = interface->typeInfo();
    if (type != ErrorType::kPseudorangeErrorDD &&
        type != ErrorType::kPhaserangeErrorDD &&
        type != ErrorType::kDopplerError) continue;

    double residual[1];
    if (!graph_->problem()->EvaluateResidualBlock(
          residual_block.residual_block_id, false, nullptr, residual, nullptr)) {
      LOG(WARNING) << "Skip GNSS " << (preopt ? "pre-opt" : "post-fit")
                   << " diagnostic residual " << residual_block.residual_block_id
                   << ": EvaluateResidualBlock failed.";
      continue;
    }
    const double normalized_residual = residual[0];
    if (preopt) {
      const double abs_normalized_residual = std::fabs(normalized_residual);
      double* max_abs_normalized = nullptr;
      size_t* count_gt3 = nullptr;
      size_t* count_gt5 = nullptr;
      if (type == ErrorType::kPseudorangeErrorDD) {
        max_abs_normalized = &gnss_preopt_residual_summary_.pseudorange_max_abs_normalized;
        count_gt3 = &gnss_preopt_residual_summary_.pseudorange_count_gt3;
        count_gt5 = &gnss_preopt_residual_summary_.pseudorange_count_gt5;
      }
      else if (type == ErrorType::kPhaserangeErrorDD) {
        max_abs_normalized = &gnss_preopt_residual_summary_.phaserange_max_abs_normalized;
        count_gt3 = &gnss_preopt_residual_summary_.phaserange_count_gt3;
        count_gt5 = &gnss_preopt_residual_summary_.phaserange_count_gt5;
      }
      else {
        max_abs_normalized = &gnss_preopt_residual_summary_.doppler_max_abs_normalized;
        count_gt3 = &gnss_preopt_residual_summary_.doppler_count_gt3;
        count_gt5 = &gnss_preopt_residual_summary_.doppler_count_gt5;
      }
      if (std::isnan(*max_abs_normalized) || abs_normalized_residual > *max_abs_normalized) {
        *max_abs_normalized = abs_normalized_residual;
      }
      if (abs_normalized_residual > 3.0) (*count_gt3)++;
      if (abs_normalized_residual > 5.0) (*count_gt5)++;
    }
    interface->deNormalizeResidual(residual);
    const double raw_residual = residual[0];
    double sigma_probe[1] = {1.0};
    interface->deNormalizeResidual(sigma_probe);
    const double effective_sigma = std::fabs(sigma_probe[0]);
    const double squared_normalized_residual = normalized_residual * normalized_residual;
    double rho[3] = {squared_normalized_residual, 1.0, 0.0};
    const char* loss_type = "none";
    double loss_delta = 0.0;
    if (residual_block.loss_function_ptr) {
      residual_block.loss_function_ptr->Evaluate(squared_normalized_residual, rho);
      if (residual_block.loss_function_ptr == huber_loss_function_.get()) {
        loss_type = "huber";
        // Must match EstimatorBase's shared HuberLoss(1) construction.
        loss_delta = 1.0;
      }
      else loss_type = "other";
    }

    if (type == ErrorType::kPseudorangeErrorDD ||
        type == ErrorType::kPhaserangeErrorDD) {
      const GnssMeasurementDDIndexPair index =
        getGnssMeasurementDDIndexPairFromErrorInterface(interface);
      const Satellite *rov_target_satellite, *ref_target_satellite,
        *rov_base_satellite, *ref_base_satellite;
      const Observation *rov_target, *ref_target, *rov_base, *ref_base;
      const bool has_rov_target = findDiagnosticObservation(
        measurement_rov, index.rov, "rov_target", state.timestamp,
        measurement_rov.timestamp, measurement_ref.timestamp,
        &rov_target_satellite, &rov_target);
      const bool has_ref_target = findDiagnosticObservation(
        measurement_ref, index.ref, "ref_target", state.timestamp,
        measurement_rov.timestamp, measurement_ref.timestamp,
        &ref_target_satellite, &ref_target);
      const bool has_rov_base = findDiagnosticObservation(
        measurement_rov, index.rov_base, "rov_base", state.timestamp,
        measurement_rov.timestamp, measurement_ref.timestamp,
        &rov_base_satellite, &rov_base);
      const bool has_ref_base = findDiagnosticObservation(
        measurement_ref, index.ref_base, "ref_base", state.timestamp,
        measurement_rov.timestamp, measurement_ref.timestamp,
        &ref_base_satellite, &ref_base);
      if (!has_rov_target || !has_ref_target || !has_rov_base || !has_ref_base) {
        continue;
      }
      const double rov_target_elevation = gnss_common::satelliteElevation(
        rov_target_satellite->sat_position, measurement_rov.position) * R2D;
      const double rov_base_elevation = gnss_common::satelliteElevation(
        rov_base_satellite->sat_position, measurement_rov.position) * R2D;

      logger
        << std::setprecision(15) << state.timestamp << ","
        << (type == ErrorType::kPseudorangeErrorDD ? "dd_pseudorange" : "dd_phaserange")
        << "," << reinterpret_cast<uint64_t>(residual_block.residual_block_id)
        << "," << index.rov.prn << "," << index.rov_base.prn << ",,"
        << index.rov.code_type << "," << normalized_residual << ","
        << raw_residual << "," << effective_sigma << ","
        << rov_target_elevation << "," << rov_base_elevation << ",,"
        << rov_target->SNR << "," << ref_target->SNR << ","
        << rov_base->SNR << "," << ref_base->SNR << ",,"
        << static_cast<int>(rov_target->slip) << ","
        << static_cast<int>(ref_target->slip) << ","
        << static_cast<int>(rov_base->slip) << ","
        << static_cast<int>(ref_base->slip) << ",,"
        << static_cast<int>(rov_target->LLI) << ","
        << static_cast<int>(ref_target->LLI) << ","
        << static_cast<int>(rov_base->LLI) << ","
        << static_cast<int>(ref_base->LLI) << ","
        << loss_type << "," << loss_delta << "," << rho[0] << ","
        << rho[1] << "," << rho[2]
        << '\n';
    }
    else {
      const GnssMeasurementIndex index =
        getGnssMeasurementIndexFromErrorInterface(interface);
      const Satellite* satellite;
      const Observation* observation;
      if (!findDiagnosticObservation(
            measurement_rov, index, "doppler", state.timestamp,
            measurement_rov.timestamp, measurement_ref.timestamp,
            &satellite, &observation)) {
        continue;
      }
      const double elevation = gnss_common::satelliteElevation(
        satellite->sat_position, measurement_rov.position) * R2D;

      logger
        << std::setprecision(15) << state.timestamp << ","
        << "doppler," << reinterpret_cast<uint64_t>(residual_block.residual_block_id)
        << ",,," << index.prn << "," << index.code_type << ","
        << normalized_residual << "," << raw_residual << ","
        << effective_sigma << ",,," << elevation << ",,,,,"
        << observation->SNR << ",,,,,"
        << static_cast<int>(observation->slip) << ",,,,,"
        << static_cast<int>(observation->LLI) << "," << loss_type << ","
        << loss_delta << "," << rho[0] << "," << rho[1] << "," << rho[2] << '\n';
    }
  }
}

// Free ambiguity logger
void GnssEstimatorBase::freeAmbiguityLogger()
{
  ambiguity_logger_.close();
}

// Free ionosphere logger
void GnssEstimatorBase::freeIonosphereLogger()
{
  ionosphere_logger_.close();
}

// Free pseudorange residual logger
void GnssEstimatorBase::freePseudorangeResidualLogger()
{
  pseudorange_residual_logger_.close();
}

// Free DD pseudorange residual logger
void GnssEstimatorBase::freeDdPseudorangeResidualLogger()
{
  dd_pseudorange_residual_logger_.close();
}

// Free phaserange residual logger
void GnssEstimatorBase::freePhaserangeResidualLogger()
{
  phaserange_residual_logger_.close();
}

// Free DD phaserange residual logger
void GnssEstimatorBase::freeDdPhaserangeResidualLogger()
{
  dd_phaserange_residual_logger_.close();
}

// Free GNSS residual diagnostics logger
void GnssEstimatorBase::freeGnssResidualDiagnosticsLogger()
{
  gnss_residual_diagnostics_logger_.close();
  gnss_preopt_residual_diagnostics_logger_.close();
}

}
