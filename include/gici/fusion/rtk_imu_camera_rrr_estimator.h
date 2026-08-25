/**
* @Function: RTK/IMU/Camera tightly couple estimator (GNSS raw (RTK formula) + IMU raw + camera raw)
*
* @Author  : Cheng Chi
* @Email   : chichengcn@sjtu.edu.cn
*
* Copyright (C) 2023 by Cheng Chi, All rights reserved.
**/
#pragma once

#include <fstream>
#include <set>

#include "gici/gnss/gnss_estimator_base.h"
#include "gici/gnss/gnss_source_reliability.h"
#include "gici/imu/imu_estimator_base.h"
#include "gici/vision/visual_estimator_base.h"
#include "gici/gnss/rtk_estimator.h"
#include "gici/fusion/gnss_imu_initializer.h"

namespace gici {

// RTK/IMU/Camera RRR couple options
struct RtkImuCameraRrrEstimatorOptions {
  // Frame state window length
  // We only keep GNSS measurements near to keyframes (one-to-one) and throw the others 
  // away after one optimization, because the GNSS measurement errors, especially for 
  // the multipath, are highly correlated between epochs when we have a slow or zero motion.
  // Besides, we need at least 2 GNSS states in window. If current setting cannot ensure 
  // this condition, we will ignore this option and extend the windows length.
  int max_keyframes = 5;

  // GNSS state window length before visual has been initialized
  int max_gnss_window_length_minor = 3;

  // Maximum yaw STD to start visual initialization (deg)
  double min_yaw_std_init_visual = 0.5;

  // Use CauchyLoss(1) only for DD pseudorange factors in this estimator
  bool use_cauchy_loss_for_dd_pseudorange = false;

  // Estimate and record DD pseudorange reliability before optimization
  bool estimate_reliability_for_dd_pseudorange = false;

  // Apply the estimated reliability as a DD pseudorange factor cost scale
  bool apply_reliability_weight_for_dd_pseudorange = false;

  // Estimate GNSS source reliability evidence before the first solve. Stage
  // 3A.0 is shadow-only and never applies this evidence to optimization.
  bool estimate_gnss_source_reliability = false;
};

// Estimator
class RtkImuCameraRrrEstimator : 
  public GnssEstimatorBase, 
  public VisualEstimatorBase, 
  public ImuEstimatorBase {
public:
  EIGEN_MAKE_ALIGNED_OPERATOR_NEW

  RtkImuCameraRrrEstimator(const RtkImuCameraRrrEstimatorOptions& options, 
               const GnssImuInitializerOptions& init_options, 
               const RtkEstimatorOptions rtk_options,
               const GnssEstimatorBaseOptions& gnss_base_options, 
               const GnssLooseEstimatorBaseOptions& gnss_loose_base_options, 
               const VisualEstimatorBaseOptions& visual_base_options,
               const ImuEstimatorBaseOptions& imu_base_options,
               const EstimatorBaseOptions& base_options,
               const AmbiguityResolutionOptions& ambiguity_options);
  ~RtkImuCameraRrrEstimator();

  // Add measurement
  bool addMeasurement(const EstimatorDataCluster& measurement) override;

  // Estimate current graph
  bool estimate() override;

  // Set initializatin result
  void setInitializationResult(
    const std::shared_ptr<MultisensorInitializerBase>& initializer) override;

protected:
  // Add GNSS measurements and state
  bool addGnssMeasurementAndState(
    const GnssMeasurement& measurement_rov, 
    const GnssMeasurement& measurement_ref);

  // Add image measurements and state
  bool addImageMeasurementAndState(const FrameBundlePtr& frame_bundle, 
    const SpeedAndBias& speed_and_bias = SpeedAndBias::Zero());

  // Visual initialization
  bool visualInitialization(const FrameBundlePtr& frame_bundle);

  // Marginalization
  bool marginalization(const IdType& type);

  // Marginalization when the new state is a frame state
  bool frameMarginalization();

  // Marginalization when the new state is a GNSS state
  bool gnssMarginalization();

  // Sparsify GNSS states to bound computational load
  void sparsifyGnssStates();

  // Compute ambiguity covariance at current epoch
  bool estimateAmbiguityCovariance(const State& state, Eigen::MatrixXd& covariance);

  // Create diagnostic loggers
  void createDiagnosticLoggers();

  // Log diagnostics
  void logDdPseudorangeReliabilityDiagnostics(const State& state);
  void logGnssSourceReliabilityEvidence(
    const GnssSourceReliabilityEvidence& evidence);
  void logVisualResidualDiagnostics(const State& state, const FramePtr& frame);
  void logImuResidualDiagnostics(const State& state);
  void logMotionConstraintDiagnostics(const State& state);
  void logGnssRejectionEvents(const double timestamp,
    const std::set<uint64_t>& before, const std::set<uint64_t>& after,
    const char* measurement_type, const char* removal_stage,
    const char* removal_role);
  void logRrrEpochDiagnostics(const double timestamp,
    const std::set<uint64_t>& pseudorange_before,
    const std::set<uint64_t>& pseudorange_after,
    const std::set<uint64_t>& phaserange_before,
    const std::set<uint64_t>& phaserange_after_pseudorange_stage,
    const std::set<uint64_t>& phaserange_after_doppler_stage,
    const std::set<uint64_t>& phaserange_after,
    const std::set<uint64_t>& doppler_before,
    const std::set<uint64_t>& doppler_after,
    const size_t pseudorange_trigger_rejected,
    const size_t phaserange_trigger_rejected,
    const size_t doppler_trigger_rejected,
    const bool ar_attempted,
    const char* post_ar_solution_status, const char* post_ar_success,
    const size_t rrr_unfix_ambiguity_reset_event,
    const GnssPreoptResidualSummary& preopt_summary,
    const double first_optimize_ms, const double gnss_rejection_ms,
    const double ar_ms, const double epoch_compute_ms);
  
  // Get latest state
  inline State& latestState() override { return states_[latest_state_index_]; }

protected:
  // Options
  RtkImuCameraRrrEstimatorOptions rrr_options_;
  RtkEstimatorOptions rtk_options_;

  // Initialization control
  std::shared_ptr<GnssImuInitializer> gnss_imu_initializer_;
  std::shared_ptr<RtkEstimator> initializer_sub_estimator_;
  bool visual_initialized_ = false;
  std::deque<FrameBundlePtr> init_keyframes_;
  std::deque<Solution> init_solution_store_;

  // Measurement alignment handle
  DifferentialMeasurementsAlign meausrement_align_;

  // RTK estimator used for ambiguity covariance estimation
  std::unique_ptr<RtkEstimator> ambiguity_covariance_estimator_;
  bool ambiguity_covariance_coordinate_setted_ = false;

  // Status control
  int num_continuous_unfix_ = 0;
  int num_cotinuous_reject_gnss_ = 0;
  int num_cotinuous_reject_visual_ = 0;

  // Latest read-only first-solve-before GNSS source evidence. Computation is
  // independent of diagnostic logging so future consumers can use it when
  // log_intermediate_data is disabled.
  GnssSourceReliabilityEvidence gnss_source_reliability_evidence_;

  // Diagnostic loggers
  std::ofstream visual_residual_diagnostics_logger_;
  std::ofstream imu_residual_diagnostics_logger_;
  std::ofstream motion_constraint_diagnostics_logger_;
  std::ofstream gnss_rejection_events_logger_;
  std::ofstream rrr_epoch_diagnostics_logger_;
  std::ofstream dd_pseudorange_reliability_diagnostics_logger_;
  std::ofstream gnss_source_reliability_evidence_logger_;
};

}
