# LPBF path-resolved moving-heat-source construction

Use this reference when converting layerwise equivalent heating to a `DFLUX`-driven moving volumetric source while preserving a sequential thermal-stress analysis.

## 1. Establish the model facts before redesigning the source

Use two complementary representations:

- inspect the live CAE object model with the Abaqus Python API to recover models, parts, sets, materials, steps, loads, interactions, predefined fields, jobs, and propagation/deactivation states;
- generate job INPs with `Job.writeInput` and inspect the submitted keywords, including `*MODEL CHANGE`, `*DFLUX`, `*TEMPERATURE`, step times, file paths, and output requests.

Journal and replay files are supporting history, not proof of the current model state. Preserve the existing geometry, mesh, materials, activation sequence, preheat, convection, radiation, and constraints unless the request explicitly changes them.

Record the working unit system explicitly. Abaqus supplies no units. Convert laser power, conductivity, specific heat, density, and volumetric flux into one consistent system before implementing the source. For a `t-mm-s-mW` model, watts become `10^3 mW` and a volumetric source is expressed in `mW/mm^3`.

## 2. Choose and normalize the source model

Choose source complexity from mesh resolution, beam size, penetration physics, and the observable available for calibration. A parameter-rich source is not automatically more physical.

A conical Gaussian volumetric source is a useful LPBF engineering model when finite penetration and radius contraction with depth matter but a weld-style front/rear asymmetry is not justified. One normalized form is:

`q(r,z) = [6 eta s P / (pi h (re^2 + re ri + ri^2))] exp[-2 r^2 / r(z)^2]`

where `P` is nominal power, `eta` absorptivity, `s` a declared equivalent-layer or calibration factor, `h` source depth, and `re`/`ri` the top and bottom radii. Define `r(z)` consistently with the cone geometry. Confirm analytically or numerically that volume integration gives `eta s P` over the implemented support.

Do not hide geometry-dependent power changes inside an unnormalized amplitude. A radius or depth edit should not change total absorbed power unless that change is deliberate and reported.

If one finite-element layer represents multiple physical powder layers, choose explicitly among:

- an energy-equivalent factor;
- multiple physical scans within one numerical layer;
- mesh refinement to resolve the physical layers.

An energy factor preserves only a selected integral quantity. It does not reproduce separate recoating, remelting, or thermal histories.

## 3. Compile the scan path from geometry

Derive path duration rather than inheriting the old equivalent-heating step time.

For each numerical layer:

1. derive the build footprint and scan bounds from the actual CAE/mesh geometry;
2. choose the nominal hatch spacing and compute an integer track count;
3. recompute the realized spacing so the first and last tracks cover the intended bounds without placing the last track outside the region;
4. alternate track direction to form a serpentine path;
5. include laser-off repositioning time using a declared jump speed;
6. rotate the raster direction between layers when required, such as alternating X and Y for 90-degree rotation;
7. calculate the total step duration from heated travel plus laser-off jumps.

Store nominal and realized hatch spacing separately. Report track count, path length, scan time, jump time, and layer rotation. Do not infer scan bounds from hard-coded coordinates when the CAE geometry can provide them.

Relate time resolution to distance:

`travel_per_increment = scan_speed x maximum_increment`

Compare this distance with element size and beam diameter. A useful initial target can be a fraction of the in-plane element size, but it is still subject to time-increment sensitivity testing and `DELTMX` cutbacks.

## 4. Implement a defensive DFLUX contract

At every call, initialize both returned flux components to zero before any early return. Then:

- accept only the intended flux type, such as `JLTYP=1` for body flux, when the model is designed for `BFNU`;
- map `KSTEP` to the physical scan layer from the verified CAE step order rather than assuming a universal numbering scheme;
- return zero in initialization, preheat, cooling, and other non-scan steps;
- use `TIME(1)` for time within the current step unless a different basis is explicitly required;
- resolve the active track, direction, along-track position, and laser-off jump state from time;
- use `COORDS` to compute radial distance and depth from the moving source center and current layer top;
- reject points outside the intended depth or radial support before evaluating the exponential;
- apply the normalized volumetric flux only inside the support.

A finite radial cutoff can reduce subroutine cost, but quantify its omitted energy. For a Gaussian cutoff expressed as a multiple of local radius, document the multiple and verify the cropped source against an uncropped or wider-support calculation at matched times.

Keep process and calibration inputs together near the top of the subroutine or in one clearly identified configuration block: power, absorptivity, equivalent-layer factor, scan speed, hatch spacing, source radii, depth, jump speed, geometric bounds, and any segment-specific scale factors.

## 5. Rebuild the thermal and stress models in lockstep

Prefer transforming copies of the authoritative models instead of recreating unrelated geometry or analysis objects.

For the thermal model:

- remove or deactivate the old layerwise uniform heat loads without disturbing activation and cooling logic;
- create a verified region that contains only the integration-point domain the moving source may heat;
- apply one user-defined body flux when propagation is intentional, and make the subroutine or explicit `OP=NEW` states turn it off outside scan steps;
- replace scan-step times with path-derived durations;
- set initial and maximum increments plus `DELTMX` from resolution and convergence evidence, not from the old equivalent-heating duration;
- bind the thermal job to the intended user-subroutine source.

For the stress model:

- preserve the same deposition/cooling step order and physical durations as the thermal model;
- keep activation, constraints, and terminal cooling behavior synchronized;
- point imported temperatures to the regenerated thermal ODB using a portable path policy appropriate to the working directory;
- map each stress step to its corresponding thermal step.

Do not copy old automatic increment numbers into new ODB mappings. When supported and verified for the target Abaqus release, omit `BINC/EINC` so the specified thermal step supplies its last available increment. Never use `BINC=0` as an automatic sentinel in Abaqus 2022. If explicit positive increments are required, resolve them only after the new thermal ODB exists and validate every reference against its frames.

## 6. Validate in increasing-cost gates

Use this minimum ladder:

1. reopen the transformed CAE and inventory the preserved and changed objects;
2. generate thermal and stress INPs with consistency checking;
3. audit `BFNU`, step times, activation states, ODB file/step mappings, output requests, and the absence of `*Conflicts`;
4. compile and link the user subroutine with the complete thermal input;
5. run `datacheck` and classify every warning;
6. run a single-track or partial-layer case and confirm source position, peak location, and laser-off jumps;
7. run one full layer, then a small multilayer build to check overlap, remelting, heat accumulation, and cooling;
8. perform time-increment and mesh sensitivity studies;
9. calibrate against melt-pool width/depth or another accepted observable;
10. run the full thermal build, validate the ODB mappings, and only then run sequential stress.

`datacheck` proves input processing and usually the user-subroutine compile/link path, set/element/step validity, and keyword compatibility. It does not validate melt-pool dimensions, peak temperature, residual stress, mesh convergence, time resolution, or material extrapolation.

Before accepting the stress result, audit the temperature ranges of elasticity, plasticity, expansion, conductivity, specific heat, density, and phase-change data. A thermal solution above the highest supported material temperature is not automatically a defensible residual-stress prediction.

## 7. Submission and rerun checklist

- DFLUX geometry and scan bounds match the current CAE build region.
- Source power, absorptivity, layer-equivalence policy, scan speed, hatch, radii, depth, and jump speed match the intended case.
- Thermal and stress step names, order, durations, activation states, and terminal behavior agree.
- The thermal job name/path matches every temperature-import reference.
- No stale hard-coded automatic increment numbers remain unless validated against the final thermal ODB.
- The user-subroutine path and compiler/linker environment are available.
- The thermal ODB exists and contains every mapped step/frame before stress submission.
- Output frequency and available disk space are appropriate for the expected increment and frame count.
- Compile/link, `datacheck`, and at least one reduced physical run have passed.

## 8. Reference implementation values are evidence, not defaults

One completed Abaqus/Standard 2022 conversion used a `t-mm-s-mW` model, 23 numerical layers, `DC3D8R`/`C3D8R` thermal-stress mesh pairing, a nominal 140 W beam, absorptivity 0.35, 800 mm/s scan speed, 0.070 mm nominal hatch, 0.040/0.020 mm top/bottom radii, 0.080 mm penetration depth, 3000 mm/s jump speed, and a 25 microsecond maximum increment. Odd/even numerical layers used X/Y serpentine rasters, and the stress mapping selected the last available increment of each paired thermal step.

These values demonstrate a verified construction pattern only. Recompute geometry, path timing, units, source support, controls, and calibration for every new model.
