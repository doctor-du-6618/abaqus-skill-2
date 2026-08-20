# Controlled CAE edits

Use this workflow when the requested change is narrower than mesh replacement: step controls, boundary conditions, constraints, loads, output requests, jobs, or keyword blocks.

## 1. Write a change contract

Before editing, record:

- authoritative master path and hash;
- destination path;
- target model and object names;
- attributes allowed to change;
- values and repositories that must remain unchanged;
- whether existing Job objects must be preserved, replaced, or omitted.

Do not expand a numerical-sensitivity edit into a geometry, material, load, output, or thermal-history change.

## 2. Snapshot the baseline

Inventory names, ordering, types, regions, suppression, propagation, and critical values. For step-control edits, export every step's procedure type, time period, initial/minimum/maximum increment, maximum increment count, stabilization controls, and output timing.

For coupled sensitivity studies, change only one branch at a time. For example, keep the thermal model and ODB fixed while refining stress-step increments so any result change is attributable to the mechanical time discretization.

## 3. Edit a copy and prove the delta

Open a byte-for-byte copy of the master, apply only the contracted attributes, save under a new name, reopen it, and produce a before/after machine-readable comparison. A successful `saveAs` is not validation.

The comparison must show both:

- every intended changed value;
- zero unapproved changes to models, parts, instances, materials, sections, steps, sets, surfaces, loads, fields, interactions, constraints, BCs, outputs, amplitudes, and jobs.

## 4. BC and constraint audit

CAE API visibility is release- and class-dependent. A BC may not expose `getValuesInStep`, and its region may not resolve through ordinary `sets` even though it is valid through `allSets` or an internal repository.

Audit in layers:

1. enumerate `boundaryConditions`, `constraints`, interactions, connectors, and equations separately;
2. inspect region references through `setName`, `internalSetName`, `surfaceName`, and `internalSurfaceName`;
3. resolve against `sets`, `allSets`, `allInternalSets`, `surfaces`, `allSurfaces`, and `allInternalSurfaces`;
4. record node/element labels and coordinate bounds for small critical regions;
5. generate an INP and verify the actual `*BOUNDARY`, `*COUPLING`, `*KINEMATIC`, `*EQUATION`, connector, and interaction keywords;
6. compare activation, modification, and deactivation in every relevant step.

An empty `model.constraints` repository does not prove the model is unconstrained; fixation may be implemented by BCs, interactions, connectors, or equations. Conversely, a named BC object with an unresolved API region is not evidence that the generated input is valid.

## 5. Increment-control edits

Treat `initialInc`, `minInc`, `maxInc`, `maxNumInc`, and step time as different controls.

- `maxNumInc` is an abort ceiling, not a speed control.
- A smaller initial or maximum increment may alter a path-dependent mechanical response and should be framed as a sensitivity study unless convergence evidence supports it.
- Preserve terminal cooling behavior and extra transition steps by name and role; do not select steps only with an incomplete regex.
- Compare generated `*STATIC` or `*HEAT TRANSFER` data for every targeted step.

If an existing thermal ODB is reused, validate every temperature mapping against that exact ODB after the edit.

## 6. Keyword-block edits

Keyword-block surgery can leave `*Conflicts` markers that prevent input processing even when CAE saving succeeds. Regenerate the INP and reject any conflict marker. Prefer supported CAE APIs when they preserve the intended object model; when keyword editing is necessary, document the exact inserted, replaced, and removed blocks.

## 7. Delivery evidence

Deliver the new CAE plus a concise report containing source/destination hashes, authorized changes, preserved-object comparison, reopen result, generated-INP audit, ODB mapping result when applicable, and unexecuted limitations.
