# abaqus-skill

Evidence-driven Abaqus/CAE model editing and validation for Codex.

`abaqus-skill` is a reusable Codex skill for mesh replacement, controlled CAE edits, sequential thermal–stress diagnosis, and LPBF moving-heat-source validation. It treats the original `.cae` as the authoritative source of analysis settings and verifies changes through CAE reopening, generated-input audits, and solver/result evidence.

中文说明：这是一个面向 Abaqus/CAE 网格替换、增材制造逐层激活以及热—应力耦合诊断的 Codex 技能。它强调保留旧 CAE 中的材料、步骤、载荷、边界条件、相互作用、输出请求和对象名称，而不是从新 INP 重新搭建整个模型。

## Features

- Replace an orphan mesh while retaining the master CAE structure.
- Preserve model, part, instance, material, section, step, load, BC, interaction, field, and output names.
- Add or remove deposition layers using terminal-step inheritance.
- Maintain analysis-specific element families such as `C3D8R` and `DC3D8R`.
- Rebuild named sets, picked sets, and element-face surfaces on the new instance.
- Validate Model Change, heat flux, BC propagation, surface regions, and predefined temperatures.
- Audit `BSTEP/BINC/ESTEP/EINC` mappings for ODB-driven stress analyses.
- Diagnose Abaqus/Standard convergence failures using `.inp`, `.msg`, `.sta`, `.dat`, and `.odb` evidence.
- Make narrow step-control, BC, constraint, job, or keyword edits with an explicit before/after contract.
- Diagnose and accelerate LPBF `DFLUX` models without conflating increments, cutbacks, output frames, I/O, subroutine calls, and CPU overhead.
- Reject generated inputs containing `*Conflicts` or invalid nonpositive `BINC` parameters.
- Generate validation reports and reproducible transformation scripts.

## Repository structure

```text
abaqus-skill/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── coupled-validation.md
│   ├── controlled-cae-edits.md
│   ├── lpbf-moving-heat-source.md
│   └── mesh-replacement-patterns.md
└── scripts/
    ├── audit_generated_inp.py
    └── inspect_inp_mesh.py
```

## Installation

### Install with Codex

Ask Codex to install the skill from this repository:

```text
Use $skill-installer to install the skill from
https://github.com/doctor-du-6618/abaqus-skill
```

Restart Codex or begin a new task after installation if the skill does not appear immediately.

### Manual installation

Clone or copy this repository to your Codex skills directory:

```text
$CODEX_HOME/skills/abaqus-skill
```

Typical Windows location:

```text
C:\Users\<username>\.codex\skills\abaqus-skill
```

The installed directory must contain `SKILL.md` at its root.

The folder name, `SKILL.md` frontmatter name, and UI `display_name` are all exactly `abaqus-skill`. Do not replace the UI name with an expanded title.

## Requirements

- Codex with local skill support.
- A compatible local Abaqus/CAE installation for CAE inspection, editing, and validation.
- An available Abaqus license.
- Python 3 for the standalone INP auditing scripts. The scripts use only the Python standard library.

This repository does not include Abaqus, solver binaries, licenses, CAE models, ODB files, or proprietary simulation data.

## Usage examples

Invoke the skill explicitly in Codex:

```text
Use $abaqus-skill. Open my existing CAE as the master, replace its mesh with the new INP,
preserve all analysis settings, and deliver a validated replacement CAE.
```

```text
Use $abaqus-skill to add one deposition layer to this coupled thermal-stress model.
Make the new final cooling step inherit the old terminal settings and audit all ODB mappings.
```

```text
Use $abaqus-skill to diagnose “Too many attempts made for this increment” using the
failed and successful INP, MSG, STA, DAT, and ODB files.
```

中文示例：

```text
使用 $abaqus-skill，以旧 CAE 为主文件，把新的 INP 网格替换进去，保留原有材料、
分析步、载荷、边界条件、相互作用和输出设置，并生成验证报告。
```

## Standalone mesh inspection

Inspect an INP and detect candidate layer bands:

```bash
python scripts/inspect_inp_mesh.py model.inp --axis z --component part --json mesh-report.json
```

The report includes:

- node and element counts;
- element-type histogram;
- coordinate bounds;
- ELSET and NSET sizes;
- candidate layer centroid bands and membership counts.

## Generated-INP audit

Audit a generated Abaqus input file against a JSON acceptance contract:

```bash
python scripts/audit_generated_inp.py validation.inp contract.json --json audit-report.json
```

The contract can verify step order, time and increment controls, body heat flux, temperature-mapping policy, keyword counts, required patterns, and forbidden importer-generated names. The auditor always rejects `*Conflicts` and nonpositive explicit `BINC` values. See `references/mesh-replacement-patterns.md` for an example contract.

## Safety and validation principles

- Always work on a copy of the master CAE.
- Never treat a raw mesh INP as the authoritative source of analysis settings.
- Confirm physical intent when the new mesh changes the activation-layer count.
- Do not accept a CAE merely because it saves or opens.
- Resolve every region-based object to a nonempty set or surface on the new instance.
- Reopen the scratch and final CAEs in Abaqus noGUI mode.
- Generate thermal and stress validation INPs with consistency checking enabled.
- Keep temporary jobs and import models out of the delivered CAE.
- Revalidate ODB endpoint increments after every thermal rerun.

## Important limitation

A structurally valid CAE is not automatically an execution-validated coupled workflow. If the referenced thermal ODB has not yet been regenerated, new temperature mappings and endpoint increments remain provisional until checked against the actual ODB.

## License

Released under the [MIT License](LICENSE).

## Disclaimer

This is an independent workflow skill and is not affiliated with or endorsed by Dassault Systèmes. Always review generated models and validation reports before production simulation.
