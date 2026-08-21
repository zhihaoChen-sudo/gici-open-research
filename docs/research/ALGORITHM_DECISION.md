Current hypothesis:

The dominant unresolved failure mode is:

persistent DD pseudorange gross inconsistency
entering the first nonlinear solve.

Evidence:

1.
pre/post residual behavior

2.
post-fit tail distribution

3.
hard rejection statistics

4.
re-optimization experiment

Rejected directions:

1.
global GNSS down-weighting

2.
pre-fit carrier phase gating

3.
second optimization after rejection

Next experiment:

DD pseudorange-only redescending robust loss.

First candidate:

CauchyLoss.

Keep unchanged:

- phase loss
- Doppler loss
- vision
- IMU
- motion constraints
- AR pipeline
