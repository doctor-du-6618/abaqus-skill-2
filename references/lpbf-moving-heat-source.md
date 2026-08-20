# LPBF moving-heat-source diagnosis and acceleration

Use this reference for `DFLUX`-driven LPBF thermal models and their sequential stress analyses.

## 1. Classify the termination

Read `.sta`, `.msg`, `.dat`, scheduler/command output, and ODB status. Distinguish:

- solver convergence or time-integration failure;
- input-processing or subroutine compile/link failure;
- external/user stop;
- postprocessing or SIM wrap-up filesystem failure after the solver outcome is already known.

Do not label an externally stopped run as nonconvergent. Do not promote a later wrap-up exception over an earlier Standard error.

## 2. Audit energy and motion

Write the effective absorbed power explicitly:

`P_effective = P_nominal × absorptivity × layer_scale × calibration_scale × segment_scale`

Check power normalization, units, depth distribution, scan speed, hatch spacing, layer thickness, path duration, laser-off jumps, layer rotations, and the meaning of `TIME(1)`/`TIME(2)`. Preserve real travel time when adding contour or repositioning segments.

Relate the maximum time increment to spatial motion:

`travel_per_increment = scan_speed × maximum_increment`

Compare this distance with in-plane element size, beam diameter, and output interval. Report the chosen spatial resolution rather than calling a larger increment “accurate” without evidence.

## 3. Separate performance levers

Keep these mechanisms distinct:

- solver increments and nonlinear retries;
- time-integration accuracy cutbacks such as `DELTMX` rejections;
- exact output-time constraints;
- saved frame count and ODB I/O;
- DFLUX call-domain size and subroutine cost;
- CPU/domain parallel overhead.

`maxNumInc` is only an abort ceiling. Reducing it cannot force fewer increments. Sparse field output reduces storage and I/O, but exact requested output times can still shorten solver increments. Test `TIME MARKS` behavior rather than assuming approximate output is faster or sufficiently comparable.

Benchmark CPU counts on the real model; more domains can be slower for a small equation count or expensive user-subroutine synchronization.

## 4. Reduce DFLUX work without changing physics

Restrict each scan load to elements whose integration points can receive nonzero flux. Derive the required depth band from the heat-source support, layer thickness, element integration scheme, and geometry. Include the substrate top band for the first layer when the source penetrates it.

Use an explicit `*DFLUX, OP=NEW` or equivalent CAE state in cooling steps to stop needless subroutine calls. Validate the cropped and uncropped models at identical saved times; require zero or accepted-tolerance differences over all nodes, not only the peak temperature.

## 5. Calibrate in stages

Separate contour, corners, and hatch infill because their thermal accumulation differs. For coarse single-integration-point elements such as `DC3D8R`, aligning a path exactly with an integration point can create localized peaks; corner turns can accumulate energy from two segments.

Use this order:

1. unit and normalization check;
2. short single-track or partial-layer run;
3. contour edge and corner calibration;
4. hatch-track calibration;
5. full first-layer and second-layer verification;
6. full thermal build;
7. sequential stress run only after thermal acceptance.

Do not generalize a contour calibration to hatch infill or a short partial path to all layers. Keep separately validated segment parameters fixed while tuning an unvalidated segment unless the evidence requires reopening both.

## 6. Comparison gates

Hold geometry, mesh, active regions, material data, scan path, power history, step duration, output comparison times, Abaqus version, precision, and CPU count constant for an A/B test.

Compare at matched physical times:

- successful increments, rejected attempts, equilibrium iterations, and wall time;
- peak temperature and its location;
- all-node MAE, RMSE, and maximum absolute difference;
- hot-node or hot-volume counts at physically relevant thresholds;
- volume-weighted temperature or energy proxies;
- melt-pool width/depth and cooling rate when the mesh and data support those claims.

A short benchmark supports only the tested time and path segment. State what remains unexecuted.

## 7. Physical validity boundary

Before accepting a temperature target, compare it with the highest temperature covered by conductivity, density, specific heat, latent heat, elasticity, plasticity, and expansion data. Abaqus may extrapolate or hold terminal table values beyond the measured range; a numerically calibrated peak outside that range is not automatically a high-confidence physical prediction.

Do not use unrealistically strong convection or radiation to mask an overpowered heat source. Calibrate against experimental track width/depth, thermal history, or another accepted physical observable when available.
