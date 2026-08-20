# abaqus-skill

`abaqus-skill` 是一个面向 Abaqus/CAE 模型修改、诊断与交付验证的 Codex skill。它强调“证据驱动”：以原始 CAE 保存的分析意图为基准，同时使用 Abaqus Python API、生成的 INP、求解器日志和 ODB 结果交叉验证实际行为。

这个 skill 适合处理以下任务：

- 替换孤立网格，同时保留材料、截面、集合、表面、步骤、载荷、边界条件和输出请求；
- 增加或删除沉积层，并同步调整激活、冷却和终止步骤；
- 对步骤控制、约束、边界条件、载荷或关键字块进行可审计的局部修改；
- 检查顺序热—力耦合中的 ODB 温度映射与收敛问题；
- 构建、标定、诊断或加速 LPBF `DFLUX` 移动热源模型；
- 审计 Abaqus 生成的 INP，并交付经过复开和关键字验证的 CAE。

## 快速使用

在 Codex 中直接点名 skill，并说明目标文件、允许修改的范围和期望输出。例如：

```text
使用 $abaqus-skill，把 new-mesh.inp 替换进 master.cae。
保留现有材料、分析步和边界条件，输出 revised-model.cae，并生成验证报告。
```

```text
使用 $abaqus-skill，检查这个顺序热—力模型为什么在温度导入后不收敛。
只做诊断，不要修改 CAE。
```

```text
使用 $abaqus-skill，把现有整层均匀热流改造成蛇形扫描的锥形高斯 DFLUX。
热模型和应力模型的步骤时间与温度映射必须同步。
```

如果请求中没有显式写出 `$abaqus-skill`，当任务明显属于上述 Abaqus 工作流时，Codex 也可以自动选择该 skill。

## 建议提供的文件

修改 CAE 时，至少需要：

- 权威原始 `.cae` 文件；
- 期望的输出目录和文件名；
- 能够打开原模型的 Abaqus 版本。

根据任务类型，建议进一步提供：

- 网格替换：新网格 `.inp` 和部件对应关系；
- 顺序耦合诊断：热/力模型、热 ODB、失败的 `.msg`、`.sta`、`.dat` 和生成的 INP；
- LPBF 移动热源：热/力 CAE、`DFLUX` 源码、扫描几何、材料温度范围、求解日志和标定目标；
- 局部修改：允许变化的对象、属性和基线值；
- 复现与核查：`.jnl`、`.rpy`、`.log`、`.rec` 以及成功算例的结果文件。

缺少 journal 或 replay 不一定阻止检查，但缺少权威 CAE 会阻止实际 CAE 修改。

## 工作模式

| 模式 | 典型任务 | 主要验证证据 |
| --- | --- | --- |
| 网格替换 | 用新 INP 替换孤立网格，重建集合和表面 | CAE 清单、网格统计、热/力 INP |
| 层数变更 | 新增或删除沉积层和步骤对 | 步骤序列、激活状态、终止继承 |
| 受控修改 | 调整增量、BC、约束、载荷或关键字 | 修改前后对象快照与 INP 差异 |
| 顺序耦合 | 温度 ODB 映射、热—力不收敛诊断 | ODB 步/帧、映射关键字、求解日志 |
| LPBF 构建 | 整层热源改为路径分辨的 `DFLUX` | 能量归一化、扫描时间、编译和 datacheck |
| LPBF 标定/加速 | 熔池标定、调用域裁剪、输出和增量优化 | 匹配物理时间的 A/B 对比与误差指标 |

## LPBF 移动热源能力

新增的 LPBF 构建流程覆盖从等效层加热到真实扫描路径的完整改造：

1. 用 Abaqus API 和生成的 INP 盘点现有模型；
2. 明确单位制、网格尺度、光斑尺度和材料有效温度范围；
3. 选择并归一化锥形高斯体热源；
4. 根据实际成形区生成蛇形路径、实际道间距、跳转时间和层间旋转；
5. 在 `DFLUX` 中处理 `KSTEP`、`TIME(1)`、`COORDS`、激光关闭区间和空间截断；
6. 同步重构热分析与应力分析的步骤时间和激活序列；
7. 按热分析步骤映射温度，避免继承旧算例的自动增量号；
8. 依次完成 CAE 复开、INP 审计、编译、`datacheck`、单道、单层、少层和完整计算验证。

参考案例中的 140 W、23 个数值层、25 微秒最大增量等数据仅用于说明已验证的构建模式，不是新模型的默认参数。

## 内置检查脚本

### 检查原始 INP 网格

```powershell
python scripts/inspect_inp_mesh.py model.inp --axis z --json mesh-report.json
```

可检查节点、单元、单元类型、坐标范围、ELSET 和候选层带。使用 `--component` 可以只在指定单元集中识别层。

### 审计 Abaqus 生成的 INP

```powershell
python scripts/audit_generated_inp.py generated.inp acceptance-contract.json --json audit-report.json
```

该脚本根据小型 JSON 验收合同检查关键对象、层集合、映射参数、异常导入器命名、`*Conflicts` 和终止步骤行为。

## 安全与交付原则

- 不直接把唯一原始 CAE 作为活动工作文件；先制作逐字节工作副本。
- 新网格只对节点、单元、连接关系、拓扑和部件归属具有权威性，不覆盖原 CAE 的分析意图。
- 不把“看起来合理”当作验证；无法用证据映射的设置应停止并报告。
- 不把 `datacheck` 通过解释为物理模型已经标定。
- 不在未获请求时自动提交耗时的完整分析。
- 最终 CAE 不应包含临时模型、旧实例、临时区域或验证 Job。

典型交付物包括：

- 新名称保存的最终 `.cae`；
- 简洁的验证报告；
- 生成并审计过的热/力 INP；
- 对非平凡改造可复现的 Abaqus Python、`DFLUX` 或配置文件。

## 目录结构

```text
abaqus-skill/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── controlled-cae-edits.md
│   ├── coupled-validation.md
│   ├── lpbf-moving-heat-source-build.md
│   ├── lpbf-moving-heat-source.md
│   └── mesh-replacement-patterns.md
└── scripts/
    ├── audit_generated_inp.py
    └── inspect_inp_mesh.py
```

文件职责：

- [`SKILL.md`](SKILL.md)：Codex 执行时的主入口、共同约束和模式路由；
- [`references/`](references/)：只在相应任务中读取的详细工作流；
- [`scripts/`](scripts/)：可重复执行的确定性检查工具；
- [`agents/openai.yaml`](agents/openai.yaml)：skill 的界面名称和默认提示。

## 维护说明

`abaqus-skill` 是规范名称。skill 文件夹名、`SKILL.md` 中的 `name` 和 `agents/openai.yaml` 中的 `display_name` 应始终保持一致。

更新 skill 后，应至少检查：

- YAML frontmatter、名称和描述有效；
- README 与 `SKILL.md` 中引用的文件均存在；
- 新增脚本能够实际运行；
- 案例经验没有被错误提升为所有 Abaqus 模型的通用规则；
- 工作区版本与已安装版本一致。
