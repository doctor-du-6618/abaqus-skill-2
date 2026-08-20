# Mesh replacement patterns

## Contents

1. Evidence hierarchy
2. Safe orphan-mesh replacement
3. Layer inference and confirmation
4. Terminal-step inheritance
5. Set and surface reconstruction
6. API failure patterns and fixes
7. Validation sequence
8. Worked 22-to-23-layer pattern
9. Generated-INP audit contract

## 1. Evidence hierarchy

Use evidence in this order:

1. Explicit user acceptance criteria or corrections.
2. Master CAE object structure and state history.
3. New mesh INP for mesh facts only.
4. Master journal/replay for creation order and GUI selections.
5. Master-generated job INP for keyword values and propagation.
6. Existing successful result and solver files for actual behavior.

Do not rebuild the complete model from a generated INP when exact CAE object structure matters. Importing a full job INP commonly changes names and splits one propagating object into many importer-generated objects.

## 2. Safe orphan-mesh replacement

Prefer this pattern inside a copy of the master model:

```python
a.features.changeKey(fromName='PART-1-1', toName='PART-1-old-1')
model.parts.changeKey(fromName='PART-1', toName='PART-1-old')

new_part = model.Part(name='PART-1', objectToCopy=mesh_source_part)
new_inst = a.Instance(name='PART-1-1', part=new_part, dependent=ON)

# Recreate all named regions on new_inst here.
# Recreate or rebind BCs, loads, interactions, fields, and surfaces here.

del a.features['PART-1-old-1']
del model.parts['PART-1-old']
a.regenerate()
```

Create replacement regions before deleting the old instance. Existing objects often resolve same-named assembly regions correctly, but verify this in a generated INP. Recreate an object when its region or state cannot be safely edited.

Use separate imported mesh sources for analysis-specific element families. A raw mechanical INP can be mechanically converted into a temporary thermal mesh input only when topology is identical and the master confirms the thermal element family.

## 3. Layer inference and confirmation

Derive candidate layers from all available evidence:

- element centroid coordinate along build direction;
- distinct interface node coordinates;
- component element sets;
- old layer-set geometry and topology;
- downstream Model Change and load references;
- element type changes and physical interfaces.

Require every proposed layer to be nonempty. Require layer sets to be mutually disjoint and their union to equal the deposition component.

If the master has 22 activation layers and the new mesh has 23 clear bands, stop and ask whether the model should gain a physical layer. Do not silently merge bands or add steps.

## 4. Terminal-step inheritance

Separate ordinary layer behavior from terminal behavior.

For an added layer:

1. Snapshot old final deposition and cooling settings.
2. Convert the old final cooling step to the ordinary cooling pattern.
3. Add the new deposition step using the ordinary deposition pattern.
4. Add the new cooling step using the old terminal cooling settings.
5. Add the new layer load and Model Change.
6. Move final BC/load/interaction deactivation to the new terminal step.
7. Extend outputs and predefined fields without multiplying objects.
8. Extend thermal ODB mappings and mark frame/increment values provisional until the new ODB exists.

For a removed layer, perform the inverse: remove only the deleted layer's objects and make the new last layer inherit the old final-layer settings and terminal states.

## 5. Set and surface reconstruction

### Sets

Use label sequences from the new instance:

```python
elements = inst.elements.sequenceFromLabels(tuple(labels))
a.Set(name='l23', elements=elements)
```

Validate counts, disjointness, union coverage, coordinate bands, component identity, and new-instance ownership.

### Picked sets

Recreate a picked set as an ordinary named set first. Bind or recreate its dependent BC/field. Delete the old instance. Then mark it internal:

```python
a.markSetInternal(setName='_PickedSet34', internalSet=True)
```

After marking, use `allInternalSets` for validation; repository visibility can differ between Abaqus releases.

### Orphan-mesh surfaces

Classify exterior faces by counting face ownership from element connectivity. One owner indicates an exterior face; two owners indicate an internal interface. Use component, centroid, and outward normal to categorize faces.

Create an Abaqus surface with face keywords:

```python
kwargs['face3Elements'] = inst.elements.sequenceFromLabels(tuple(face3_labels))
a.Surface(name='_PickedSurf29', **kwargs)
```

Do not use `side3Elements` for orphan mesh element surfaces. Mark picked surfaces internal only after dependent interactions are bound and the old instance is gone.

## 6. API failure patterns and fixes

| Failure | Cause | Fix |
|---|---|---|
| `TypeError: keyword error on side3Elements` | Orphan mesh surface uses face keywords | Use `face1Elements` through `face6Elements` |
| Picked set becomes unavailable after old-instance deletion | Region marked internal too early or remained feature-dependent | Recreate as ordinary, bind object, delete old feature, then mark internal |
| `Model` has no `writeInput` | Input writing belongs to Job in this Abaqus release | Create a temporary Job and call `writeInput`; do not save the Job |
| `HeatTransferStep` rejects `nlgeom` | Mechanical-only or release-specific argument | Use the inspected HeatTransferStep signature |
| BC has no `resetToPropagated` | Method is unavailable for that BC class/release | Recreate the same-named BC and apply terminal deactivation explicitly |
| Imported model has `BODYFLUX-*`, `Field-*`, or `Model_Change-*` | Full job INP was used as model source | Retain copied master models; import only the mesh part |
| CAE saves but later objects are invalid | Regions still reference deleted/old instance membership | Reopen, resolve every region, and generate validation INPs |

## 7. Validation sequence

1. Save a scratch CAE.
2. Close and reopen it in Abaqus noGUI mode.
3. Assert exact model/part/instance names and absence of old or temporary objects.
4. Check mesh counts, element-type histograms, section coverage, sets, and surfaces.
5. Resolve every region-based object to a nonempty set or surface.
6. Create temporary validation Jobs for every model and call `writeInput(consistencyChecking=ON)`.
7. Audit generated keywords for materials, steps, controls, loads, BC states, Model Change, outputs, and temperature mappings.
8. Search for unexplained importer names.
9. Close without saving the temporary Jobs.
10. Save the final CAE and reopen that exact final path once more.

## 8. Worked 22-to-23-layer pattern

Validated structure from a successful replacement:

- Master: two models, 22 deposition/cooling pairs, terminal `c22` of 1000 s.
- New mesh: 29,050 nodes, 26,104 elements, 23 deposition bands of 888 elements, plus 5,680 substrate elements.
- Stress element type: `C3D8R`; thermal element type: `DC3D8R`.
- New sequence: `l1/c1 ... l22/c22, l23/c23`.
- Ordinary `c22`: 12 s, maximum increment 2 s.
- New terminal `c23`: inherited 1000 s, maximum increment 100 s.
- New thermal load: `h23`, body heat flux `4.0E8`, active in `l23`, deactivated in `c23`.
- New Model Change: stress `Int-24` with strain, thermal `Int-27` without strain.
- Final BC deactivation moved to `c23`.
- Stress temperature mappings extended to thermal steps 47 and 48.
- Final CAE contained no Job objects and passed reopen plus input-generation validation.

Treat these values as an example of the inheritance pattern, not universal constants.

## 9. Generated-INP audit contract

Pass a JSON contract to `scripts/audit_generated_inp.py`. Example:

```json
{
  "required_steps": ["c22", "l23", "c23"],
  "step_controls": {
    "c22": {"time_period": 12.0, "maximum_increment": 2.0},
    "l23": {"time_period": 0.000025, "maximum_increment": 0.00001},
    "c23": {"time_period": 1000.0, "maximum_increment": 100.0}
  },
  "temperature_mappings": {
    "c22": {"bstep": 46, "einc": 23},
    "l23": {"bstep": 47, "einc": 13},
    "c23": {"bstep": 48, "einc": 34}
  },
  "temperature_mapping_policy": {
    "exactly_one_per_step": true
  },
  "body_heat_flux": {
    "l23": {"region": "l23", "magnitude": 400000000.0}
  },
  "required_patterns": ["Interaction: Int-27", "Model Change, add"],
  "forbidden_patterns": ["BODYFLUX-[0-9]+", "Model_Change-[0-9]+"]
}
```

Adapt expected names, values, and mappings to the accepted model contract. Do not copy example increment numbers without checking the actual thermal ODB.

For sparse-output workflows that intentionally omit increment numbers, replace the per-step `einc` expectations with `"omit_binc": true` and `"omit_einc": true` in `temperature_mapping_policy`. Add `expected_total` or `keyword_counts` when the full-model contract fixes those counts. The auditor always rejects `*Conflicts` and nonpositive explicit `BINC` values.
