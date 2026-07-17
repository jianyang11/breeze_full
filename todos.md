# BREEZE 执行 todos

最后更新：2026-07-17 Asia/Shanghai

工作根目录：`/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2`

Python 环境：`breeze/.venv-breeze/bin/python` (`3.12.13`)。所有 Python 命令必须使用该解释器。

> 收口决定（2026-07-14）：L1.1--L1.9 与 L2.1--L2.9 全部 **deferred（投稿后工作）**。理由：投稿前不开启新的框架重构工程；这些计划不得被描述为本稿已实现的方法或结果。

## F6. Fig. 6 round-level 证据冻结、正式集成与 PR #2 合并（2026-07-17）

> 范围锁定：仅对本地 `breeze/runs/rescreen_v2_full/records/`
> 归档记录做 SHA-256、聚合和绘图；0 训练、0 API、不改写任何冻结实验输出。

- [x] F6.1 核对工作树、`origin/main` 与 PR #2 头提交，确认 PR 基于当前 `main`。
- [x] F6.2 审计 PR #2 的图件、图注、测试与 PDF，确认 Fig. 6 仍是显式 blocker，未被推断数据或占位图遮掩。
- [x] F6.3 盘点本地 round JSON：数量必须恰为 450，三类各 150 slots，候选轮次只能为 $K=0,1,2,3$。
- [x] F6.4 实现可重入的冻结脚本：严格解析 JSON、逐文件 SHA-256、记录文件大小与 class/slot，禁止覆盖已有不同冻结内容。
- [x] F6.5 按每个 slot 的首个 `feasible=true` 聚合首次通过轮次，断言 `selected` 与首次通过候选完全一致。
- [x] F6.6 与冻结 `slot_summary.csv` 逐槽核对 `accepted_before_diversity`、`n_candidates` 和 `n_feasible_expansions`，断言 450 slots / 286 admitted。
- [x] F6.7 在 `breeze/results/admission_round_freeze_2026-07-17/` 落盘 manifest、slot aggregate、$K=0..3$ 累计表与机器可读校验报告。
- [x] F6.8 用冻结聚合表绘制 Fig. 6 累计准入曲线；图中区分三类与总体，如实显示每轮边际增量和 $K=3$ 时 286/450。
- [x] F6.9 导出可编辑 PDF/SVG、600-dpi TIFF 和 300-dpi PNG，执行尺寸、字体、灰度/色盲和 source-manifest 哈希 QA。
- [x] F6.10 用新 Fig. 6 替换正式 `acceptance_k.pdf`，重写正文描述与图注，明确这是 slot-level 总体计数而非独立重复的统计推断。
- [x] F6.11 替换 Fig. 6 blocker 测试，添加冻结完整性、曲线单调性、类别计数和输出哈希测试。
- [x] F6.12 用 `.venv-breeze` 运行全部相关测试、重编 CAS PDF，按 `pdf` skill 逐页渲染核查 21 页终稿。
- [x] F6.13 审查 diff 和待提交列表，排除用户未跟踪原件/试验目录；将 Fig. 6 修正推送到 PR #2 分支。
- [ ] F6.14 合并 PR #2 到 `main`、推送 `origin/main`，再次核对远端提交、图件哈希和 PDF 页数。

## R. CAS 终稿证据约束重构（2026-07-15）

> 执行规范：以 961 行 `breeze/paper/main_cas.tex` 为结构骨架，以
> `analysis/evidence_ledger.md`、冻结报告和脚本生成表格为唯一事实来源；
> 写作阶段不调用生成 API，不重跑冻结实验，不把未进入台账的结果写入正文。

### R0. 启动、同步与约束冻结

- [x] R0.1 读取本轮 `breeze_paper_rewrite_prompt.md`，将其视为终稿硬约束。
- [x] R0.2 读取并应用 `awesome-ai-research-writing`、`nature-figure`、
  `huashu-nuwa` 和 `pdf` skills；图表后端冻结为 Python。
- [x] R0.3 读取仓库 `AGENTS.md`，确认禁止 fallback/hack/后处理遮掩，
  并确认完成后必须审查 diff、提交、推送。
- [x] R0.4 `git fetch origin main` 后核对本地 `HEAD` 与 `origin/main` 均为
  `5aa92cd`；保留所有未跟踪实验目录和原始副本，不读取为正式证据。
- [x] R0.5 核对 `main_cas.tex` 为 961 行骨架、`main.tex` 为 347 行证据口径稿。
- [x] R0.6 读取 `analysis/evidence_ledger.md`，冻结允许与禁止的 claim。
- [x] R0.7 逐项建立“正文 claim -> 台账行 -> 冻结 CSV/报告 -> 生成表格”映射，
  出现数值冲突时停止对应段落并记录 blocker。

### R1. 对标论文与领域叙事蒸馏

- [x] R1.1 盘点已有本地对标 PDF、DOI 页面和文献审计文件，区分已核验、
  仅元数据核验和未核验来源。
- [x] R1.2 用 PDF 视觉检查 BearGen/AEI 的 workflow、责任边界、
  waveform/spectrum、few-shot bar 和辅助嵌入图式。
- [x] R1.3 核验 1--2 篇 physics-informed GAN/diffusion 轴承论文的正式元数据、
  数据集、协议、baseline、指标和图式。
- [x] R1.4 核验近两年 AEI/MSSP synthetic augmentation 论文及
  Randall--Antoni 教程来源，不使用搜索摘要代替正文证据。
- [x] R1.5 按女娲主题蒸馏法提取领域共识、论文间分歧、叙事顺序、图式逻辑、
  反模式和诚实边界；不模仿原句。
- [x] R1.6 生成/更新 `analysis/venue_alignment_table.md`，字段至少包括论文、
  方法、数据集、工况、baseline、指标、图表风格、可借鉴点和核验级别。
- [x] R1.7 从对标中冻结 BREEZE 的叙事模板：训练成本痛点 -> recipe-as-data ->
  renderer/verifier 责任边界 -> 正结果 -> 预注册边界。

### R2. 数字、表格与引用唯一来源

- [x] R2.1 审计 `scripts/build_paper_tables.py` 输入路径、列名、排序、统计字段和
  输出文件，确认不读取未冻结/未入台账结果。
- [x] R2.2 在 `breeze/.venv-breeze/bin/python` 下重新生成
  `breeze/paper/generated/*.tex`，检查运行日志和返回码。
- [x] R2.3 将四个 generated 表与其冻结 CSV/报告逐格复核；禁止手抄数值。
- [x] R2.4 检查正文中所有裸写 Accuracy、Macro-F1、delta、p/q、seed、shot、
  synthetic budget 数字，能表驱动的改为脚本输入。
- [x] R2.5 审计 `references.bib` 的 DOI、题名、作者、期刊、年份和重复项。
- [x] R2.6 将已真实核验的相关文献扩充到 40--55 条；未核验条目不写入 bib。
- [x] R2.7 记录训练型 baseline 状态：只有通过冻结协议、统计审计并加入台账后
  才可进入贡献和结果；否则保留明确 blocker，不填数字。
- [x] R2.8 审计 CWRU 各 split 的合成池来源；确认 `lolo_load0` 复用 load0 池，
  将正式迁移结论收紧为 within-load0 与 held-out load1--3 的 72/72 比较。

### R3. 以 main_cas 为骨架的结构合并

- [x] R3.1 备份当前可编译 CAS 源的哈希和 PDF 页数，仅作审计，不复制旧 claim。
- [x] R3.2 重写摘要至不超过 250 词，顺序为痛点、方法、PU/CWRU/Berkeley
  三条正证据、成本定位、边界；不写未完成训练 baseline 结果。
- [x] R3.3 重写 Introduction 为四段问题链和四条贡献，贡献③若训练 baseline
  未冻结则降为可复现实验设计/当前 blocker，不伪装为已完成贡献。
- [x] R3.4 重写 Related Work 为训练型生成、physics-informed 生成、LLM
  recipe/code generation 与 inference-time verification 三条主线。
- [x] R3.5 保留并校正 Problem Formulation，准确表达混合双边区间、类特异 gate、
  多样性下界和 rejection/resampling，不再用错误单边证书公式概括全部规则。
- [x] R3.6 重写 Framework，完整定义 LLM recipe、deterministic renderer、
  train-calibrated verifier、K 轮反馈及责任边界。
- [x] R3.7 逐式核对 renderer 方程、符号、采样率、特征频率和参数来源，确保正文
  与实际代码一致。
- [x] R3.8 重写 Experimental Setup，覆盖 PU、CWRU、Berkeley 正式协议以及
  UMich/MU-TCM 边界协议；写明 split unit、shots、n_syn、seeds 和检验族。
- [x] R3.9 按 PU Phase-A v2 -> CWRU within/LOLO -> Berkeley partial ->
  physical metrics -> ablation 的顺序重写正结果。
- [x] R3.10 新建集中式 Negative Results and Boundaries，完整呈现 PU LOCO
  v1--v6、UMich metadata confound 和 MU-TCM inner-validation stop。
- [x] R3.11 重写 Discussion/Conclusion，先重申有效域，再说明适用边界和开放问题；
  禁用 `certified`、`universal superiority`、`zero-shot` 等越界措辞。
- [x] R3.12 同步 Reproducibility、Data Availability、AI declaration、prompt 与
  certificate/failure report 可审计说明。

### R4. 十张图的证据合同、重绘与挂载

- [x] R4.1 为每张图写一条 core conclusion、panel evidence chain、archetype、
  review risk、source CSV 和导出尺寸，形成图表合同。
- [x] R4.2 核对 Python 3.12.13 与 matplotlib/scipy/pandas 等绘图依赖；缺失时
  明确 blocker，不切换 R 或其他后端。
- [x] R4.3 重绘 `framework`：突出 recipe--renderer--verifier--feedback 主链，
  训练数据只用于校准边界。
- [x] R4.4 重绘 `responsibility_boundary`：区分 LLM、renderer、verifier、
  downstream classifier 的输入、输出和不可归因内容。
- [x] R4.5 将 Algorithm 1/闭环流程作为正文可读的算法框，避免与框架图重复。
- [x] R4.6 重绘四列 waveform + envelope spectrum 对比；只使用可追溯的
  real/LLM/rule/random 冻结样本，禁止挑图隐藏失败。
- [x] R4.7 重绘 boxplots 与 metric_distances，按数据集/类别单独呈现物理和
  分布指标，caption 写清 n 与统计定义。
- [x] R4.8 重绘 downstream_bars，用配对种子分布/置信信息支撑结果，避免仅画
  均值柱状图造成过度确定感。
- [x] R4.9 重绘 acceptance_k，区分 proposal slot、admitted slot 和 rendered
  window，解释一对多映射。
- [x] R4.10 重绘 cross_condition_heatmap，完整显示失败单元格，禁止选择性聚合。
- [x] R4.11 重绘 failure_reasons + failure_case，使用真实拒绝记录并给出 gate
  阈值与失败证据。
- [x] R4.12 全部图统一字体、字号、线宽、方法色、面板标号与 caption；导出
  editable PDF/SVG 与 600 dpi TIFF。
- [x] R4.13 将十张图全部挂入 `main_cas.tex`，检查正文首次引用、顺序、浮动和
  caption 自包含性。

### R5. 全文科研写作与 claim 一致性

- [x] R5.1 按 awesome-ai-research-writing 先做段落逻辑检查，再做英文润色，
  最后去除通用 AI 腔；不改变数字、公式、label 和 cite 语义。
- [x] R5.2 逐句扫描 `significant|transfer|training-free|milling|physical|certif`，
  回链 evidence ledger 并修复越界表述。
- [x] R5.3 交叉核对摘要、贡献、方法、结果、结论五处 claim，确保对象、协议、
  指标和统计边界一致。
- [x] R5.4 核对 Berkeley 统一为 qualified partial：15/18，总结时同时披露
  三个未通过 LLM-vs-rule 的比较。
- [x] R5.5 核对 UMich 只写 condition/process metadata confounding，不写
  “unlearnable”。
- [x] R5.6 核对 PU LOCO v1--v6 为完整预声明失败链，不把内部诊断包装成正式测试。
- [x] R5.7 同步 `cover_letter.md`、`highlights.txt`、`submission_checklist.md`，
  删除与终稿证据不一致的旧定位。

### R6. 构建、PDF 视觉 QA 与最终冻结

- [x] R6.1 使用 CAS 模板编译 `main_cas.tex`，解决 undefined cite/ref、
  overfull/underfull、重复 anchor 和缺图错误。
- [x] R6.2 用 Poppler 将最终 PDF 全页渲染到 `tmp/pdfs/`，逐页检查字体、表格、
  图片清晰度、caption、浮动位置、页眉页脚和章节过渡。
- [x] R6.3 对 10 张图的 PDF/TIFF 做尺寸、DPI、字体嵌入、文本裁切、重叠和
  色盲可区分性检查。
- [x] R6.4 运行 bibliography、claim、placeholder、禁词、生成表一致性和
  PDF warning 自动审计。
- [x] R6.5 更新 `analysis/evidence_ledger.md` 的仓库提交审计信息，但只有通过
  独立证据审查的新增结果才可进入正结果区。
- [x] R6.6 输出终稿重构快照，列出完成项、blocker、未使用结果和复现命令。
- [x] R6.7 审查 `git diff` 与拟提交文件，排除 raw data、checkpoint、训练 runs、
  虚拟环境和用户未跟踪原始副本。
- [x] R6.8 创建描述性 commit，推送 `origin/main`，再次核对远端包含当前提交。

## Framework reset: Layer 1 -- real-data, group-aware calibration (planned 2026-07-10)

### Position lock

BREEZE is not a bearing-only verifier. It is a training-free closed-loop
admission framework for industrial electromechanical equipment, with CNC
machine-state monitoring, milling tool-condition monitoring, and bearing fault
monitoring as equal domain instantiations. The Layer-1 output is a frozen,
auditable `CalibrationArtifact`; it is not a PU-specific set of bearing bounds.

### Literature basis for this redesign

- Ball-screw fault studies establish vibration as a usable observation but use
  machine-specific test rigs, preload/failure definitions, and operating
  context. Therefore a lead-screw gate must require provenance and mechanism
  metadata; it must not invent a universal fault frequency. Wang et al.,
  *Journal of Vibration and Shock* 37(12), 2018:
  https://jvs.sjtu.edu.cn/EN/Y2018/V37/I12/201
- MU-TCM provides a public milling design of experiments with synchronized
  multi-sensor signals, tool wear VB, and cutting-condition metadata. It is
  the public CNC validation line, not a bearing surrogate:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12102343/
- Multivariate conformal work motivates calibration through held-out
  nonconformity scores rather than an ad hoc collection of marginal thresholds.
  Its guarantees require exchangeability, so BREEZE will calibrate at the
  independent-source and regime level and will not claim coverage under
  unobserved regime shift. Sun and Yu, CopulaCPTS, 2022:
  https://arxiv.org/abs/2212.03281

### Dataset scope lock

| role | dataset | Layer-1 status | claim boundary |
|---|---|---|---|
| primary CNC machine-state case | private machine-tool | include after a signed data card; classes are normal machining, lead-screw anomaly, and base imbalance | no component-specific physical admission claim until the required machine metadata are present |
| public CNC milling case | MU-TCM full | include after raw-signal extraction and a preregistered experiment/insert-edge split | tool-wear and cutting-condition claims only |
| rotating-equipment transfer case | PU / Paderborn | include; existing results remain a frozen legacy baseline | bearing kinematics only |
| external bearing transfer case | CWRU drive-end 12 kHz | include; existing results remain a frozen legacy baseline | CWRU 6205 geometry and DE vibration only |
| optional later stress test | DIRG VariableSpeedAndLoad | defer until the four core adapters run | condition-transfer only |

Do not use XJTU-SY, Berkeley/NASA milling, UMich CNC, HIT, IMS, JUST, MFPT,
or the private machine-tool data as a substitute for missing metadata. XJTU
lacks a frozen supervised protocol; Berkeley is partial/no-go; UMich has an
unresolved condition confound; the other datasets lack a ready physical-label
or raw-data contract.

### Layer-1 data contract

Every dataset adapter must emit the following fields for every window. No
adapter may overload `bearing_id` to represent a file, tool, or machine run.

```text
X, y, source_id, entity_id, regime_id, time_order,
sensor_schema, physics_metadata, split_manifest
```

- `source_id`: independent acquisition source used for leakage control and
  calibration (measurement file, run, experiment, or contiguous machining
  segment).
- `entity_id`: physical subject when known (bearing, insert-edge, screw/axis).
- `regime_id`: declared operating context, never inferred from labels.
- `physics_metadata`: typed, source-backed metadata; unknown fields stay
  unknown rather than receiving imputed physical values.
- `split_manifest`: immutable outer train/test group assignment plus the
  train-only reference/calibration group assignment and source-file hashes.

Adapter mapping:

| dataset | source_id | entity_id | regime_id | required physics metadata |
|---|---|---|---|---|
| private machine-tool | acquisition CSV/run | machine axis or screw assembly when known | spindle/feed/program stage | label mechanism, spindle rpm, feed, screw lead/pitch or transmission ratio, sensor mounting, current definition, run order |
| MU-TCM | experiment/repetition MAT | insert-edge | material, Vc, fz, ap, ae, lubrication | VB, tooth count, spindle speed, sensor mapping, cutting-stage bounds |
| PU | measurement file | bearing | rpm, torque, radial load | bearing geometry, channel mapping |
| CWRU | source MAT file | drive-end bearing | load and rpm | 6205 geometry, DE channel mapping |

### Calibration algorithm to implement

1. Freeze the outer split at `source_id` level. The test split is unreadable by
   calibration, generation, and protocol selection.
2. Split outer-train by `source_id` into `reference` and `calibration` groups;
   all windows from a source remain together. Fit feature references only on
   `reference` groups.
3. Compute deterministic generic nonconformity scores for statistics, smooth
   spectral shape, and multichannel structure. Domain scores are supplied only
   by an enabled physics plugin.
4. Calibrate a single joint admission threshold from held-out calibration-group
   scores using the exact empirical order statistic for the declared target
   coverage. Do not use per-gate coverage powers or a grid search over
   marginal tail probabilities in the new protocol.
5. Estimate diversity from leave-one-source-out real-real distances, not from
   adjacent overlapping windows in the same source.
6. Freeze a `CalibrationArtifact` containing the schema, manifests, feature
   definitions, thresholds, group counts, train/calibration pass rates,
   applicable regimes, plugin availability, and hashes.
7. A candidate is physically admitted only when both the generic score and all
   required domain scores pass. A missing mandatory field marks the plugin
   `unavailable` and blocks the corresponding domain claim; it is not replaced
   with a guessed frequency or a repaired waveform.

### CNC-specific stop conditions

- The private machine-tool data currently have five train files per class.
  Five independent calibration groups cannot produce a non-vacuous 90 percent
  split-conformal group-level threshold: the 0.90 order statistic requires at
  least nine calibration groups. Window count must never be used to conceal
  this limitation.
- Before lead-screw or base-imbalance generation begins, create and approve a
  `machine_tool_data_card.md` covering the metadata listed above and the exact
  physical meaning of each label. Until then, the existing machine-tool
  verifier is an exploratory distribution-consistency audit only.
- For base imbalance, do not assume a 1X spindle signature until the dataset
  owner confirms that the label denotes rotational imbalance and provides a
  speed reference. For lead-screw anomaly, do not assume a screw-order gate
  until feed/lead or an equivalent measured axis-rate reference is available.

### Execution plan

- [x] L1.1: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Add `breeze/src/datasets/protocol.py` with typed `DatasetProtocol`,
  `SensorSchema`, `PhysicsMetadata`, and immutable `SplitManifest` objects.
- [x] L1.2: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Write data cards and manifests for private machine-tool, MU-TCM,
  PU, and CWRU. Resolve the stale private-label mapping in the registry and
  reports from the documented owner confirmation; record missing fields
  explicitly.
- [x] L1.3: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Implement the source-group-aware calibration engine and artifact
  serializer. Unit-test that outer-test identifiers cannot reach its API.
- [x] L1.4: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Implement generic deterministic score extractors and group-level
  joint order-statistic calibration; unit-test leave-one-source-out diversity.
- [x] L1.5: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Move the existing PU verifier behind `BearingPhysicsPlugin` without
  altering frozen legacy outputs. Reproduce a frozen PU row before using the
  new protocol for any new claim.
- [x] L1.6: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Implement `CncMachinePhysicsPlugin` with two explicitly separate
  modes: `lead_screw` and `base_imbalance`. Each mode must validate its required
  metadata before it exposes any gate.
- [x] L1.7: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Implement `MillingPhysicsPlugin` for MU-TCM. It may use tooth-pass
  and process-order evidence only after tooth count, spindle speed, and active
  cutting intervals are validated from the data card.
- [x] L1.8: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Run real-data-only audits on reference, calibration, and untouched
  test source groups. Report per-source and per-regime pass rates before any
  LLM call or downstream classifier training.
- [x] L1.9: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Decide whether additional independent private CNC runs are required
  for a formal 90 percent calibration claim. If they are unavailable, retain the
  private dataset as a CNC case study with an explicit empirical-audit scope,
  not a distribution-free coverage claim.

Acceptance criteria: no test-source access during calibration; no window-level
random split; no inferred mechanical metadata; every enabled domain gate has a
documented physical source and applicability domain; every accepted synthetic
sample can be traced to one frozen calibration artifact.

## Framework design: Layer 2 -- generic deterministic signal constraints (planned 2026-07-10)

### Position lock

Layer 2 is the domain-neutral deterministic signal-structure admission layer.
It receives a window that has already passed Layer-0 schema/legality checks and
a frozen Layer-1 `CalibrationArtifact`, then returns an auditable generic
accept/reject result. It does not contain bearing geometry, current-sideband
rules, tooth-pass frequency, screw order, spindle 1X, an inferred machine
state, or a trained class-identity classifier. Those are Layer-3 physics
plugins, enabled only when their data-card preconditions are satisfied.

The layer is conditioned on the declared `(dataset, class, sensor_schema,
regime_id)` cell of the artifact. This is not a learned recognition model: the
class is the requested generation label and the layer only measures whether the
candidate has the real data's declared generic signal structure. A missing
regime or sensor description is an invalid protocol state, not a value to
impute.

### Literature basis for the boundary

- Multi-sensor milling research extracts time-, frequency-, and time-frequency
  information across sensors, while warning that redundant channels can obscure
  useful information. This supports separate generic temporal, spectral, and
  cross-channel blocks rather than treating one sensor layout as universal.
  Zhou and Xue, *Sensors* 18(11), 3866, 2018:
  https://doi.org/10.3390/s18113866
- The MU-TCM public CNC dataset pairs synchronized signals with cutting
  conditions and tool-wear observations. Signal agreement is therefore
  distinct from a validated machining-mechanism claim; the latter needs the
  metadata handled by Layer 3:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12102343/
- Ball-screw vibration diagnosis is based on a specific fault definition and
  test setting. Its spectral signatures must remain a CNC physics plugin, not
  a generic spectral constraint:
  https://jvs.sjtu.edu.cn/EN/Y2018/V37/I12/201
- Multivariate conformal prediction supplies the calibration principle:
  combine deterministic nonconformity scores first, then calibrate their joint
  tail on held-out data. It does not license a guarantee when independent
  source groups or exchangeability are absent. Sun and Yu, ICLR 2024:
  https://arxiv.org/abs/2212.03281

### Formal input and output contract

```text
GenericSignalConstraint(
    CandidateWindow, SensorSchema, CalibrationArtifact, declared_class,
    declared_regime
) -> GenericReport
```

`SensorSchema` declares channel count, channel order, units, synchronisation,
sampling rate, and whether each channel is a vibration, current, force, AE, or
another measured quantity. Layer 2 never pads a missing channel with zeros or
renames a channel to fit another dataset.

`GenericReport` must contain the artifact hash, protocol-cell identifier,
active/inactive feature blocks, every block score, the joint score and its
calibrated threshold, both diversity distances and thresholds, pass/fail
reasons, and a statement that the result is `generic_structural` only. It must
not assert a bearing, tool, lead-screw, or imbalance mechanism.

### Algorithm to implement

1. **Use the frozen Layer-1 reference cell.** Construct every reference set
   from outer-train `reference` source groups only. Compute calibration scores
   only on the disjoint Layer-1 `calibration` source groups. Outer-test data,
   synthetic data, and downstream-classifier outputs cannot enter either set.
2. **Extract deterministic, schema-aware block representations.** For every
   channel, compute robust amplitude/distribution descriptors and temporal
   dependence descriptors. Compare normalized one-sided PSD shapes on the
   normalized frequency axis with a distributional distance; do not introduce
   equipment-specific fixed bands. When two or more time-synchronised channels
   are declared, additionally compute channel-energy composition and
   cross-channel dependence. A one-channel schema (CWRU) marks the last block
   `inactive` and removes it from the composite score; it is not compared to a
   fabricated multi-channel vector.
3. **Make all block scores comparable without a fitted classifier.** For each
   active block, derive reference leave-one-source-out distances. Convert a
   candidate distance to its empirical reference rank, with the rank convention
   and ties fixed in the artifact. Combine active block ranks as their maximum,
   so the joint score records the strongest generic departure rather than
   allowing one plausible block to compensate for another implausible block.
4. **Calibrate one source-level joint threshold.** Before looking at
   calibration data, freeze a deterministic non-overlapping window manifest
   and source-level aggregate. Compute one joint score per calibration
   `source_id`, then select the exact declared empirical order statistic. The
   same threshold applies to all Layer-2 blocks in that protocol cell; no
   per-gate coverage powers, tail multipliers, or search over test performance
   are permitted. The artifact records group count and whether the requested
   coverage is non-vacuous.
5. **Apply non-copy diversity at source level.** Use the same schema-aware
   representation to compute real--real nearest-neighbour distances while
   excluding windows from the same `source_id`. Calibrate a lower diversity
   bound from those leave-one-source-out distances. For a declared generation
   batch, report both candidate-to-real and candidate-to-candidate distances;
   an exact duplicate is rejected by the Layer-0 content hash, while a
   sub-threshold near-copy fails this Layer-2 criterion. Thresholds are frozen
   before generation and are never updated with accepted synthetic samples.
6. **Reject without altering the waveform.** A Layer-2 failure produces its
   report and returns control to recipe generation. No clipping, spectral
   equalisation, template mixing, learned repair, or post-hoc projection is an
   admissible Layer-2 operation.

The only numerical choices exposed by this layer are declared protocol
parameters: target coverage, the source-level aggregation definition, the
non-overlapping window manifest, and the deterministic feature-definition
version. They are selected before calibration, stored in the artifact, and are
shared across all four core adapters. Dataset names may select a schema and
metadata card, but may not select hidden Layer-2 constants.

### Block definitions and scope

| block | generic evidence | applicability | explicitly excluded |
|---|---|---|---|
| temporal distribution | robust amplitude, quantile, impulse, and temporal-dependence descriptors per declared channel | all schemas | bearing defect rates, tool wear thresholds, current-sideband rules |
| spectral shape | normalized PSD distribution and its distance to the reference PSD distribution | all schemas | fixed bearing/CNC frequency bands and assumed speed orders |
| multichannel structure | channel-energy composition and cross-channel dependence for declared synchronised channels | `n_channels >= 2` | assumed X/Y/Z orientation or vibration-current semantics |
| non-copy diversity | leave-one-source-out real-real and candidate distances in the same generic representation | all schemas | synthetic-pool-driven recalibration and within-file window neighbours |

Layer 2 starts after M1 format/legality validation. Layer 3 may append a
physics score, but Layer 3 cannot silently override a Layer-2 failure and Layer
2 cannot turn an unavailable physics plugin into a generic pass.

### Required migration of the four core datasets

| dataset | reusable generic material | move out of Layer 2 | migration boundary |
|---|---|---|---|
| private machine-tool | time statistics, channel-energy/correlation, normalized PSD-CDF distance in `MachineToolVerifier` | the `ExtraTrees` class-identity certificate; any label-mechanism assertion | first adapter; four declared channels remain schema-owned, while lead-screw/base-imbalance evidence waits for Layer 3 metadata validation |
| MU-TCM full | synchronized multi-sensor time/spectral/cross-channel representation | local quantile multipliers (`.995*1.15`, `.002/.998`, `.01*.35`) and tool/process rules | rebuild its `AdmissionCalib` scores from the shared artifact; use its public cutting metadata only in Layer 3 |
| PU | v2 time statistics, generic soft spectral shape, PSD-Wasserstein and diversity calculations | envelope defect bands, MCSA, 6203 geometry, and PU channel assumptions | reproduce the frozen PU generic row before enabling `BearingPhysicsPlugin` |
| CWRU 12 kHz DE | single-channel time/spectral representation and generic diversity | 6205 geometry, drive-end envelope frequencies, and any current-channel logic | replace the standalone generic portion of `CwruVerifier`; retain the one-channel schema rather than borrowing PU channels |

The current duplicated verifiers are evidence sources, not interfaces to
preserve. In particular, a trained `ExtraTrees` identity certificate is useful
only as an exploratory downstream diagnostic; it cannot be a formal Layer-2
admission gate in a training-free framework.

### Execution plan

- [x] L2.1: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Define typed `GenericFeatureSchema`, `GenericSignalConstraint`,
  `GenericReferenceCell`, `GenericDiversityPool`, and `GenericReport` objects
  under `breeze/src/`; make the Layer-1 artifact their only calibration input.
- [x] L2.2: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Implement deterministic temporal, normalized-PSD, and declared
  multichannel representations with source-balanced reference aggregation.
  Unit-test channel permutation, one-channel activation, non-finite input,
  and sample-rate/schema mismatches.
- [x] L2.3: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Implement leave-one-source-out block distances, empirical-rank
  transformation, maximum joint score, and exact source-level order-statistic
  calibration. Unit-test that changing outer-test data cannot alter the
  artifact.
- [x] L2.4: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Implement content-hash duplicate detection plus the frozen,
  leave-one-source-out real--real diversity calibration. Unit-test that
  overlapping windows from the same source cannot calibrate a diversity
  threshold.
- [x] L2.5: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Migrate private machine-tool generic code first. Remove the
  per-gate coverage exponent and classifier certificate from formal admission;
  preserve a separate exploratory report only where required for historical
  comparability.
- [x] L2.6: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Migrate MU-TCM, PU, and CWRU adapters onto the same contract. No
  adapter may retain local tail multipliers, fixed generic thresholds, or
  dataset-name branching inside the generic scorer.
- [x] L2.7: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Run a real-data-only audit for each dataset and each declared
  class/regime cell: reference/calibration/test source counts, active blocks,
  per-source scores, pass rates, diversity distributions, and unavailable
  fields. Do this before any LLM generation, downstream training, or physics
  claim.
- [x] L2.8: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Freeze four artifacts and establish regression tests: PU and CWRU
  must reproduce their declared generic features on frozen legacy inputs;
  private machine-tool and MU-TCM must prove schema compatibility without
  importing bearing-only assumptions.
- [x] L2.9: Deferred（投稿后工作；投稿前不开启新的框架重构工程）. Only after L2.1--L2.8 pass, attach the separate CNC, milling, and
  bearing Layer-3 plugins. Formal certificates must list generic and physics
  decisions separately.

Acceptance criteria: a single Layer-2 implementation accepts schemas with one,
three, or four declared channels without padding; no trained classifier,
equipment kinematic value, local threshold multiplier, or outer-test source is
reachable from it; each decision is reproducible from the artifact and report;
rejected signals are never post-processed into acceptance; generic and
domain-physics claims are separable in every certificate.

## Framework design: Layer 3 -- metadata-gated domain-physics evidence (planned 2026-07-13)

### Position lock

Layer 3 is not an additional generic classifier and it is not a collection of
hard-coded frequency bands. It verifies an explicitly declared mechanical
mechanism after a candidate has passed Layer 0 legality and Layer 2 generic
structure. A Layer-3 decision is valid only for the tuple `(plugin, mechanism,
sensor_schema, regime_id, data-card version)`. It must never be promoted to a
general fault-diagnosis claim outside that tuple.

The only legal results are `pass`, `fail`, and `unavailable`. `unavailable`
means a required physical measurement, label definition, or independent
calibration group is absent. It blocks the corresponding physical certificate;
it is not converted into a generic pass, an inferred frequency, a classifier
score, or a repaired signal. Layer 2 may still issue its strictly generic
structural report in that situation.

### Literature basis for the design

- Envelope analysis is appropriate for rolling-bearing local defects because
  impacts recur at geometry- and speed-derived BPFO/BPFI/BSF/FTF frequencies;
  the demodulation carrier band must be chosen with the resonance mechanism in
  mind rather than treating raw-spectrum peaks as the defect itself. Kim, An,
  and Choi, *Applied Sciences* 10(20), 7302, 2020:
  https://doi.org/10.3390/app10207302
- The relationship between spectral-kurtosis indices and squared-envelope
  evidence supports using a resonance-band family to expose impulsive carrier
  responses, but it does not support one globally fixed band or a fixed number
  of selected bands. Antoni and Randall, *Mechanical Systems and Signal
  Processing* 40(2), 2013:
  https://doi.org/10.1016/j.ymssp.2013.02.023
- Motor-current signature analysis can expose mechanical/electrical fault
  components, but its sidebands depend on motor topology, supply fundamental,
  load, and measurement configuration. MCSA is therefore optional evidence
  conditional on documented current channels and train-source separability:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC11858980/
- Milling monitoring studies use the rotational/tooth-passing process together
  with cutting-state measurements; vibration cannot reliably distinguish air
  cutting from material removal on its own. Thus TPF claims require verified
  spindle/teeth and an active-cut interval. Mohamad et al., *Machines* 13(4),
  276, 2025:
  https://doi.org/10.3390/machines13040276
- MU-TCM publishes synchronized internal/external signals, cutting-condition
  information, and wear observations. Its synchronization and experiment
  provenance are prerequisites for a milling physics claim:
  https://doi.org/10.1038/s41597-025-05168-5
- Ball-screw preload-loss experiments report signatures that vary with the
  feed-drive construction, preload, worktable position, and loading. Some
  studies track ball-pass frequency/order changes, not a universal 1X rule.
  Wang et al., *MSSP* 48, 77-91, 2014:
  https://doi.org/10.1016/j.ymssp.2014.02.017
  and NIST, *Manufacturing Letters*, 2024:
  https://doi.org/10.1016/j.mfglet.2024.09.148

### Unified physical-plugin contract

```text
PhysicsPlugin(
    CandidateWindow, SensorSchema, PhysicsMetadata, CalibrationArtifact,
    GenericReport, declared_class, declared_regime
) -> PhysicsReport

required_metadata() -> typed fields
validate_metadata() -> valid | unavailable with reasons
derive_targets() -> mechanism-specific targets and uncertainty intervals
calibrate(reference_source_groups, calibration_source_groups) -> PhysicsArtifact
verify(candidate) -> PhysicsReport
```

`PhysicsArtifact` is frozen separately from the Layer-1 generic artifact but
must reference its hash, split manifest, feature-definition version, plugin
version, data-card hash, physical target definitions, reference/calibration
source IDs, group counts, and exact thresholds. `PhysicsReport` must expose
the derived targets, observed evidence, uncertainty interval, source-calibrated
score, decision, and an explicit claim scope.

No plugin may access outer-test sources, synthetic-pool statistics, LLM text,
or a downstream classifier during calibration. A candidate is physics-admitted
only when Layer 2 passes and every *required, available* Layer-3 plugin passes.
No plugin may modify a failed waveform.

### Common calibration algorithm

1. Validate the signed data card and sensor schema before calculating any
   physical target. Unknown geometry, speed, sensor placement, label meaning,
   or synchronization produces `unavailable`.
2. Derive target frequencies/orders and their uncertainty intervals only from
   typed metadata: geometry, measured speed/position, cutting parameters,
   acquisition clock, and documented measurement uncertainty. Do not derive a
   target from the class label or from a candidate spectrum.
3. On Layer-1 `reference` source groups, calculate the plugin's deterministic
   evidence vector. A physical evidence definition is fixed before calibration:
   the declared frequency/order family, frequency-resolution rule,
   carrier/analysis band family, source-level aggregation, and class/regime
   mapping.
4. Use the disjoint Layer-1 `calibration` source groups to form one joint
   physical nonconformity score per `source_id` and freeze its exact empirical
   order-statistic threshold. A plugin must record that a requested coverage
   level is non-vacuous at the available group count.
5. Report all component scores but decide only with the frozen joint score.
   Component gates cannot be independently tuned on test data or compensated
   by a learned class-identity model.
6. Re-run the plugin against held-out real source groups before any synthetic
   generation. Report pass rates by class, source, and regime; a physical
   plugin with systematic real-data failure is invalid rather than a reason to
   relax its threshold.

### Plugin A: `BearingPhysicsPlugin` for PU and CWRU

Required metadata: bearing geometry (rolling-element count, ball and pitch
diameter, contact angle), explicit class-to-mechanism mapping, measured RPM or
RPM interval for every source, vibration channel mapping, sampling rate,
sensor bandwidth/usable analysis range, and, when MCSA is requested, documented
motor topology plus a synchronized current-channel pair.

Evidence design:

- Compute BPFO/BPFI/BSF/FTF from geometry and source RPM. Class mapping must
  come from the data card; no label-synonym lookup is permitted in the formal
  plugin.
- Build a deterministic, metadata-bounded resonance-band family. Evaluate the
  physically targeted envelope evidence over the full family and aggregate it
  before source-level calibration. Do not retain a hard-coded Top-3
  spectral-kurtosis selection; calibrating the aggregate over the entire
  declared family accounts for the selection operation.
- For a local defect, evaluate target-frequency alignment, fundamental and
  harmonic evidence, and where the mechanism calls for it, shaft/cage
  modulation. Frequency tolerance is derived from DFT resolution plus declared
  RPM/geometry uncertainty; an unrecorded percentage tolerance is prohibited.
- For a healthy class, score the absence of the same documented fault evidence
  with its own calibrated healthy distribution; it must not borrow a fault
  lower bound.
- MCSA is a separate optional evidence block. It activates only for a declared
  current sensor topology and only becomes a hard component when calibration
  sources demonstrate fault-versus-healthy separation. Otherwise its report is
  `unavailable`, not an automatic pass.

PU uses its documented 6203 geometry and vibration/current schema; CWRU uses
the drive-end 6205 geometry and its vibration-only schema. CWRU must never
receive a synthetic current channel or an MCSA decision.

### Plugin B: `MillingPhysicsPlugin` for MU-TCM

Required metadata: experiment and insert-edge IDs, wear observation/VB and
measurement time, material, cutting speed or measured spindle-speed trace,
tooth count, feed per tooth or feed trace, axial/radial depth, lubrication,
sampling clocks, synchronized channel mapping, and verified active-cut bounds.

The plugin has three separately certified evidence scopes; each is enabled only
when its own fields are present:

| scope | required additional measurement | admissible evidence |
|---|---|---|
| `process_spectrum` | spindle speed and tooth count | TPF/spindle order family and channel-specific process energy during active cutting |
| `cycle_synchronous` | spindle encoder/phase reference or equivalent synchronized tooth events | per-tooth force/vibration/current/AE evidence indexed by actual tooth phase |
| `wear_trajectory` | repeated VB observations, insert-edge identity, and chronological machining order | source-level relationship between measured wear progression and calibrated process evidence |

No scope may encode a universal rule such as “wear always increases RMS” or
“TPF amplitude must grow.” The reference source groups establish the signed
class/regime relationship. Air-cut and transient regions are outside the
plugin's admissible window manifest. Manual label-name mappings such as
`worn -> severity=0.5` in the current `MillingKinematicsPlugin` are prompt
assistance only and must be removed from formal admission logic.

### Plugin C: `CncMachinePhysicsPlugin` for the private machine-tool data

This plugin must expose two independent modes and must not claim a physical
relation merely because the source label is `lead_screw_anomaly` or
`base_imbalance`.

| mode | required signed metadata | evidence allowed after validation |
|---|---|---|
| `lead_screw` | exact failure mechanism (for example preload loss, recirculation defect, or misalignment), measured axis position/velocity or encoder trace, screw lead, screw/nut geometry as applicable, table mass/load, axis/run direction, sensor mounting, and label acquisition protocol | screw rotational/order targets and only those ball-pass, modal-shift, sideband, or position-dependent features justified by the stated mechanism |
| `base_imbalance` | exact physical meaning of the label, affected rotating assembly or structural path, measured RPM/phase if rotational imbalance is claimed, sensor orientation/mounting, machine foundation state, and controlled operating regime | 1X/harmonic evidence only for a confirmed rotating imbalance; otherwise a separately documented structural/modal mechanism with its own measured excitation/reference |

For a lead-screw preload-loss claim, commanded feed is insufficient when the
axis may lag; use measured motion/encoder data. For a base-structure label that
does not denote rotating imbalance, 1X is not a valid target. Until these data
cards exist and calibration groups are sufficient, both modes return
`unavailable`; the private dataset remains a Layer-2 empirical case study.

### Migration boundary from current code

| current component | destination under the new framework |
|---|---|
| `BearingKinematicsPlugin.char_freqs()` and physically explicit envelope/MCSA feature functions | extract into `BearingPhysicsPlugin`; retain only train-source regression compatibility with frozen PU/CWRU legacy rows |
| `BreezeVerifierV2` statistics, soft spectrum, PSD-W1, and generic diversity | move to Layer 2; they must not remain part of a physics certificate |
| fixed Top-3 resonance selection and implicit 2 percent target tolerance | replace with the declared full band-family aggregate and metadata-derived uncertainty interval |
| `MillingKinematicsPlugin` TPF calculations | retain as target derivation inside `MillingPhysicsPlugin`; remove hand-coded label severity from formal verification |
| `MachineToolVerifier` and `ExtraTrees` certificate | retain generic portions in Layer 2; do not promote `ExtraTrees` to Layer 3; add no CNC physics rule until data-card validation passes |

### Execution plan

- [ ] L3.1: Add `breeze/src/physics/base.py` with typed `PhysicsPlugin`,
  `PhysicsMetadataRequirements`, `PhysicsArtifact`, `PhysicsReport`, and the
  explicit `pass/fail/unavailable` status. Unit-test that unavailable metadata
  cannot yield a physics pass.
- [ ] L3.2: Add immutable domain data cards: `bearing_pu.md`, `bearing_cwru.md`,
  `mutcm_milling.md`, and `machine_tool_data_card.md`. Include provenance,
  field-level source, unit, uncertainty, and a list of missing values.
- [ ] L3.3: Extract `BearingPhysicsPlugin` from the legacy PU/CWRU verifier.
  Implement geometry/RPM target derivation, full-band-family envelope aggregate,
  healthy evidence, and schema-gated MCSA. Preserve frozen legacy outputs in
  a dedicated compatibility test; do not overwrite existing results.
- [ ] L3.4: Audit PU and CWRU real source groups with the new plugin. Report
  per-class/per-RPM-group calibration and untouched-test pass rates, target
  uncertainty, MCSA availability, and every unavailable reason.
- [ ] L3.5: Implement `MillingPhysicsPlugin` only after MU-TCM raw extraction,
  synchronization audit, experiment/insert-edge split, and active-cut manifest
  are frozen. Start with `process_spectrum`; add the other scopes only when
  their required measurements are verified.
- [ ] L3.6: Audit the private machine-tool metadata against both CNC mode
  tables. Obtain a signed owner response for every missing field. Implement no
  physical frequency/order test before this audit passes.
- [ ] L3.7: Implement each validated CNC mode as a separate class with source-
  level calibration and regime-specific real-data audit. Keep any unavailable
  mode visible in reports and certificates.
- [ ] L3.8: Add a `CompositeAdmissionReport` requiring Layer 0, Layer 2, and
  all declared Layer-3 plugin decisions. Its certificate must state which
  claims are generic and which are mechanism-specific.
- [ ] L3.9: Run negative-control tests: wrong bearing geometry, RPM outside
  the declared interval, missing current topology, air-cut milling segment,
  missing spindle phase, absent screw lead, and ambiguous base label must all
  fail validation or return `unavailable`, never a physics pass.
- [ ] L3.10: Before new LLM experiments, freeze all artifacts, manifests,
  source-group audits, and regression results. Then update the paper claim to
  match the plugins actually available; no unavailable CNC/milling mechanism
  may be presented as verified.

Acceptance criteria: every physical target is reproducible from documented
metadata rather than labels or candidate spectra; every threshold is calibrated
on independent training sources; PU/CWRU, MU-TCM, and private CNC issue
separate evidence scopes; no fixed Top-K band choice, guessed 1X/TPF/screw
order, synthetic current channel, trained identity classifier, or waveform
repair enters Layer 3; a certificate cleanly distinguishes `pass`, `fail`, and
`unavailable` physical evidence.

## 当前执行游标（2026-07-08，必须按顺序）

1. [completed] `12.A KinematicsPlugin`：统一运动学插件接口、轴承/铣削插件最小实现已完成；PU smoke 回归与 Phase-A v2 对应冻结行完全一致。
2. [completed] `12.B CWRU 修正版`：统一 `n_syn=20/class`、40 seeds、within+LOLO 四折已跑完、汇总并冻结；2400/2400 行齐全，90 个预注册 Wilcoxon/Holm 比较全部通过。
3. [in_progress] `12.C/12.D`：优先级按用户 2026-07-08 最新铣削 v2 指令更新：Berkeley/NASA milling 先按文献标准 0.2/0.7 mm 重构协议并重新 inner-val 攻坚；UMich CNC 二分类并行优先作为第二达标路径；LOCO v3 是高价值可选线。Berkeley v1 inner-val 攻坚已按 §0-§5 穷尽 Step 1-4，但原 0.2/0.45 分档未达到 5/6 gate；正式 40-seed held-out test 未跑。Berkeley v2 binary 已预注册并一次性 formal，结果 15/18 比较通过但 LLM>rule 三项未过，冻结为 partial/no-go。UMich v2 二分类 inner-val 已完成，最佳 LLM v2 仅 2/6 gate；UMich v3 加入 `passed_visual_inspection` 纯血 exemplar 后最佳仍仅 1/6 gate，均未进入 formal。私有机床 v2 LLM smoke 已在冻结 inner split 上结束并 BLOCKED，formal test 未读。API 总上限 3000，当前真实累计 1131/3000；Berkeley v2 API 预算 ≤150，UMich API 预算 ≤200。
4. [pending] `Phase C/D/E/F`：baseline/物理真实性/消融/论文重写只能在两条实验线关账后进行。

当前状态：任务 1“冻结当前实验快照”、任务 2“BREEZE-v2 高危 gate 改进准备”、任务 3“BREEZE-v2 离线重筛实验”、任务 4“下游结果补强”、任务 5“自建机床跨数据集实验”、任务 6“主结果统计与图表最终化”、任务 7“论文写作”、任务 8“终审与投稿准备”和任务 9“按审稿意见大修论文”均已完成到当时数据允许的边界。Phase-A v2 补丁已在预算对等、20 seeds 和预注册检验族下通过，且 2026-07-06 已冻结全部 Phase-A v2 产物。用户 2026-07-07 最新补丁将论文定位锁定为 A：BREEZE 是面向工业旋转机械监测信号的零训练 LLM 生成 + 物理验证准入统一框架，轴承与铣削为平级实例化；私有机床数据彻底移出论文，IMS 取消。当前主线改为 5 个公开数据集：PU、CWRU、XJTU-SY、UC Berkeley/NASA milling、UMich Kaggle CNC。不能由真实数据支持的 claim 继续标为 BLOCKER，不用写作替代实验。核心报告：
- `reports/experiment_snapshot_2026-07-04.md`
- `reports/snapshot_raw_2026-07-04.json`
- 生成脚本：`breeze/scripts/freeze_snapshot.py`
- `reports/breeze_v2_rescreen_report_2026-07-04.md`
- `reports/machine_tool_experiment_2026-07-04.md`
- `reports/machine_tool_synthetic_protocol.md`
- `analysis/main_tables.md`
- `breeze/paper/main.tex`
- `breeze/paper/main.pdf`
- `breeze/paper/main_cas.tex`
- `breeze/paper/main_cas.pdf`
- `breeze/paper/highlights.txt`
- `breeze/paper/cover_letter.md`
- `breeze/paper/supplementary_material.md`
- `breeze/paper/submission_checklist.md`
- `analysis/reviewer_response_matrix.md`
- `reports/revision_snapshot_2026-07-04.md`
- `reports/revision_statistics_2026-07-04.md`
- `reports/reviewer_response_draft_2026-07-04.md`
- `reports/figure_revision_snapshot_2026-07-04.md`
- `breeze/results/revision_v2_significance_all_baselines_bh.csv`
- `breeze/results/cross_condition_verifier_full.csv`
- `breeze/results/phaseA_v2_downstream_cnn.csv`
- `breeze/results/phaseA_v2_wilcoxon.csv`
- `breeze/results/phaseA_v2_gate_report.md`
- `breeze/results/phaseA_v2_frozen_2026-07-06/manifest_sha256.csv`

## 12. 2026-07-07 定位 A 统一框架补丁（当前活动）

执行边界：
- [x] 读取 `awesome-ai-research-writing` 规则：实验分析和论文 claim 必须由本地 CSV/JSON/NPZ 支撑，不能编造或把 smoke 结果写成 SOTA。
- [x] 确认本地数据目录：`data/3. Milling-mill/mill.mat` 为 UC Berkeley/NASA milling；`data/archive/` 为 UMich CNC；`data/xjtu/XJTU-SY_Bearing_Datasets/` 已出现分卷 rar 与文档，但用户说明仍在下载，暂不解压、不预处理、不调用 API。
- [x] 冻结 2026-07-06 CWRU smoke 产物到独立目录，作为内部开发记录；冻结目录为 `breeze/results/cwru_legacy_2026-07-06_pre_patch_v2/`，含 `manifest_sha256.txt`，已设只读。后续 CWRU 修正版全部使用新目录/新文件名前缀，不能覆盖旧报告。
- [x] 将 API 用量继续统一写入/报告；截至 CWRU full v1，累计 637/2000，本轮 CWRU 修正新增 0 次 API，当前累计仍为 637/2000。
- [x] 核对并修正本地 LLM/API 节流：主配置 `LLM_MIN_INTERVAL=2.0`；CWRU LLM smoke 脚本旧 `2.2` 秒默认值/约束/报告文字已改为 `2.0` 秒；未改动非 API 的 `120` timeout、采样率或 verifier 窗口常量。
- [x] 按 2.0 秒串行节流重估 API 预算并持续更新：当前累计 658/2000，剩余 1342；剩余预算的节流下限 44.7 min，预算约束方案预计最终 1716-1788/2000，见 `breeze/results/api_budget_estimate_2026-07-07.md`。

### 12.A 代码接口抽象：`KinematicsPlugin`
- [x] 审查现有 renderer/verifier/Phase-B CWRU 脚本，定位运动学频率、调制模式和频带先验的硬编码位置；主要集中在 `config.fault_freqs()`、`recipe_ablation.py`、`phase_b_cwru_*` 脚本。
- [x] 新增最小接口 `KinematicsPlugin`，包含 `char_freqs()`、`modulation_pattern(cls)`、`band_priors()`；见 `breeze/src/kinematics.py`。
- [x] 实现 `BearingKinematicsPlugin`：BPFO/BPFI/BSF/FTF、故障类冲击/调制先验、轴承频带先验；PU `config.fault_freqs()` 已保持旧 API 但通过插件计算，数值回归 max diff=0。
- [x] 实现 `MillingKinematicsPlugin`：TPF=主轴转频×刃数、TPF/主轴转频谐波、低采样率过程特征频带先验；`band_priors()` 明确 `requires_envelope=False`。
- [x] 将 Phase-B 新脚本显式消费 plugin 输出，保持 verifier 五 gate、recipe schema、renderer 和闭环反馈机械无关；`phase_b_cwru_physics_config.py` 已使用 `BearingKinematicsPlugin`，并显式记录 CWRU 6205 的 `ball_spin_harmonic_factor=2.0`。
- [x] 重构后重跑 PU smoke，与 Phase-A v2 冻结产物做一致性核对，防止接口抽象引入回归；`breeze/results/kinematics_plugin_pu_smoke_2026-07-07_report.md` 显示 n=5 seeds 0-1 的 real_only 与 LLM 行在 n_syn、Acc、Macro-F1、per-class F1、confusion 上完全一致。

### 12.B CWRU 修正版：统一预算 + 全 40 seeds + LOLO 4 折
- [x] 废弃测试集调过的旧 schedule 作为正式结果：`n=5/10 用 38/class、n=25 用 20/class` 仅保留内部开发记录。
- [x] 冻结新的正式 CWRU budget：统一 `n_syn=20/class` 用于 n_real={5,10,25}、within 与 LOLO 全折；选择依据为先验保守预算和避免测试集调参，旧 budget ablation 仅作为开发记录。
- [x] CWRU within-condition：`within_load0` 用统一 `n_syn=20/class`、40 seeds、n_real={5,10,25} 重跑 real_only/noise_aug/rule/LLM；正式汇总见 `breeze/results/cwru_patch_v2_2026-07-07/cwru_patch_v2_report.md`。
- [x] CWRU LOLO：`lolo_load0/1/2/3` 四折已跑完，统一 `n_syn=20/class`、40 seeds、n_real={5,10,25}、real_only/noise_aug/rule/LLM。
- [x] CWRU LOLO 汇总：已报告四折均值±折间波动、每折 Wilcoxon+Holm；2400/2400 行齐全，90 个预注册比较全部 Holm q<0.05 且 mean_delta>0。
- [x] 生成 CWRU cross-condition heatmap 素材 CSV：`breeze/results/cwru_patch_v2_2026-07-07/cwru_patch_v2_summary.csv` 与 `cwru_patch_v2_lolo_fold_summary.csv`；旧 `lolo_load1` optional-stopping 记录仅内部保留，不进入论文主结论。
- [x] CWRU 修正版产物冻结到独立目录 `breeze/results/cwru_patch_v2_2026-07-07_frozen/`，含 `manifest_sha256.txt`；本轮新增 API 用量为 0。

### 12.C 轴承线遗留
- [x] PU LOCO split：已生成 `proc/pu_loco_<condition>_{train,test}.npz`，split unit 为 operating condition；四折 train/test 类计数已核对，无窗口级随机划分。
- [x] PU LOCO downstream/summarizer 脚本：已新增 `breeze/scripts/run_pu_loco_downstream.py` 与 `breeze/scripts/summarize_pu_loco.py`，协议为 40 seeds、n_real={5,10,25}、每 `(heldout,n_real,metric)` 内 Holm。
- [x] PU LOCO 折内 pool 构建脚本：已新增 `breeze/scripts/build_pu_loco_pools.py`，支持非 held-out 条件重渲染、condition-specific verifier、rule/random/LLM 三源；`random_open_loop` 已修正为不经过 verifier。
- [x] PU LOCO LLM small smoke：旧 N09 Phase-A 池不能用于 LOCO（held-out N09 泄漏、其他条件工况不匹配）；旧 LLM recipe 模板重配置 smoke 不达标（heldout=N09，45 slots accepted=4，kept healthy=0/OR=5/IR=15）。折内小批量 LLM API 四折完成，均通过 ≥30% 总体 slot acceptance；累计 API 到 701/2000。四折 kept counts：N09_M07_F10 healthy=6/OR=2/IR=10；N15_M01_F10 healthy=6/OR=5/IR=8；N15_M07_F04 healthy=8/OR=4/IR=10；N15_M07_F10 healthy=8/OR=1/IR=11。OR 为稳定弱类，不能直接下游，下一步必须按每折每类目标 accepted count 断点续跑补齐。
- [x] PU LOCO LLM target-count scaler：已新增并运行按 heldout fold 和 class 均衡的 LLM pool 扩展，目标 n_syn=20/class；四折均 `target_reached`，最终 kept counts 为 N09_M07_F10 20/22/24，N15_M01_F10 21/26/23，N15_M07_F04 21/22/21，N15_M07_F10 23/25/28（healthy/OR/IR）。PU LOCO LLM pool 总 API=133 次，本阶段累计 770/2000。报告：`breeze/runs/pu_loco_llm_smoke_2026-07-07_v3/pu_loco_llm_pool_report.md`。
- [x] PU LOCO non-LLM pools：已生成每折 rule 和 random_open_loop class-balanced pools；random_open_loop 直接入池不经过 verifier，rule 经过相同 train-only verifier；每折每类均 ≥20。rule 在两个折初次不足，已用同目录断点续跑把 slots_per_class 从 5 扩到 10 后补足，见 `breeze/runs/pu_loco_nonllm_pools_2026-07-07/pu_loco_nonllm_pool_report.md`。
- [x] PU LOCO downstream v1：正式协议 4 folds × 5 methods × n_real={5,10,25} × 40 seeds 已完成，20 个 CSV 全部 121 行，`pu_loco_summary.csv` / `pu_loco_wilcoxon.csv` / `pu_loco_report.md` 已生成。
- [blocked] PU LOCO claim：v1 不达标，96 个注册比较中 57 个未通过；LLM 在多数组合低于 `noise_aug`，且 N09/N15_M01 的 IR、N15_M07_F04 的 OR 是主要弱类。失败分析见 `breeze/results/pu_loco_2026-07-07/pu_loco_v1_failure_analysis.md`。后续若继续优化 PU LOCO，必须在训练折内部 validation 上选方案，并用新目录重跑，不能用本次 held-out test 结果调参。
- [x] PU LOCO v2 condition-aware diagnosis：按用户 2026-07-08 指令，v1 根因假设更新为“训练工况频率渲染导致 held-out 工况 BPFO/BPFI/转频错位”。已用 recipe metadata + 工况元数据诊断，不读取 held-out 波形/标签；266 条 accepted OR/IR recipe 中 125 条相对 held-out 目标频率误差 >10%，跨 900↔1500 rpm 误差固定为 +66.7% 或 -40.0%。报告：`breeze/results/pu_loco_v2_2026-07-08/pu_loco_v1_frequency_mismatch_report.md`。
- [x] PU LOCO v2 preregistration：已写 `breeze/results/pu_loco_v2_2026-07-08/pu_loco_v2_preregistration.md`，明确可用 held-out 工况元数据、禁止 held-out 波形/标签、condition-aware generation、训练折外推 verifier、新目录、统计族和 pass/fail 解释。
- [x] PU LOCO v2 pool/downstream：用户 2026-07-08 最新补丁确认 `pu_loco_v2_preregistration.md`，已按预注册直接跑完，未更改协议；零 API 复用 v1 已接受 LLM morphology，只按 held-out 工况重写 `fr_hz`、BPFO/BPFI impact rate、current fault frequency；四折池均达到 ≥20/class，downstream 2400/2400 行齐全，新增 API=0。
- [blocked] PU LOCO v2 claim：v2 未通过，96 个注册 Holm 比较中 60 个失败；四折均值 LLM 仍低于 `noise_aug`，且 N09/N15_M01 的 IR、N15_M07_F04/N15_M07_F10 的 OR 仍是弱类。报告见 `breeze/results/pu_loco_v2_2026-07-08/pu_loco_v2_failure_analysis.md`。不能把 PU LOCO v2 写成 cross-condition 成功；若后续做 LOCO v3，必须另行预注册并只用训练折内部 validation 选方案。
- [in_progress] PU LOCO v3 option-B attack：用户 2026-07-08 新补丁要求在 v1/v2 冻结基础上做训练工况内模拟 LOCO。第一步零 API 形态-工况关系诊断已完成，只用 4 个工况训练轴承数据；内部模拟 4 折未赢 `noise_aug` 前禁止触碰正式 held-out test。
- [x] PU LOCO v3 morphology map：量化每工况×类别的共振带能量、RMS/kurtosis/crest、包络峰 prominence、调制深度、背景谱形离散峰/底噪，并回归/趋势分析其与 rpm、torque、radial load 的关系。报告：`breeze/results/pu_loco_v3_2026-07-08/morphology_condition_map.md`。关键结论：IR 的 3-3.6 kHz 共振能量、包络峰和调制深度可插值；OR 的 600-1200 Hz 共振能量和 crest 可插值，但 OR 包络峰/调制弱预测；不可预测特征不能盲目外推。
- [in_progress] PU LOCO v3 internal simulated LOCO：4 个工况轮换伪 held-out；伪 held-out 真实窗口仅评估，不用于生成/校准；已生成 train-bearing-only internal splits 和 real_only/noise_aug baseline；下一步跑候选池 n_real={5,10,25}、10 seeds smoke，与 `noise_aug` 比较。
- [in_progress] PU LOCO v3 candidates：已新增 `breeze/scripts/build_pu_loco_v3_internal_candidates.py`，候选 1=`morphology_idw`（训练工况形态逆距离插值+heldout kinematics），候选 2=`morphology_nearest`（最近训练工况形态+heldout kinematics），均零 API、复用 accepted v1 LLM recipe 结构并写入新目录；LLM 工况外推推理（≤50 API，先≤15）和 LLM+noise hybrid 只有在候选 1/2 内部未赢 `noise_aug` 后再考虑。
- [ ] XJTU-SY：等待用户下载完成后，先校验 rar 完整性和解压清单；再做实验/轴承级 split、标签定义、M4 配置、verifier 校准、小批量 ≤30 API smoke，达标后才放量。
- [ ] XJTU-SY：如果只能定义 run-to-failure 退化档而非故障诊断类别，先停下报告 claim 边界，不把末端失效位置扩张成逐窗口标签。

### 12.D 铣削线：Berkeley/NASA + UMich CNC

#### 12.D.Berkeley 2026-07-08 独立窗口攻坚清单

执行根目录：`/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/`。所有 Python 命令使用 `breeze/.venv-breeze/bin/python`。本清单只允许用 `proc/milling_berkeley_inner_train.npz` 与 `proc/milling_berkeley_inner_val.npz` 做迭代选择；正式 held-out test 只能在 inner-val 达标、预注册写完后一次性执行。

- [completed] Step 0 差距诊断：读取当前 v4/v5 LLM 池、rule、noise_aug、random open-loop 与 inner-train/inner-val 下游结果，生成 `breeze/results/milling_berkeley_inner_attack_2026-07-08/berkeley_gap_diagnosis.md`。
- [completed] Step 0.1 PSD/频带诊断：按 `sharp/worn/severe` 和通道计算平均 PSD、band energy、PSD-W1，定位 LLM 与真实/对照错配频段。
- [completed] Step 0.2 时域统计诊断：计算 RMS、kurtosis、crest、每齿周期统计分布重叠，和 noise_aug/rule 保留结构对比。
- [completed] Step 0.3 通道结构诊断：检查力/振动/AE/电流通道幅值比、互相关、共模板迹象，并对照 noise_aug/rule。
- [completed] Step 0.4 下游错误诊断：汇总 inner-val 混淆矩阵、弱类与物理判别特征，明确优先补强结构。
- [completed] Step 1 零 API 分通道真实 exemplar + per-band EQ：已在 `milling_generation.py` 中加入 train-only per-class/channel band fractions、`band_eq_strength` 和 rerender 支持；v6/v7/v8 均只用 inner-train/inner-val 评估。
- [completed] Step 1 smoke：v6/v7/v8/v9/v10/v11/v12 候选均已在 inner-val 上跑 n={2,5,10}、10 seeds，并写入 iteration log 与对比 CSV。
- [completed] Step 1 LLM 小批量：repair prompt 共新增 30 API，accepted slots 总计 30/30；API 已记录到 `breeze/results/phaseB_api_usage_log.csv`，但 inner-val gate 未通过。
- [completed] Step 2 类间排序约束：已尝试 high-margin template、full-train-margin template、repair prompt 和 prototype-admitted soft gate；均只用 inner-train 特征构造。
- [completed] Step 3 混合背景渲染：已实现 inner-train 真实背景片段 + LLM 磨损特征叠加的 full-train-margin / coherent EQ rerender，日志中标注 exemplar-grounded。
- [completed] Step 4 n_syn/K 扫描：在 inner-val 上完成 `n_syn in {10,20,40}` 扫描，候选最高 3/6 checks，未达到预注册门槛。
- [blocked] Step 5 达标判定：inner-val 上 Acc/Macro-F1 六项未达到 ≥5 项 LLM 同时 ≥ rule 且 ≥ noise_aug；不得写 `berkeley_v6_preregistration.md`。
- [blocked] Step 5 formal：由于预注册门槛未过，正式 40-seed held-out test 禁止执行，本窗口未跑。
- [completed] Stop condition：Step 1-4 已穷尽仍不达标；已输出完整攻坚报告、每轮日志、inner-val 曲线和 API 用量，等待用户决定是否换策略。
- [x] Berkeley/NASA milling：读取 `mill.mat` 与 `Readme.pdf`，写规格表（采样率、通道、实验数、VB/磨损标签、窗长、split）；输出 `breeze/results/milling_preprocess_2026-07-07/specification.md` 和 `specification.csv`。
- [x] Berkeley/NASA milling：按 case/file 划分 split；VB 三档 frozen 为 sharp<0.2 / worn 0.2-0.45 / severe>0.45，train counts sharp=629/worn=731/severe=476，test counts sharp=221/worn=255/severe=170。
- [x] UMich CNC：读取 `data/archive/train.csv` 与 `experiment_*.csv`，写规格表（100 ms 采样、4 轴/主轴电流通道、18 实验、worn/unworn、文件级 split）；train counts unworn=91/worn=117，test counts unworn=31/worn=27。
- [ ] 两个铣削数据先跑 real_only few-shot；若饱和，shot 档降为 n={2,5,10}；仍无空间则该数据集降级为 verifier 审计并停下讨论。
- [x] Berkeley verifier/pool smoke：c=90 train-only 低采样率 verifier 已跑通；rule/random/LLM pools 均达到 B=20/class。LLM compact prompt v3 接受率 83.3%，rescreen v4 零 API 合并后 counts sharp=55/worn=34/severe=23。报告：`breeze/results/milling_berkeley_2026-07-08/berkeley_smoke_report.md`。
- [blocked] Berkeley downstream claim：held-out test smoke 已冻结为失败开发记录，不能进入正式 40 seeds。按用户 2026-07-08 要求，Berkeley inner-val 攻坚已穷尽分通道真实 exemplar、per-band EQ、类间排序约束、混合背景+磨损特征叠加、repair LLM prompt、pool combination、prototype-admitted soft gate 和 n_syn 扫描；最佳候选仍未达到 5/6 gate。预注册未写，正式 held-out 未跑。报告：`breeze/results/milling_berkeley_inner_attack_2026-07-08/berkeley_inner_attack_report.md`；迭代日志：`breeze/results/milling_berkeley_inner_attack_2026-07-08/iteration_log.md`。

#### 12.D.Berkeley v2 0.2/0.7 文献协议重构

执行边界：Berkeley v2 是 test 前协议修订，依据外部文献标准与 v1 inner-val 失败诊断；沿用 case/run 级 split 单元，只换标签定义；所有选择仍只用 inner-train/inner-val，正式 held-out 只能在预注册后一次性运行。

- [completed] Berkeley v2 todo 初始化：更新本清单，建立新结果目录 `breeze/results/milling_berkeley_v2_2026-07-08/` 与新运行目录前缀，冻结 v1 失败产物不动。
- [completed] Berkeley v2 文献依据记录：已写 `berkeley_v2_protocol.md`；引用 `tvhahn/ml-tool-wear` 0.2/0.7 标签实现与 NASA PCoE Berkeley Milling 数据集，ISO 3685 仅作待核标准背景。
- [completed] Berkeley v2 重新分档：按 Healthy `VB<0.2`、Degradation `0.2<=VB<0.7`、Failure `VB>=0.7` 重建 train/test 与 inner train/val NPZ，沿用原 split 单元；train counts 629/1054/153，test counts 221/374/51。
- [completed] Berkeley v2 可分性 smoke：三分类 inner-val 显示 healthy/degradation 可分，但 failure mean F1 仍低于 0.4；冻结三分类路线，不进入三分类 formal。
- [blocked] Berkeley v2 三分类 inner attack：failure 样本支持和 separability 不足，按 v2 决策规则转二分类，未写三分类预注册。
- [completed] Berkeley v2 二分类出口：已建立 Healthy vs Degraded 二分类，inner-val `n_syn=20` 达到 LLM ≥ rule 且 ≥ noise_aug 的 6/6 gate，并写 `berkeley_v2_binary_preregistration.md`。
- [blocked] Berkeley v2 formal：预注册后正式 40-seed held-out test 已一次性完成；15/18 注册比较通过，但 LLM>rule 在 n=2 Macro-F1、n=10 Acc、n=10 Macro-F1 未过 Holm，Berkeley v2 binary 判定 partial/no-go，不再调参。

#### 12.D.UMich v1 二分类优先攻

执行边界：UMich 使用 experiment-level split，worn/unworn 二分类；实际主轴转速来自 CSV 过程列，若找不到刀齿数只使用主轴转频谐波族，不编造 TPF。

- [completed] UMich 数据/元数据审计：读取 `data/archive/train.csv` 与 `experiment_*.csv`；确认标签为 `tool_condition` 二分类 `unworn/worn`，本地 README 未给出可审计刀齿数；未把 `S1_ActualVelocity` 编造成 TPF。
- [completed] UMich split/inner split：按 experiment-level split 重建 `milling_umich_v2` 6 动态电流通道 NPZ；train counts unworn=91/worn=117，test counts unworn=31/worn=27；inner train 74/93，inner val 17/24，无窗口随机泄漏。
- [completed] UMich real_only smoke：n={2,5,10}、10 seeds 完成，任务未饱和且有增强空间；结果写入 `breeze/results/milling_umich_v2_2026-07-08/downstream_real_only_10seed/`。
- [completed] UMich verifier/rule/random smoke：排除常量 Z 电流通道后，rule 接受 39/40 slots、169 windows，random_open_loop 200 windows；inner-val 对照完成。
- [completed] UMich LLM smoke：两轮 30-slot LLM smoke 均达到 30/30 accepted；v1 counts 75/75，v2 repair counts 71/72；所有调用写入 API 流水，密钥未落盘。
- [blocked] UMich full inner gate：`n_syn in {10,20,40}` 扫描完成，最佳 LLM v2 仅 2/6 gate（Acc at n=2/5），Macro-F1 全未达到 noise_aug/random/rule；未写预注册，正式 40-seed held-out test 禁止执行。
- [completed] UMich verifier/LLM 小批量：未确认刀齿数，因此 UMich verifier/prompt 不使用 TPF；只使用 process statistics、PSD shape、trend、channel correlation。
- [blocked] 铣削下游正式对照：UMich inner-val 未过 5/6 gate；不得跑正式 40 seeds，不做 Holm formal claim。
- [blocked] 铣削物理真实性：UMich 无可信 TPF 元数据，因此不报告 TPF 谐波误差；保留 PSD/verifier 审计和 no-go 报告。
- [completed] UMich v3 纯血 exemplar：预处理已把 `tool_condition`、`passed_visual_inspection`、`machining_finalized` 写入 NPZ；纯血 inner_train exemplar 为 unworn=68、worn=24，来源 experiment_11/12/17 与 09/10，held-out/inner-val 纯血样本不进入 exemplar。
- [blocked] UMich v3 纯血 LLM：纯血校准 LLM smoke 30 API 后 only unworn accepted；zero-API real-exemplar rescue 得到 unworn=71/worn=18，但 n_syn=10 inner-val 仅 1/6 gate，仍不预注册、不跑 formal。

#### 12.D.UMich v4 任务可学性修复

执行边界：Berkeley v2 binary formal 已冻结为 partial/no-go；UMich v4 在进入任何 LLM synthetic 生成前，必须先证明 clean label、主动切削阶段、stage/metadata 控制后的真实数据可学。API 从 1020/3000 起算；本小节 learnability repair 阶段新增 API 必须为 0。

- [completed] v4 todo 初始化：按用户 `铣削线 v4` 附件冻结 Berkeley 结论，并将 UMich v4 主线拆成标签四象限、阶段过滤、阶段对齐、工况混杂审计、split 修复、可学性门槛、生成攻坚七步。
- [completed] v4 stage-contiguous 预处理：已新增 `preprocess_umich_v4_task_repair.py`，仅保留主动切削 `Layer * Up/Down` 阶段，窗口不跨 `Machining_Process` 边界，source unit 保持 experiment-level；已生成 multi-stage 与 `Layer 1 Up` 单阶段 train/test、inner train/val NPZ。
- [completed] v4 stage-zscore：已新增 `standardize_umich_by_stage.py`，按 inner-train 每阶段统计做 channel z-score；已生成 multi-stage stage-z inner train/val NPZ。
- [completed] v4 metadata channel：已新增并编译 `augment_umich_metadata_channels.py`；已生成 raw+stage-z 的 feedrate/clamp_pressure/stage one-hot 常量通道版本，包括 clean inner split 版本。
- [completed] v4 clean-aware split 修复：旧 all-label inner-val 中 clean worn=0，已新增 `build_umich_v4_clean_inner_split.py` 并从 outer-train stage-contiguous NPZ 重建 clean-only experiment-level inner split；inner_train clean counts unworn=59/worn=13，inner_val clean counts unworn=14/worn=6。
- [completed] v4 四象限与阶段/工况审计：已输出 experiment-level、window-level、stage-level、feedrate/clamp_pressure-level clean/ambiguous counts；outer-train active-stage windows=184，其中 clean supervised=92，非主动或 ambiguous 移除=168。
- [completed] v4 metadata-only/stage-only/signal-only baseline：只用 clean inner-train/inner-val；metadata-only Acc/Macro-F1=1.0/1.0，stage-only=0.45/0.4486，signal-feature-only=1.0/1.0；确认 clean 标签与 feedrate/clamp_pressure 严重混杂。
- [completed] v4 real_only learnability gate：比较 all-label raw/stage-z/single-stage 与 clean raw/stage-z/meta/stage-z+meta。clean raw full Acc/Macro-F1=0.94/0.9001，n=10=0.63/0.6106；clean stage-z+meta full=0.94/0.8824，n=10=0.895/0.8856；数值门槛通过，但 metadata confound gate 失败。
- [blocked] v4 stop/go：已输出 `breeze/results/milling_umich_v4_task_repair_2026-07-09/umich_v4_task_repair_report.md`；clean_unworn 条件只在 (3,2.5),(3,3),(3,4),(6,3)，clean_worn 只在 (12,4),(15,4)，无 feedrate×clamp 条件重叠，condition-balanced clean split 不成立。按用户规则停止在 LLM 生成前，新增 API=0，累计仍 1020/3000。

#### 12.D.MU-TCM small subset 0-API 审计

执行边界：只审计 `data/MU-TCM face-milling dataset/small_subset` 是否有潜力作为新 milling formal 数据集；不调用 LLM/API，不构造 formal held-out test，不使用随机窗口 split，不把 small subset 当 formal conclusion。

- [completed] MU-TCM small 文件树审计：已扫描已解压目录与 `small_subset.7z`，输出 `breeze/results/mutcm_small_audit_2026-07-09/mutcm_small_file_tree_report.md`；本地无 `7z/7zz/py7zr`，压缩包清单未单独读取，使用已存在解压目录。
- [completed] MU-TCM small metadata 自动识别：已从 synced MAT 元数据、文件名、`signals_stats.csv`、VB 图像目录识别 experiment info、material、Vc、fz、ap、ae、VB、sensor paths 和 sampling-rate family；输出 `mutcm_small_metadata_summary.csv`。
- [completed] MU-TCM small condition support：已输出 `mutcm_small_condition_wear_support.csv`；CastIron.GG30 与 StainlessSteel.316L 在同一 Vc=100/fz=0.1/ap=1.5 下均覆盖 VB_level 0.0/0.1/0.2/0.3，说明 small subset 比 UMich clean subset 更少工况-confound。
- [completed] MU-TCM small labels：方案 A `VB_level in {0.0,0.1}` vs `{0.2,0.3}` 得到 healthy=4/worn=4，可做 experiment-level LOEO 诊断；方案 B 严格 `VB==0.0` vs `VB>=0.2` 只有 healthy=1/worn=4，不支持 LOEO formal。
- [completed] MU-TCM small metadata-only/signal-only baseline：方案 A metadata-only LOEO Acc/Macro-F1=0.0/0.0，signal-only=0.625/0.619，高于多数类基线 0.5；输出 `mutcm_small_baseline_summary.csv` 与 `mutcm_small_confound_audit.md`。
- [completed] MU-TCM small stop/go：small subset 通过“同条件多磨损级、metadata-only 不近 100%、signal-only 高于随机线、方案 A 支持数足够、experiment-level split 可构造”的初筛；但仅 8 个 experiment，不是 formal 结果。下一步若继续，应审计全量 MU-TCM 并重新预注册，而不是直接用 small subset formal。

#### 12.D.MU-TCM full_dataset light 0-API 审计

执行边界：full_dataset 太大，不完整解压；只从 `full_dataset.7z` 抽取 `signals_stats.csv` 和 `signals_sync.csv` 到 `breeze/results/mutcm_full_light_audit_2026-07-09/extracted_csv/`。不解压 `signals_synced/*.mat` 或 `signals_unsynced/*.mat`，不调用 LLM/API，不预注册，不跑 formal。

- [completed] MU-TCM full light 文件树：使用 `bsdtar -tf` 只读压缩包清单，确认 synced MAT=67、unsynced MAT=67、VB jpg=74、CSV=2，`signals_stats.csv` 和 `signals_sync.csv` 均存在；输出 `full_dataset_file_tree_report.md`。
- [completed] MU-TCM full light metadata：基于 `signals_stats.csv`、文件名和 README 工况说明构建 experiment-level metadata，67 行；输出 `mutcm_full_metadata_summary.csv` 和 `mutcm_full_metadata_report.md`。
- [completed] MU-TCM full light support：8 个 cutting conditions 全部覆盖 rounded VB level 0.0/0.1/0.2/0.3，且每个 condition×VB_level 至少 2 repetitions；输出 `mutcm_full_condition_wear_support.csv` 和 report。
- [completed] MU-TCM full light labels：Scheme A healthy=33/worn=34，Scheme B healthy=17/worn=34/drop=16，Scheme C healthy=33/worn=34；三者均支持 experiment-level split、leave-one-condition-out 和 n_real={2,5,10}，推荐优先 Scheme A。
- [completed] MU-TCM full light metadata confound：metadata_safe（material+Vc+fz+ap+ae+Lubrication）不接近 1.0；Scheme A LOGO condition Acc/Macro-F1=0.4925/0.4924。metadata_leaky（加入 Insert/Edge/Repetition）在非 insert-edge 隔离 split 下为 1.0，说明正式协议必须强制 insert-edge grouped isolation，不能把工具身份当安全特征。
- [completed] MU-TCM full light signal baseline：仅使用 `signals_stats.csv` 的信号统计特征（180 列，去掉文件名/VB/metadata/start/end 等泄漏列）。Scheme A best signal-only：LOEO 0.970/0.970，LOGO condition 0.896/0.896，GroupKFold condition 0.881/0.881，GroupKFold insert-edge 0.866/0.865，均明显高于多数类 0.507。
- [completed] MU-TCM full light stop/go：输出 `mutcm_full_audit_pass.md`，判定通过 light audit，可进入下一步“只抽取 signals_synced MAT、构建 experiment-level NPZ、重新做 inner-val/prereg 前审计”；该结论不是 formal success，新增 API=0，累计仍 1020/3000。

#### 12.D.MU-TCM v2 synced-MAT no-API inner gate

执行边界：只抽取 `full_dataset/signals_synced/*.mat`；禁止抽取 `signals_unsynced/*.mat`；不调用 LLM/API，不预注册，不跑 formal test。所有 split 以 experiment/MAT 文件为最小隔离单位，Insert/Edge/Repetition 只作为 group/diagnostic 字段，不能作为安全特征。

- [completed] MU-TCM v2 pipeline 初始化：新增 `breeze/scripts/mutcm_v2_synced_pipeline.py`，统一生成 synced extraction、metadata index、experiment-level NPZ、window-level NPZ、split 诊断和 no-API baseline gate 产物。
- [completed] MU-TCM v2 synced 抽取：从 `full_dataset.7z` 只抽取 `signals_synced/*.mat`，输出 `mutcm_v2_synced_extract_report.md`；67/67 MAT 与 `signals_stats.csv` 对齐，缺失/额外文件均为空，`signals_unsynced` 未抽取。
- [completed] MU-TCM v2 metadata index：输出 `mutcm_v2_metadata_index.csv` 与 report，字段包括 sample/file/MAT path、Insert/Edge/Repetition、material/Lubrication、Vc/fz/ap/ae、VB/rounded_VB、Scheme A label、condition_id、insert_edge_id、group_experiment。
- [completed] MU-TCM v2 experiment-level NPZ：基于 `signals_stats.csv` 的非泄漏 signal statistics features 构建 `proc/mutcm_v2_schemeA_experiment_features.npz`，形状 `(67, 180)`，类别 healthy=33/worn=34。
- [completed] MU-TCM v2 window-level NPZ：从 synced MAT 中读取 force/vibration/AE/internal CNC 通道，按 experiment 限额采样，输出 0.5s `proc/mutcm_v2_schemeA_window_signal_0p5s.npz` `(804, 19, 1000)`、1.0s `proc/mutcm_v2_schemeA_window_signal_1p0s.npz` `(783, 19, 2000)`，canonical `proc/mutcm_v2_schemeA_window_signal.npz` 镜像 1.0s；NaN/Inf=0。
- [completed] MU-TCM v2 split 诊断：构造 condition-aware inner split、GroupKFold by condition、GroupKFold by insert_edge；inner_train label balanced 25/25 且支持 n_real={2,5,10}，inner_val 8/9；输出 `mutcm_v2_split_report.md`。
- [completed] MU-TCM v2 no-API baseline gate：跑 majority、metadata_safe、metadata_leaky diagnostic、real_only、noise_aug、rule、random_open_loop；20 seeds、n_real={2,5,10} 与 full inner-train；gate 通过，real_only full Acc/Macro-F1=0.8235/0.8211，n_real=10=0.7941/0.7864，metadata_safe full=0.4706/0.3200，rule full=0.7059/0.6886；仍未进入 LLM/prereg/formal。

#### 12.D.MU-TCM v3 LLM inner-val attack

执行边界：只使用 v2 固定 inner_train/inner_val；不读取或运行 formal held-out test；不预注册，除非 inner-val gate 先通过；API 从累计 1020/3000 起算，本轮上限 180 次；所有请求串行且间隔 >=2 秒；`_file_name`、VB、rounded_VB、Insert/Edge/Repetition、material/Vc/fz/ap/ae/condition_id 不能作为安全模型特征。

- [completed] MU-TCM v3 脚本与断点续跑：新增 `breeze/scripts/mutcm_v3_llm_inner_attack.py`，输出到 `breeze/results/mutcm_v3_llm_inner_2026-07-09/`，覆盖 split、exemplar、LLM prompt/API/admission、inner-val scan、Holm/gate。
- [completed] MU-TCM v3 固定 split：从 v2 assignments 构造 `mutcm_v3_inner_split_index.csv` 和 `mutcm_v3_inner_split_report.md`，同一 MAT 文件窗口未跨 split。
- [completed] MU-TCM v3 inner-train exemplar：只用 inner_train 统计 channel stats、PSD/band、class difference 和 VB-level monotonic diagnostics，输出 `mutcm_v3_inner_train_exemplar_stats.json` 与 `mutcm_v3_class_difference_report.md`。
- [completed] MU-TCM v3 LLM recipe generation：生成 prototype/boundary/condition-balanced recipe，API=51/180，LLM pool healthy=60/worn=61；prompt/API/admission 记录已输出，key 未写入日志。
- [completed] MU-TCM v3 n_syn scan：在 inner-val 上扫 n_real={2,5,10}、n_syn={10,20,40}、20 seeds，对 real_only/noise_aug/rule/random_open_loop/LLM_synthetic 输出 summary/per-class/condition/Wilcoxon-Holm；ExtraTrees 主结果 selected n_syn=20。
- [completed] MU-TCM v3 gate 判定：ExtraTrees 主结果 gate=2/6，variant_no_boundary=0/6，LogisticRegression 诊断=2/6 且有收敛 warning；未写 preregistration，未运行 formal test，输出 `mutcm_v3_inner_attack_fail_analysis.md`。

### 12.E 论文定位 A 重写前置条件
- [ ] 5 数据集规格表全部由本地数据和公开文档支撑；私有机床和 IMS 不进入论文主体。
- [ ] 摘要/标题/引言按 machinery-level 统一框架重写，但只在两条实验线关账后开始。
- [ ] Related Work 补 taxonomy：LLM-description generation / physics-informed GAN / physics-informed diffusion / verifier-guided admission，并补 TimeGAN、SigCWGAN、TTS-GAN、TTS-CGAN、DDPM、CFG-DDPM、physics-informed diffusion。
- [ ] 方法章按框架总览 → `KinematicsPlugin` → 轴承实例化 → 铣削实例化 → recipe/schema/renderer/gates/feedback 重排。
- [ ] 若两个铣削数据集只有一个完整达标，写作前停下，与用户确认是否回退到“轴承主线 + 跨域章”定位。

## 11. 最新冲刺任务：阶段 A 生死实验优先（当前活动）

阶段 A 验收门槛：在 PU `N09_M07_F10` 文件划分协议上，同预算、同 renderer、同 verifier 比较 random recipe、rule recipe、LLM closed-loop K=3 recipe，经 CNN 8 seeds × n_real=10/25/50 下游验证；LLM 必须在 Accuracy 和 Macro-F1 上显著高于 random 和 rule（Wilcoxon + Holm/BH q<0.05）。若不达标，立即停止阶段 B/C/D/E/F/G 扩展，报告失败原因和 claim 调整建议。

执行边界：
- [x] 暂停阶段 B 数据集扩展：JUST 大文件下载已中断，保留 partial 文件用于未来 `curl -C -` 续传；不继续 XJTU/CWRU/DIRG/JUST/HIT 大规模实验。
- [x] 读取 `breeze/HANDOVER.md`，确认正式 LLM K=3 池为 `breeze/runs/pool_breeze_k3.npz` / `breeze/runs/pool_physics_file_k3/`，旧文件划分 verifier K=3 接受率约 78.9%。
- [x] 核对现有 random/rule 对照：`recipe_ablation_random_v2_full` 为同 renderer + v2 verifier 的物理范围随机 recipe，450 slots 0 accepted；`recipe_ablation_rule_v2_full` 为同 renderer + v2 verifier 的规则 recipe，450 slots 167 accepted，703 windows after diversity。
- [x] 核对 LLM K=3 与 random/rule 是否同一 verifier：`rescreen_v2_full` 已确认以 `pool_physics_file_k3` 为输入，用同一 v2 verifier 离线重筛，保留 K=3 闭环 provenance 且与 random/rule v2 对齐。
- [x] 生成阶段 A 三组统一 pool summary：`breeze/results/phaseA_pool_summary.csv`。random 0/450 accepted；rule 167/450 accepted、703 kept；LLM K=3+v2 286/450 accepted、757 kept。
- [x] 下游 smoke：三组 pool 在 CNN 上跑 n_real=10、seeds=0/1，`eval_custom_pool.py` 对空 random pool、rule pool、LLM pool 均能断点续跑且 CSV 字段完整。
- [x] 下游 full：CNN 8 seeds × n_real=10/25/50 已完成，输出 `breeze/results/phaseA_downstream_cnn.csv`（96 结果行）。
- [x] 统计检验：Accuracy 和 Macro-F1 分别做 paired Wilcoxon，LLM-vs-random 与 LLM-vs-rule 做 Holm/BH 校正；输出 `breeze/results/phaseA_downstream_summary.csv`、`breeze/results/phaseA_wilcoxon_holm_bh.csv`、`reports/phaseA_gate_report_2026-07-05.md`。
- [ ] circular-validation 证据：因阶段 A downstream gate 已失败，按最新指令停止，不继续计算 discriminator AUROC / nearest-neighbor 扩展指标。后续只有在用户决定迭代 LLM 机制并重跑阶段 A 时再补齐。
- [x] 阶段 A 判定：FAILED。LLM K=3+v2 显著优于 random，但不显著优于 rule；50-shot 对 rule 的 Accuracy 和 Macro-F1 均略低。停止阶段 B/C/D/E/F/G，不写 SOTA/可靠生成 claim。

### 11.B Phase-A v2 补丁重跑（当前活动）

补丁原则：上一轮 Phase-A 失败后不进入 Phase B。本轮先修正预算不对等、random 对照退化和统计功效不足；仍禁止进入 Phase B/C/D/E/F/G，除非 Phase-A v2 通过修订门槛。

- [x] 合成预算对等化：补跑 rule IR 类，不耗 LLM API；rule kept 变为 healthy=227、OR=407、IR=151，因此统一预算可取 B=150。
- [x] 构建 balanced pools：LLM、rule、random open-loop 均按类均衡到 B=150，固定 seed `20260705`，已写出 NPZ 与 manifest；random+verifier 0% 接受率单独报告，不参与下游。
- [x] 增加 random open-loop：复用相同随机 recipe family，不经 verifier 直接入池，按类截到 B=150。
- [x] 下游 smoke：n_real=5/10，seeds=0/1，四组 real_only/random_open_loop/rule/LLM 已跑通，确认 n=5 可抽样、CSV 可断点续跑。
- [x] 下游 full：20 seeds × n_real={5,10,25,50} × 4 组完成，输出 `breeze/results/phaseA_v2_downstream_cnn.csv`，321 行完整。
- [x] 预注册检验族：每个 n_real 一族，族内两比较（LLM>random_open_loop、LLM>rule），Accuracy 和 Macro-F1 分开成族；族内 Holm，全局 BH 参考，输出 `breeze/results/phaseA_v2_wilcoxon.csv`。
- [x] LLM 池零 API 补足核对：LLM kept healthy=192、OR=304、IR=261，均 ≥B=150，无需额外 API 或多种子补足。
- [x] API 用量记录：本轮新增 LLM API 调用为 0；结果来自缓存 K=3 LLM 池 + 本地 rescreen/balanced sampling/downstream 训练。
- [x] Phase-A v2 判定：PASSED。n≤25 的 Acc/Macro-F1 均 Holm q<0.05 显著优于 random open-loop 和 rule；n=50 LLM 对 rule 为正向差值且优于 real_only。报告见 `breeze/results/phaseA_v2_gate_report.md`。
- [x] Phase-A v2 产物冻结：2026-07-06 创建只读快照 `breeze/results/phaseA_v2_frozen_2026-07-06/`，包含 pools、CSV、报告、选样 manifest、rule/random/rescreen slot summary 共 21 个产物；校验清单为 `manifest_sha256.csv`。后续任何重跑必须使用新目录和新文件名前缀，不覆盖 Phase-A v2 原产物或冻结快照。
- [x] 论文披露约束：rule 的 IR 为瓶颈类，补到 balanced B=150 时使用 400 个 IR slots、59 个 accepted slots，补跑接受率 14.75%；论文需如实报告各来源 slot 消耗和接受率。

### 11.C Phase B 数据集扩展（当前活动）

阶段 B 目标：在 Phase-A v2 通过并冻结后，按用户 2026-07-06 最新顺序执行 CWRU → XJTU → IMS。DIRG/PU 的本地审计结果保留为补充候选，但不再替代当前顺序。每个数据集都必须先做 M4 运动学重配置、train-only verifier 重校准和 ≤30 次 API 的 LLM 小批量接受率验证；接受率、失败原因和 API 用量达标后再放量。API 计数从用户提供当前 endpoint/key 起重置为 0，key 不写入项目文件，总预算上限沿用 ≤2000 次。

- [x] Phase B 资源/API 预算预估：协议审计阶段新增 LLM API 调用为 0；2026-07-06 用户已提供 API endpoint/key，后续调用从 0 开始累计，阶段用量写入 `breeze/results/phaseB_api_usage_log.csv`。
- [x] Phase B 数据集顺序重排：当前顺序冻结为 CWRU → XJTU → IMS；旧的“XJTU 跳过、DIRG 优先”记录只作为历史审计，不再控制当前执行顺序。
- [x] CWRU 协议 smoke：读取已冻结 CWRU splits，核对每类窗口数、condition/负载拆分、无窗口泄漏；生成 `breeze/results/phaseB_cwru_protocol_summary.csv`。
- [x] CWRU verifier/renderer 适配设计：按 CWRU drive-end 6205-2RS JEM SKF 轴承几何和转速计算 BPFO/BPFI/BSF/FTF，写明通道、fs、window、fault sizes；输出 `breeze/results/phaseB_cwru_physics_config.csv`、`.json` 和 `phaseB_cwru_verifier_renderer_design.md`。
- [x] CWRU rule/random synthetic smoke：实现单通道 vibration renderer + train-only verifier，within_load0 小样本已跑通；random+verifier 0/32 accepted，rule 30/32 accepted slots、四类均有 accepted items，输出 `breeze/runs/phaseB_cwru_within_load0_rule_smoke_v5/pool.npz`。
- [x] CWRU 下游 smoke：real_only、noise_aug、rule custom_pool 已用 2 seeds × n_real={5,10} 跑通 `breeze/results/phaseB_cwru_downstream_smoke.csv`；LLM pool 仍需 API 配置与预算估算后才能生成。
- [x] CWRU LLM 小批量接受率验证：已使用 30/30 API requests。`smoke_api_v1` 用 20 次请求覆盖 healthy/IR/B/OR，IR/B/OR 均 5/5 accepted，healthy 0/5 accepted；`smoke_api_v2_healthy_prompt` 用 10 次请求复测 healthy，10/10 因 900-token 约束下 JSON 截断而 parse failed。输出见 `breeze/results/phaseB_cwru_llm_smoke_combined_gate_report.md`。
- [x] CWRU 小批量验收：FAILED。不能进入 XJTU/IMS、CWRU full pool 或 downstream claim。失败主因是 healthy 背景谱形；v1 broad band weights 无法过 PSD W1，v2 20-30 components prompt 又超出 max_tokens≤900 的有效 JSON 输出长度。
- [x] CWRU compact healthy prompt v3：用户批准额外 5-10 API requests 后，运行新目录/tag `smoke_api_v3_healthy_compact`；使用 10 次请求，healthy 10/10 accepted slots、42 accepted items。CWRU Phase-B API 累计 40 次；key 未写入项目文件。
- [x] CWRU LLM smoke combined pool：合并 v3 healthy 与 v1 IR/B/OR，输出 `breeze/runs/phaseB_cwru_within_load0_llm_smoke_combined_v3/pool.npz`，by-class counts 为 healthy=42、IR=23、B=23、OR=25；原始 v1/v3 目录未修改。
- [x] CWRU downstream smoke：real_only/noise_aug/LLM custom_pool 已跑 2 seeds × n_real={5,10}；另测 LLM n_syn={5,10,20}。汇总见 `breeze/results/phaseB_cwru_llm_smoke_v3_report.md` 和 `phaseB_cwru_llm_smoke_v3_downstream_summary.csv`。
- [x] CWRU 放量决策 v3：NO-GO。Admission 已通过，但 v3 LLM downstream smoke 不稳定，且同 n_syn=10 时不稳定低于 rule smoke；不能进入 150/class CWRU full pool 或 XJTU/IMS。
- [x] CWRU 下游失败诊断：已检查 LLM vs rule 的 per-class F1、real/syn PSD/envelope 距离、nearest-neighbor 距离和 classifier confusion；v3 fault 样本主要问题是 IR/B/OR envelope prominence 偏低、NN 距离偏大，且 B/IR RMS 偏离真实中位数。诊断见 `breeze/results/phaseB_cwru_pool_quality_smoke.csv`。
- [x] CWRU fault-quality prompt v4：用诊断结果反馈 prompt，不改 verifier、不后处理样本；额外 15 API requests，IR/B/OR 均 5/5 accepted，合并 v3 healthy 后输出 `breeze/runs/phaseB_cwru_within_load0_llm_smoke_combined_v4/pool.npz`。
- [x] CWRU v4 downstream smoke：n_syn≈20、5 seeds、n_real={5,10} 下，LLM v4 在 mean Acc/Macro-F1 上均高于 rule_nsyn20 与 noise_nsyn20；paired deltas 见 `breeze/results/phaseB_cwru_v4_5seed_paired_deltas.csv`，报告见 `breeze/results/phaseB_cwru_v4_smoke_decision_report.md`。
- [x] CWRU 放量前本地验证 v4：已扩到 10 seeds × n_real={5,10,25}，n_syn≈20；v4 在 n=5/10 明显优于 rule/noise，但 n=25 对 noise 的 Accuracy 仍边界不足。报告见 `breeze/results/phaseB_cwru_v4_10seed_local_verification.md`。
- [x] CWRU balanced pilot v5：本地 rule pilot 生成 0 API；LLM 额外 15 API supplement，累计 API=70；合并池 LLM counts healthy=42、IR=50、B=41、OR=50。n_syn=38/class balanced pilot 通过 n=5/10，但 n=25 对 noise 不显著。
- [x] CWRU synthetic budget ablation：n_syn=20/class 在 n=25 更稳；n=25 追加到 20 seeds 后，LLM 对 rule/noise 的 Acc/Macro-F1 均通过 Holm smoke gate。报告见 `breeze/results/phaseB_cwru_v5_budget_ablation_report.md` 与 `phaseB_cwru_v5_nsyn20_mixedseed_check.md`。
- [x] CWRU full-pool 预算执行：已复用 v3/v4/v5 pilot slots，并补 140 slots/class；实际新增 API requests=567（含重试），累计 637/2000。full supplement accepted slots：healthy=139/140、IR/B/OR=140/140；full combined accepted items：healthy=603、IR=750、B=631、OR=750。
- [x] CWRU full-pool 质量诊断：`breeze/results/phaseB_cwru_pool_quality_full_v1.md` 显示 full pool 全部样本通过 verifier，fault envelope prominence 与 rule smoke 同量级或更高，NN 距离未异常放大。
- [x] CWRU full v1 within_load0 smoke：按预注册 schedule（n=5/10 用 n_syn=38/class，n=25 用 n_syn=20/class）跑 CNN smoke；LLM full 对 rule/noise 的 Acc/Macro-F1 全部 Holm q<0.05。报告见 `breeze/results/phaseB_cwru_full_v1_smoke_report.md`。
- [x] CWRU within_load0 schedule 表补齐：已补跑 real_only，并汇总 LLM/rule/noise/real_only；`breeze/results/phaseB_cwru_within_load0_schedule_report.md` 显示 LLM full v1 在 registered schedule 下显著优于 real_only、noise_aug、rule。
- [x] CWRU cross-condition smoke：`train_load0_test_load1` 使用同一 CWRU full LLM pool 与 registered schedule 完成 20 seeds × n_real={5,10,25}；LLM 对 rule/noise_aug/real_only 的 Acc 与 Macro-F1 均为正向且 Holm q<0.05。报告见 `breeze/results/phaseB_cwru_cross_load1_schedule_report.md`。
- [x] CWRU LOLO smoke：已选择 `lolo_load1`（train loads 0/2/3，test load 1）。n=5/10 使用 20 seeds，n=25 因 20-seed 初查对 noise_aug 边界而扩到 40 seeds；最终 LLM 对 rule/noise_aug/real_only 的 Acc 与 Macro-F1 均为正向且 Holm q<0.05。报告见 `breeze/results/phaseB_cwru_lolo_load1_schedule_report.md`。
- [x] CWRU dataset gate report：汇总 M4 配置、train-only verifier、API/slot 消耗、full pool 构成、within/cross/LOLO downstream 统计，判定 CWRU smoke gate 通过但 claim 限定为 CNN few-shot 对 real_only/noise/rule。报告见 `breeze/results/phaseB_cwru_dataset_gate_report.md`。
- [ ] XJTU 重新审计：按最新指令恢复 XJTU-SY 队列，重新核验官方/作者可下载数据、许可证、轴承几何、采样率、工况、故障类型和 run-to-failure 标签边界；旧“跳过”报告只作为历史记录。
- [ ] XJTU M4/verifier/LLM smoke：若能建立透明监督或 run-to-failure 协议，先做 M4 运动学重配置、verifier 重校准和 ≤30 API 接受率验证；不能定义标签时停下报告 claim 边界。
- [ ] IMS 重新协议化：基于 NASA/IMS run-to-failure 原始文件重新定义可复现实验协议，明确是否只做退化阶段/附录验证；不能把末端失效描述扩张成逐窗口 fault 标签。
- [ ] IMS M4/verifier/LLM smoke：在协议成立后再做 M4 运动学重配置、verifier 重校准和 ≤30 API 接受率验证；协议不成立则停止 Phase-B 该数据集并报告。
- [ ] Phase B 全量开跑前更新训练次数、预计耗时、synthetic budget、断点文件路径和 API 预算；旧 `breeze/results/phaseB_execution_budget.md` 需按 CWRU → XJTU → IMS 新顺序改写后才能作为放量依据。

## 10. 硬性执行指令：从 admission framework 向可靠 LLM 故障信号生成重构（当前活动）

### 10.A 2026-07-05 强标准全量执行清单（当前执行顺序）

原则：每个子任务先做 smoke test，再全量；所有长任务必须断点续跑；所有数字必须能追溯到本地 CSV/JSON/NPZ/PDF；若结果未达到强 claim 标准，继续改实验/方法，不能把目标写成结果。

#### 10.A.1 任务清单与证据边界
- [x] 读取用户给定 11 部分改进标准，拆分为摘要、引言、相关工作、方法、数据集、实验设置、结果、物理真实性、消融、图表、讨论 11 类硬要求。
- [x] 读取 `awesome-ai-research-writing` 写作/逻辑/实验分析协议，确认不得编造数据、不得增强 unsupported claim。
- [x] 检查当前 `todos.md`、主稿、结果表和报告，确认现有稿件是 admission framing，且当前冻结结果不支持 SOTA/多数据集强 claim。
- [x] 建立新的细化执行清单并写入本文件，后续每完成一个阶段都回写状态。
- [x] 建立逐条强标准核对表：每条要求对应“数据/代码/CSV/图/论文段落/是否达标/BLOCKER”，见 `analysis/strong_standard_checklist_2026-07-05.md`。
- [x] 每轮实验后更新核对表，防止重复处理或把旧结论带入新稿。已在 CWRU 与 MFPT 核验后更新一次；后续每轮实验继续回写。

#### 10.A.2 本地数据与公开数据下载
- [x] 清点本地已有数据：PU 四个工况均有 processed `.npz`，私有机床有 processed `.npz`，外部 CWRU/MFPT/IMS/XJTU 等当前本地缺失。
- [x] 将用户补充的候选公开数据集列入核验队列：CWRU、PU、IMS、XJTU-SY、DIRG、JUST Dataset 1/2、HIT。核验原则：官方/作者托管优先，记录 URL、许可/引用要求、文件大小、格式、通道、工况和是否适合 few-shot fault classification。
- [x] 生成数据登记脚本 `breeze/scripts/dataset_registry.py`。
- [x] 生成 `analysis/dataset_registry_2026-07-05.csv` 与 `reports/dataset_registry_audit_2026-07-05.md`。
- [x] 核验 CWRU 官方下载入口、文件结构、采样率、通道、故障类型、载荷、转速、fault size、标签。
- [x] 下载 CWRU 最小可行子集到本项目数据目录，先选一个清晰的 12 kHz drive-end protocol 做 smoke。
- [x] 为 CWRU 写断点续跑下载清单、校验文件大小/数量、记录 source URL 和本地路径：`analysis/cwru_de12k_full_manifest_2026-07-05.csv`、`breeze/scripts/cwru_download.py`。
- [x] 为 CWRU 写预处理脚本：读取 `.mat`、选择通道、统一 window/stride、标签映射、condition registry、split registry：`breeze/scripts/cwru_preprocess.py`。
- [x] CWRU smoke：每类少量文件预处理，检查窗口形状、类别分布、无 train/test 泄漏。Smoke 输出 `proc/cwru_smoke_train.npz` / `proc/cwru_smoke_test.npz`。
- [x] CWRU 全量：within-condition、cross-condition、leave-one-condition-out split 生成并冻结。Full 输出 `proc/cwru_de12k_all.npz` 和 `proc/cwru_de12k_*_train/test.npz`。
- [x] 核验 MFPT 官方数据入口与许可：`https://www.mfpt.org/fault-data-sets/` 当前 301 到 ASNT/MFPT 介绍页，未发现 `.mat/.zip/.csv` 等公开下载端点；记录 blocker：`reports/mfpt_availability_audit_2026-07-05.md`。若用户提供可验证公开 URL，再重复“最小子集 smoke -> 全量预处理 -> split 冻结”。
- [x] IMS：NASA PCoE 官方页面已核验到 `4.+Bearings.zip`，大小约 1.08GB；已用 `curl -C -` 下载，zip 完整性通过。内层 `IMS.7z` 包含 `1st_test.rar`、`2nd_test.rar`、`3rd_test.rar` 和 readme。
- [x] IMS smoke：`bsdtar` 可读取 RAR；样本文件为 ASCII，20 kHz、20,480 点，Set 1 为 8 通道，Set 2/3 为 4 通道。已生成 `analysis/ims_bearing_set_manifest_2026-07-05.csv`、`analysis/ims_bearing_file_manifest_2026-07-05.csv`、`reports/ims_bearing_audit_2026-07-05.md`。
- [x] IMS 适配判断：这是 run-to-failure 数据，readme 只给实验末端失效描述，没有逐文件 fault-onset 标签；暂不作为 CWRU/PU 式监督多类 fault classification 主 claim，除非后续单独定义并披露 run-to-failure 协议。
- [x] XJTU-SY：已核验用户给定 GitHub 路径经 API 返回 404；搜索到 `WangBiaoXJTU/xjtu-sy-bearing-datasets`，README 说明其为 15 个轴承 run-to-failure prognostics 数据并给出多个网盘链接。用户已指示跳过此数据集，记录于 `reports/xjtu_sy_skip_audit_2026-07-05.md`；不纳入主实验或公开数据集计数。
- [x] DIRG Zenodo `3559553`：已通过 Zenodo API 核验 DOI `10.5281/zenodo.3559553`、许可 `cc-by-4.0`、文件清单和大小；下载说明 PDF 并确认 VariableSpeedAndLoad 适合监督诊断。
- [x] DIRG `VariableSpeedAndLoad.zip`：已从 Zenodo 官方 content URL 下载，md5 `e703421e4624b205c2f03efc9dad9f06` 与记录一致，zip 完整。
- [x] DIRG smoke：读取 3 个 `.mat`，确认每文件 `(512000, 6)`，fs=51200 Hz，生成 `proc/dirg_variable_smoke.npz`，形状 `(375, 6, 4096)`。
- [x] DIRG 全量预处理：119 个 `.mat`，7 类、17 speed/load conditions，4096 非重叠窗，输出 `proc/dirg_variable_all.npz`，形状 `(14875, 6, 4096)`；默认 held-out `300Hz/1400N` split 输出 train/test NPZ，无同工况泄漏。
- [x] 核验 JUST Mendeley Dataset 1/2：已记录版本/DOI/许可/文件清单/文件大小；Dataset 1 含 condition1--6，Dataset 2 含 condition7--9，页面描述为振动 + 声发射 CSV，标签 N/I/O/B1。当前 `condition1.zip` 仅部分下载，已用断点续传恢复；完整 raw/sha256/extract/smoke 仍待下载完成。
- [x] 核验 HIT GitHub/Google Drive：已记录作者仓库、README、论文 DOI、GitHub 文件清单；GitHub Channel-1 示例已下载并预处理为 train/test NPZ。限制：README 未定义标签 0/1/2 的物理含义，full dataset 在 Google Drive，暂不支撑物理故障生成 claim。
- [x] 所有新增公开数据集写入 dataset registry，报告采样率、通道、故障类型、负载、转速、切窗、split。当前已回写 CWRU、IMS、DIRG、HIT、JUST 元数据状态与 XJTU-SY 跳过状态；JUST raw smoke 待完整下载后再补。

#### 10.A.3 LLM/recipe 责任边界与核心对照
- [x] 清点已有 LLM 模型、prompt、temperature、API 日志：本地代码有 `mimo-v2.5`、prompt schema、temperature=1.0、timeout=300；top-p/API seed/完整响应日志不完整。
- [x] 从 `renderer.py` 提取 renderer 方程与参数责任边界。
- [x] 写入 `breeze/scripts/recipe_ablation.py`，支持 random recipe、rule recipe、同一 renderer、同一 v2 verifier、同一 slot budget、断点续跑。
- [x] recipe 对照 smoke：random 15 slots 全拒绝，rule 15 slots 接受 1 slot/保留 5 windows，脚本链路跑通。
- [x] recipe 对照全量完成：random/rule 各 450 slots，输出 pool、summary、fail reasons。
- [ ] 将 LLM v2、random v2、rule v2 合并为同一 summary 表，报告接受率、失败率、失败原因、LLM calls、kept windows。
- [ ] 当前全量结果为 LLM v2 286/450 slots、rule 167/450 slots、random 0/450 slots；支持 LLM > rule > broad-random，不支持用户目标中的 LLM > random > rule。需要继续迭代更合理的 empirical-random baseline 后再判断。
- [ ] 如果 random/rule pool 样本不足，先基于接受率写证据，不强跑下游；若样本充足，再跑同合成预算下游对照。
- [ ] 对 LLM vs random/rule 做统计：接受率差异、下游差异、物理指标差异；只有显著优于 random/rule 才允许写 LLM 独立贡献。
- [ ] 若现有 LLM API key 可用，评估是否重跑完整 v2 closed-loop K=0/1/2/3；若不可用，继续明确 v2 是 offline rescreening，不能写成新闭环。

#### 10.A.4 物理真实性与非复制证据
- [ ] 写扩展物理指标脚本，输入 real train/test、各 synthetic pool，输出 class-wise CSV 和报告。
- [ ] 实现 BPFO/BPFI/BSF/FTF 特征频率误差统计，报告 ±3% 和 ±5% 内比例。
- [ ] 实现 envelope peak prominence、SNR、harmonic consistency、IR sideband consistency。
- [ ] 实现 PSD-Wasserstein、band energy distance、spectral centroid、band centroid drift。
- [ ] 实现 real-vs-synthetic discriminator AUROC，先用固定 feature classifier smoke，再全量多 seed。
- [ ] 实现 nearest-neighbor distance 到 train real，报告 synthetic-to-real / real-to-real 比例，证明不是复制训练样本。
- [ ] 检查 PU vibration-current coherence 可行性；若两相电流不支持稳定 hard gate，记录为 certificate score 而非 hard claim。
- [ ] 将指标接入图表：真实/合成 waveform + FFT + envelope spectrum，FID/KID/MMD/PSD-W1 总览，nearest-neighbor 和 discriminator 图。

#### 10.A.5 强 baseline、分类器和统计
- [ ] 清点已有 baselines：real-only、noise、VAE、GAN、open-loop basic、open-loop physics、stats-only、envelope-only、BREEZE K0-K3、v2。
- [ ] 补齐传统增强：jitter、scaling、crop、mixup，确保同 synthetic budget。
- [ ] 评估 diffusion baseline：先做资源/时间 smoke；若不能严谨训练，写 BLOCKER，不用弱 diffusion 充数。
- [ ] 增加分类器：CNN、ResNet1D、TCN、Transformer、SVM、RF。先在 PU 主工况 10-shot smoke。
- [ ] few-shot 扩展为 10/25/50/100/300/500；先每个 n_real 2 seeds smoke，再 20 seeds 全量。
- [ ] severe imbalance normal:fault=8:2：定义采样协议，先 smoke，再全量。
- [ ] 统一 synthetic budget、train/test split、随机种子；所有结果写入 append-only CSV，支持断点续跑。
- [ ] 对每个数据集/shot/分类器报告 best baseline vs BREEZE 的差值，并做 BH 多重比较校正。
- [ ] 如果 BREEZE 不能超过最强 baseline，继续方法迭代；仍不能超过则收回 SOTA/可靠生成强 claim。

#### 10.A.6 新增公开数据集上的生成/验证/下游
- [ ] CWRU verifier schema：按 CWRU 元数据定义 characteristic frequencies 或保守的 envelope/PSD/stat gates；不复用 PU 电流 gate。
- [ ] CWRU random/rule/LLM recipe schema 适配：根据可用通道和 fault metadata 设计 renderer 或明确只能做 verifier/augmentation subset。
- [ ] CWRU closed-loop 或 offline recipe pool smoke：每类少量 slots，检查接受率与失败原因。
- [ ] CWRU 全量 pool：断点续跑、保存 JSON/NPY/manifest/summary。
- [ ] CWRU 下游：within-condition、cross-condition、leave-one-condition-out、multi-classifier、multi-shot。
- [ ] 若 MFPT/IMS/XJTU 纳入，重复 CWRU 的 schema -> smoke -> full -> downstream 流程。

#### 10.A.7 论文与图表重构
- [ ] Related Work 增加 taxonomy 表：LLM-description generation、physics-informed GAN、physics-informed diffusion、verifier-guided admission。
- [ ] 补齐 BearGen、TimeGAN、SigCWGAN、TTS-GAN、TTS-CGAN、DDPM、CFG-DDPM、physics-informed diffusion 比较；只引用已核验来源。
- [ ] 方法部分公开模型、prompt、temperature、top-p/seed 缺失状态、recipe schema、renderer 方程、K=0/1/2/3 接受率/失败率/LLM calls。
- [ ] 数据集部分改为公开数据集主实验，私有机床只做附加 schema audit 或移出主 claim。
- [ ] 实验设置写清多分类器、多 shot、severe imbalance、20 seeds、BH correction、统一 budget。
- [ ] 结果部分只写真实达到的 strongest-baseline gains 和显著性；没有达到则保留 admission framing。
- [ ] 摘要只有在结果满足“多公开数据集最高/并列最高、LLM>random>rule、强 baseline 显著提升”后才替换正式摘要。
- [ ] 引言和 Discussion 根据最终证据选择强生成 claim 或收缩 claim，避免 circular validation 未实验化解时硬写。
- [ ] 所有新增图统一期刊风格，渲染 PDF/PNG 检查无标签拥挤。

#### 10.A.8 最终验证
- [ ] 运行所有新增 smoke 和全量脚本的 sanity checker：行数、seed 覆盖、缺失任务、类别分布、文件存在性。
- [ ] 重新生成主表、补充材料、review matrix、submission checklist。
- [ ] 编译 `main.pdf` 与 `main_cas.pdf`，检查 undefined refs/cites、overfull、图表渲染。
- [ ] 对照用户 11 部分改进标准逐条打勾；未达标项写明真实原因和下一步，不报告成功。

### 10.0 前置 skill 安装与可用性核验
- [x] 检查本机已安装 skills：未发现 `nature`、`女娲/nuwa`、`awesome-ai-research-writing`。
- [x] 读取 `skill-installer` 官方说明，确认应通过 openai/skills curated 或 experimental 安装。
- [x] 尝试列出 curated skill 清单：GitHub API 返回 HTTP 403，未成功。
- [x] 尝试列出 experimental skill 清单：GitHub API 返回 HTTP 403，未成功。
- [x] 尝试用 git 只读浅克隆 openai/skills 仓库确认路径：权限请求被拒绝，未成功。
- [x] 用户提供三个 GitHub 仓库后，已安装 `nature-figure` 到 `/Users/jianyang/.codex/skills/nature-figure`。
- [x] 已安装 `huashu-nuwa` 到 `/Users/jianyang/.codex/skills/huashu-nuwa`。
- [x] `Leey21/awesome-ai-research-writing` 仓库不是标准 Codex skill 结构，已按 `skill-creator` 规范包装为本地 skill 并安装到 `/Users/jianyang/.codex/skills/awesome-ai-research-writing`，原 README 保存在 `references/prompt-library.md`。
- [x] 已读取并应用 `nature-figure` 的 manifest、core contract、stance、Python backend、API/design/QA 参考。
- [x] 已读取并应用 `huashu-nuwa` 的主流程、extraction framework、fidelity scorecard；本任务按主题框架抽取，不创建名人角色 skill。
- [x] 已读取并应用 `awesome-ai-research-writing` 的主流程和写作/逻辑/实验分析/图题相关 prompt 库。
- [x] 说明：新安装 skill 若要自动出现在 Codex skill 列表中，通常需要重启 Codex；当前窗口通过直接读取已安装文件继续执行。

### 10.1 文献调研与图式抽取
- [x] 检索并核验用户指定论文：BearGen / AEI 2026；已用用户提供 PDF 与 Crossref DOI `10.1016/j.aei.2026.104400` 核验。
- [x] 检索并核验用户指定论文：物理约束 GAN / Measurement Science and Technology 2025；已核验 DOI `10.1088/1361-6501/ae1a04`。
- [x] 检索并核验用户指定论文：HAWAN-PIR 2025；当前无可验证 DOI/出版页，已在审计中标为未核验，不编造。
- [x] 检索并核验 Physics-Informed Diffusion 相关论文；已核验 JVC 2026 `10.1177/10775463261455715`，并补充 MSSP 2025 diffusion `10.1016/j.ymssp.2025.113170`。
- [x] 补充 fault diagnosis synthetic data、physics-informed generation、LLM time-series generation 相关论文；已补 BearGen 引文链、MST 2025、MSSP 2022 GAN、MSSP 2025 diffusion、JVC 2026 physics-informed diffusion。
- [x] 对每篇文献记录：方法、数据集、工况、故障类型、baseline、指标、图表类型、可借鉴点。
- [x] 单独整理文献图式常用格式：workflow、mechanism、waveform+spectrum/envelope spectrum、feature distribution、ablation bar/line、cross-condition table、failure case、t-SNE/UMAP 辅助图。
- [x] 输出 `analysis/literature_figure_style_review_2026-07-04.md`，所有条目附来源链接或本地 PDF 路径。

### 10.2 当前稿件与图表差距诊断
- [x] 枚举当前所有图：framework、waveforms、boxplots、acceptance、downstream、CAS 同步图。
- [x] 对照文献图式，判断每张图缺失的证据层：LLM/renderer/verifier 边界、闭环反馈、物理机制、失败案例、跨工况结果。
- [x] 写入 `analysis/figure_gap_audit_2026-07-04.md`，标记哪些可由现有结果重画，哪些必须新增实验后才能画。
- [x] 明确 t-SNE/UMAP 只能作为辅助，不进入核心 claim。

### 10.3 数据集与工况补强可行性
- [ ] 清点本地已有公开数据集：PU 已有工况、CWRU/MFPT/IMS/XJTU-SY 是否存在。
- [ ] 对候选公开数据集记录下载源、许可/可用性、采样率、通道、故障类别、转速/负载/故障程度。
- [ ] 先选择一个最小新增公开数据集做可行性验证，避免一次性下载/处理过多。
- [ ] 设计统一 dataset registry 与断点续跑预处理脚本，支持 within-condition、cross-condition、leave-one-condition-out。
- [ ] BLOCKER：新增数据集需要网络下载或本地数据路径；若无数据/下载权限，不得声称已完成多数据集实验。

### 10.4 LLM 生成流程硬证据补齐
- [ ] 清点当前工作区中已有 LLM 模型名、版本、prompt、temperature、top-p、seed、max tokens、API 日志。
- [ ] 若缺失，写入 blocker，不用模糊描述替代。
- [ ] 从 renderer 代码提取完整方程、参数边界、LLM recipe 与 renderer 责任边界。
- [ ] 设计并实现对照：random recipe + renderer、rule recipe + renderer、LLM recipe + renderer、open-loop LLM、LLM + verifier。
- [ ] BLOCKER：若没有 LLM API key 和完整 prompt/调用日志，不能重跑闭环 LLM 生成，也不能把 v2 offline rescreening 写成新闭环生成。

### 10.5 物理可靠性与分布真实性指标
- [ ] 实现/核对 BPFO/BPFI/BSF/FTF 误差统计，按类报告 ±3%-5% 内比例。
- [ ] 实现/核对 envelope peak prominence、SNR、harmonic consistency。
- [ ] 实现/核对 PSD-Wasserstein、band energy distance、spectral centroid。
- [ ] 实现/核对冲击间隔与转速一致性。
- [ ] 实现/核对 RMS、kurtosis、skewness、crest factor、peak value 分布。
- [ ] 实现/核对 vibration-current coherence；若 PU 当前通道不可稳定支持，明确写出原因。
- [ ] 实现/核对 MMD/FID-like、real-vs-synthetic discriminator AUROC、nearest-neighbor distance，每类单独报告。

### 10.6 强 baseline 与诊断稳定性
- [ ] 清点已有 baselines：real only、noise augmentation、VAE、GAN、open-loop LLM、physics-guided open-loop、BREEZE K0-K3、v2。
- [ ] 补齐缺失传统增强：jitter、scaling、crop、mixup。
- [ ] 评估 diffusion baseline 可行性；如果不能在本机 CPU/时间内严谨训练，标 blocker，不能用弱 diffusion 充数。
- [ ] 补齐 random recipe + verifier、rule recipe + verifier。
- [ ] 所有 baseline 使用相同 train/test split、相同合成预算、相同 seeds；先 smoke test，再全量断点续跑。
- [ ] 若 LLM + verifier 未超过强 baseline，必须把 claim 收回为 physics-verified admission framework。

### 10.7 图表重绘
- [x] 制定统一 figure style spec：字体、字号、线宽、颜色、panel label、caption 口径、导出格式。
- [x] 重画总体框架图：`breeze/paper/figs/framework.pdf`，替换为 gate-admitted 闭环流程。
- [x] 新增或重画 LLM recipe / renderer / verifier 责任边界图：`breeze/paper/figs/responsibility_boundary.pdf`。
- [x] 新增或重画闭环反馈流程图：`framework.pdf` + `acceptance_k.pdf`，分别展示闭环机制和反馈轮数代价。
- [x] 重画 waveform + envelope spectrum 对比图：`breeze/paper/figs/waveforms.pdf`。
- [x] 新增或重画物理指标分布图：`boxplots.pdf` + `metric_distances.pdf`。
- [x] 新增或重画 cross-condition 结果图/表：`cross_condition_heatmap.pdf` + Table 8，明确为 verifier audit。
- [x] 新增或重画 ablation 图：`acceptance_k.pdf`。
- [x] 新增或重画 failure case 图：`failure_case.pdf`，来源为 `runs/rescreen_v2_full/records/healthy_0013.json`。
- [x] 新增或重画 acceptance/failure reason breakdown 图：`failure_reasons.pdf`。
- [x] 每张图均用 PDF 和 PNG 渲染检查，确认无标签拥挤、遮挡、颜色不可读；主稿和 CAS 关键页已用 `pdftoppm` 渲染复核。

### 10.8 写作与 claim 一致性
- [x] 若硬实验未证明 LLM 本身不可替代，全文 claim 保持/改回 `physics-verified admission framework` / physical-gate admission framework。
- [x] 删除所有把 verifier 功劳写成 LLM 功劳的句子；新增责任边界图和正文说明 verifier pass 不是物理正确性证明。
- [x] 谨慎使用 `certified`，优先用 `physics-verified`、`train-calibrated admissible` 或 gate-admitted；旧报告中的高风险标题也已改写。
- [x] 摘要、贡献、方法、实验、结论逐段核对，确保 claim 与实验结果一致。
- [x] `awesome-ai-research-writing` skill 已安装并读取，已用于图注、claim 收缩和技术写作复核；不再是 blocker。
- [ ] 2026-07-05 摘要升级请求 blocker：用户要求写入“多公开数据集最高/并列最高、LLM recipe > random recipe > rule recipe、相对最强 baseline 显著提升”。当前冻结结果不支持，已写入 `reports/abstract_upgrade_blocker_2026-07-05.md`；完成新增实验前不能覆盖正式摘要。
- [x] 已先写好 SOTA 目标摘要模板，保存为 `breeze/paper/abstract_sota_template.tex`；关键数据均保留显式占位符，等待后续实验达到 SOTA 后填入。

### 10.9 最终核对
- [ ] 建立逐条需求核对表：每一点是否有代码、实验结果、图表、论文文字、统计检验、复现说明。
- [ ] 对缺项明确写 BLOCKER 或继续补实验；不交付半成品为“已完成”。
- [x] 更新 todos、snapshot、review matrix、submission checklist。
- [x] 编译 `main.pdf` 和 `main_cas.pdf`，检查日志和 PDF 渲染；主稿无实质 warning，CAS 仅剩作者占位页 overfull。

关键冻结结论：
- PU 主实验当前使用 `N09_M07_F10`，3 路通道为 `vibration_1`, `phase_current_1`, `phase_current_2`；X/Y/Z 是内部短名，不是 PU 三轴振动。
- 主 split 是每个轴承按 file_id 前 80% train、后 20% test；当前 train/test 窗口量为 3846 / 962，文件 id 无交叉。
- 自建机床数据为 4 通道 `X,Y,Z,Current`，窗口形状 `(4, 2048)`，不能直接复用 PU 的 1 振动 + 2 电流 verifier。
- 已在 `sci_llm/论文全文.md` 找到自建机床数据介绍：NI 采集卡四通道同步采样，采样率 4000 Hz，三类工况为正常加工、丝杠异常、底座不平衡；但本地材料仍未把文件前缀 `1/2/3` 明确映射到这三个工况，因此 BREEZE 稿件继续使用匿名标签 `MT-1/MT-2/MT-3`。
- 当前 `_file_c90` verifier 全量复算通过率：train 3603/3846 = 0.9368，test 880/962 = 0.9148；旧 `recal_file.log` 记录为 0.943/0.905，论文以当前冻结脚本复算为准，除非后续查明代码版本差异。
- 正式生成池：`pool_physics_file_k3` 450 slots，355 accepted，acceptance 0.7889；`pool_basic_file_k0` 450 slots，0 accepted。
- `downstream_file.csv` 完整覆盖 14 baselines × 3 n_real × 8 seeds = 336 行，missing=0。
- 完整主表中 BREEZE 相对 real-only 有稳定增益，但不是全基线最高，不能写成“最高准确率”。
- `downstream_file.csv` 只有 acc 和 macro-F1，没有 per-class F1；若论文要强调 IR 类，需要补跑或改训练输出。
- 十张核心图已重跑并导出 PDF/SVG/PNG/TIFF：`framework`、`responsibility_boundary`、`failure_reasons`、`failure_case`、`waveforms`、`boxplots`、`metric_distances`、`downstream_bars`、`acceptance_k`、`cross_condition_heatmap`；`paper/main.tex` 已编译为 21 页 `paper/main.pdf`，LaTeX 日志无 undefined refs、natbib warnings、overfull boxes。
- 用户已下载 Elsevier CAS 模板到 `breeze/els-cas-templates`；已生成 AEI/CAS 单栏版本 `paper/main_cas.tex` 并编译为 15 页 `paper/main_cas.pdf`。CAS 版本使用 `cas-sc`，原 `main.tex` 保留为稳定的 `elsarticle` 版本。当前 CAS 日志无 undefined refs/cites 和 duplicate anchor warnings，仅剩 `cas-sc` 前言内部 `\maketitle` 的 overfull 提示，PDF 可读且图表页已抽检。
- v2_full 离线重筛得到 pool `breeze/runs/rescreen_v2_full/pool_v2.npz`，757 个样本：healthy 192 / OR 304 / IR 261。
- v2_full 8-seed 自定义评估相对 real_only 显著提升：acc +14.30/+7.11/+5.75 pt @ n_real=10/25/50；但仍不是所有强基线最高。

原则：
- 不编造数据、不把计划项写成已完成结果。
- 阈值、参数、实验结论必须能追溯到代码、日志、CSV、JSON 或数据文件。
- 批量任务必须先小样本验证，再中样本，再全量；长任务必须断点续跑。
- 不做波形后修补、局部稳定化或不忠实的后处理补丁；BREEZE 的定位是 training-free 物理验证、约束反馈与证书化入池。
- 按奥卡姆剃刀原则处理审稿意见：优先收缩过强表述、补足可追溯定义和公平统计；只有现有证据不足且能严格复现时才新增实验，不用复杂包装掩盖结果边界。
- 每个阶段结束前必须复核产物和数字，结果不达标则记录问题并迭代，不提前声称成功。

## 9. 审稿意见大修任务（已完成到当前数据边界）

### 9.1 审稿意见拆解与证据映射
- [x] 将审稿意见拆成 claim 收缩、方法定义、实验补强、相关工作、排版可信度五类。
- [x] 建立 review response matrix：每条 criticism/question 对应稿件位置、需要的证据文件、可完成状态。
- [x] 标记不能通过现有数据支持的内容，准备删除或降级而不是硬写。
- [x] 建立本轮修改快照文件，记录每次实验、脚本、论文段落改动和验证结果。

### 9.2 术语与主张降级
- [x] 全文检索 `certified`、`guarantee`、`physical validity`、`current-signature consistency`、`portability` 等高风险词。
- [x] 将强保证类表述改为 `verified under train-calibrated physical gates` / `admitted by evidence gates` 等更准确表述。
- [x] 重写摘要，明确 BREEZE 是 train-calibrated rule-based rejection/admission framework，不训练生成器，不提供形式化物理正确性保证。
- [x] 重写贡献点，突出可审计 admission、训练集校准、few-shot real-only 增益和适用边界，删除“全面优于增强方法”的暗示。
- [x] 修正 MCSA claim：PU 中若可靠性不足则仅作为 certificate/evidence，不作为 hard gate；摘要和方法一致。
- [x] 将私有机床数据 claim 降级为 schema-level portability / smoke test，不声称同等 bearing-physics verification。

### 9.3 方法定义补强
- [x] 重写 Eq. 1，将单边约束改成混合 gate 集合：双边区间、上界、下界、健康样本故障峰抑制、类条件证据和多样性距离。
- [x] 明确 slot、recipe、window、accepted window 的定义和一对多关系。
- [x] 从代码和 JSON 中核对 “286 slots before diversity, 757 windows after diversity” 的来源；应改写为 450 slots -> 286 accepted slots -> 761 accepted items before diversity -> 757 kept windows。
- [x] 补充 deterministic renderer 方程和参数来源，只写代码可复现的内容。
- [x] 补充 LLM generator 已知信息：模型、prompt/response schema、temperature、rounds、seed 可控性；缺失项明确列为未提供/不可复现限制。
- [x] 公开性说明：thresholds、certificates、failure reports、pass/fail 明细的本地路径和可共享范围。

### 9.4 v2 与实验边界修正
- [x] 明确 v2 是 offline rescreening，不是完整 v2 closed-loop LLM 生成；标题、表注、结果和讨论全部统一。
- [x] 报告 v2 无真实新增 LLM 调用成本；成本应沿用原始 450 slots 的已记录调用，不能声称 v2 closed-loop 成本。
- [x] 统计 v2 fail-reason 分布、accepted slot/window 数、每类 synthetic cap 后样本数，输出 `reports/revision_statistics_2026-07-04.md` 和 `results/revision_v2_*.csv`。
- [x] 核查 Table 5 中 v2 592 样本是否来自 192+200+200 cap，并写入待改稿件表注。
- [x] 对 v2 vs envelope-only、open-loop physics-guided、GAN、noise augmentation 补完整 paired tests，并做 BH 多重检验校正。
- [x] 若 v2 不稳定优于强基线，结果段改为“相对 real-only 和 v1 的收益”，并诚实说明 strong augmentation 在部分 setting 更强。
- [x] 复核 calibration sensitivity，避免 p=0.0547 被写成显著或边界显著。

### 9.5 追加实验可行性检查
- [x] 检查现有 PU 预处理数据是否包含跨工况、跨转速/载荷/故障尺寸可用 split。
- [x] 先做少样本 smoke test：跨工况 real-only / selected baseline / BREEZE admission 是否能在当前数据与时间内可复现。
- [x] 若跨工况实验可行，写断点续跑脚本，先小样本再全量，输出独立 CSV 和报告。
- [x] 若跨工况闭环生成需要 API key 或缺少原始 LLM prompt，则不编造；将其列为 future work 或 revised limitation。
- [x] 检查是否能复用 compact CNN 之外的轻量模型作为下游稳健性实验；当前稿件按奥卡姆剃刀原则没有新增未充分跑完的下游模型，只把 compact CNN 限制写入讨论。

### 9.6 相关工作系统补强
- [x] 联网/本地查证 TimeGAN、C-RNN-GAN/RCGAN、time-series diffusion、fault diagnosis augmentation、physics-informed generative models、LLM/time-series synthesis、rejection sampling/verifier-guided generation 等文献。
- [x] 只引用可核对来源，不凭记忆编造 DOI、页码或年份。
- [x] 新增 related work 小节或段落：time-series generative augmentation、physics-informed fault synthesis、LLM-based signal synthesis、verifier/rejection/admission control。
- [x] 在 related work 中清楚区分 BREEZE 与训练 generator 的方法、与普通 data augmentation、与 prompt-only LLM synthesis 的差别。

### 9.7 图表与排版修正
- [x] 修复 Figure 4 标签拥挤问题：检查当前 `figures.py`，调整布局、字体、legend 或拆分图。
- [x] 重新生成所有受影响 figures，并用 `pdfinfo` 与 PNG 渲染检查。
- [x] 将 Author One、Author Two、previous work 2026、MechaForge 占位标记集中列入 author-input，不在正式 PDF 中留下未记录的占位；真实作者信息仍需用户提供。
- [x] 同步修改 `main.tex` 与 `main_cas.tex`，保证审稿版和 CAS 版内容一致。
- [x] 重新编译两个 PDF，检查 undefined refs/cites、overfull、natbib warnings。

### 9.8 大修后复核与交付
- [x] 生成 revised snapshot：论文改动摘要、实验新增/未新增原因、所有数字来源、剩余作者输入项。
- [x] 更新 `submission_checklist.md`，列明审稿意见已处理项和仍需作者确认项。
- [x] 生成面向审稿人的 response draft，逐条回答 10 个 Questions for Authors。
- [x] 终检：数字、术语、表注、图注、结论、limitations 相互一致。
- [x] 报告最终产物路径、未能完成原因和下一步需要用户提供的信息。

## 0. 冻结前现场确认

- [x] 确认用户指定环境路径：`breeze/.venv-breeze`。
- [x] 确认用户指定数据范围：`breeze_full-2`。
- [x] 读取 `BREEZE_final_plan.md`，提取论文主线、实验块和验收标准。
- [x] 读取 `breeze/HANDOVER.md`，识别已完成、未完成和高风险项。
- [x] 核对 `HANDOVER.md` 中“已完成”数字能否由本地文件复现；c90 pass rate 与旧日志有轻微差异，已记录。
- [x] 将旧根目录 `todos.md` 和 `breeze/todos.md` 改为指向当前主清单，避免旧任务误导。

## 1. 任务 1：冻结当前实验快照

### 1.1 文件与目录清点
- [x] 枚举 `breeze_full-2` 一级目录，记录源码、数据、结果、论文草稿位置。
- [x] 统计 `breeze/src` 源码文件与关键职责。
- [x] 统计 `breeze/runs` 中验证器、生成池、日志、旧池和废弃池。
- [x] 统计 `breeze/results` 中所有 CSV 结果表。
- [x] 统计 `breeze/paper` 中 LaTeX、图表和编译产物。
- [x] 标注 `pool_physics_k3_v1` 为旧架构池，当前主论文不混用。

### 1.2 环境冻结
- [x] 用指定 venv 记录 Python 版本。
- [x] 用指定 venv 记录核心依赖版本：numpy、scipy、pandas、scikit-learn、torch、matplotlib。
- [x] 检查 `requirements.txt` 与实际环境包名一致。
- [x] 记录 CPU/GPU 可用性：CUDA=False，MPS=False。

### 1.3 PU / Paderborn 数据冻结
- [x] 从 `config.py` 确认采样率、窗口长度、步长、轴承几何参数和工况。
- [x] 从 `data.py` 确认当前通道选择：`vibration_1`, `phase_current_1`, `phase_current_2`。
- [x] 统计 `proc/*.npz` 中 PU 文件数量、窗口形状、类别、轴承、工况。
- [x] 核对主工况 `N09_M07_F10` 的轴承列表与 `HANDOVER.md` 一致。
- [x] 统计主文件划分 `load_file_split` 的 train/test 样本量、类别分布、轴承分布。
- [x] 检查 train/test 文件 id 无交叉。
- [x] 明确论文只能说“本项目保留 3 路通道”，不能说 PU 原始数据只有 3 路。

### 1.4 实验室自建机床数据冻结
- [x] 从 `data_mt.py` 确认 CSV 表头和通道语义：X/Y/Z/Current。
- [x] 从 `sci_llm/论文全文.md` 补充确认自建机床数据采集介绍：NI 采集卡、四路同步模拟输入、三轴振动 + 电流、采样率 4000 Hz、源文档窗口 4096 点且 50% 重叠、工况包含正常加工/丝杠异常/底座不平衡。
- [x] 标注仍未确认的信息：文件前缀 `1/2/3` 到三种物理工况的精确映射。
- [x] 统计 `data_mt/*.csv` 文件、每类文件号和原始行数。
- [x] 统计 `proc/mt_train_*.npz` 与 `proc/mt_test_*.npz` 的样本量和形状。
- [x] 核对 train 文件号 1/2/4/5/10 与 test 文件号 7/8。
- [x] 标注私有数据不能直接复用 PU 的 3 通道 verifier，需要独立 schema。

### 1.5 验证器冻结
- [x] 读取 `runs/verifier_N09_M07_F10_file_c85.json`。
- [x] 读取 `runs/verifier_N09_M07_F10_file_c90.json`。
- [x] 读取 `runs/verifier_N09_M07_F10_file_c95.json`。
- [x] 全量复算 c85/c90/c95 的 train/test 通过率、fail gate 分布、共振带和阈值摘要。
- [x] 确认主协议使用 `_file_c90`，旧 bearing split verifier 不用于主表。
- [x] 核对 verifier gates：sanity、boundary、energy、envelope、MCSA、spectrum。
- [x] 记录高危 gate：硬频带、单一 SK 共振带、MCSA 可靠性、9 维 diversity。

### 1.6 生成池冻结
- [x] 统计 `runs/pool_physics_file_k3` 的 slot 数、JSON 数、NPY 数、接受数、轮次分布。
- [x] 统计 `runs/pool_basic_file_k0` 的 slot 数、JSON 数、NPY 数、接受数。
- [x] 统计 `runs/pool_breeze_k3.npz` 的样本形状、类别分布、来源。
- [x] 统计 `runs/breeze_ref_pool_v8.npz` 的样本形状、类别分布、来源。
- [x] 统计 VAE/GAN 基线池文件是否存在、样本量与类别分布。
- [x] 检查 `pools.py` 能组装 open-loop/stats/envelope/BREEZE 候选池。
- [x] 标注正式论文可用池、开发检查池和废弃旧池。

### 1.7 下游结果冻结
- [x] 读取 `results/downstream_file.csv`，统计行数、baselines、n_real、seeds、缺失组合。
- [x] 计算主表均值/标准差：accuracy、macro-F1；确认 per-class F1 当前不可用。
- [x] 识别 BREEZE 系列与强基线的真实排序，禁止把 BREEZE 写成全表最高。
- [x] 读取并核对 LLM 池下游检查日志和 v8 参考池日志。
- [x] 读取 `results/acceptance.csv`，核对 K=0..3 接受率和调用成本。
- [x] 读取 `results/pool_metrics.csv`，核对物理指标与多样性指标。
- [x] 读取 `results/significance.csv`，核对显著性检验设置与可用结论。

### 1.8 图表和论文草稿冻结
- [x] 确认 `paper/main.tex` 章节骨架和 TODO 状态。
- [x] 用 `figures.py` 重跑四张数据图：waveforms、boxplots、acceptance、downstream。
- [x] 用 `fig_framework.py` 重跑 framework 图。
- [x] 用 `pdfinfo` 确认 5 个 PDF 图和 `main.pdf` 可读取。
- [x] 列出当前可直接写入论文的表格与图。
- [x] 列出必须暂缓写入论文的缺失结果。

### 1.9 冻结报告产物
- [x] 创建 `reports/experiment_snapshot_2026-07-04.md`。
- [x] 创建 `reports/snapshot_raw_2026-07-04.json`。
- [x] 报告包含环境、数据集、通道、split、verifier、生成池、结果、图表、论文状态。
- [x] 报告中所有核心数字给出来源文件或由脚本全量复算。
- [x] 报告明确“已完成 / 未完成 / 高风险 / 禁止写法”。
- [x] 更新本 `todos.md` 到当前状态。

## 2. BREEZE-v2 高危 gate 改进准备

- [x] 阅读 `verifier/features.py` 与 `verifier/verifier.py` 的实现细节，整理当前 M1-M5 gate 公式。
- [x] 将当前 c90 fail gate 分布转成 v2 优先级：spectrum 与统计边界是主要风险。
- [x] 设计并实现 v2 soft spectrum：重叠三角滤波器组，替代硬边界频带。
- [x] 设计并实现 v2 PSD W1：Welch PSD CDF Wasserstein 距离。
- [x] 放弃单独多尺度硬频带作为默认 hard gate，避免重新引入硬切分；保留 soft spectrum + W1。
- [x] 设计并实现 v2 resonance：robust train-supported top-3 resonance bands，融合 envelope evidence 与 SK evidence。
- [x] 设计并实现 v2 MCSA：两相 vector-current，先做 train fault-vs-healthy 可靠性校准；不可分时仅 certificate。
- [x] 设计并实现 v2 diversity：扩展物理 embedding + class-wise real-real NN 阈值。
- [x] 设计并实现 v2 stats_union：legacy quantile 与 robust axis ellipsoid 的训练集支持域并集。
- [x] 为每个候选写明参数依据、训练集校准方式、不接触 test 的边界，见 `breeze/src/verifier/v2.py`。
- [x] 写断点续跑输出规范：每个 v2 配置单独 JSON/CSV/NPZ，已有结果跳过，见 `breeze/src/rescreen_v2.py`。

## 3. BREEZE-v2 离线重筛实验

- [x] 从现有 `pool_physics_file_k3` 抽取每类 10 slots 小样本，输出 `breeze/runs/rescreen_v2_s10`。
- [x] 对 v2 候选逐一离线重筛，输出 pass/reject 原因 JSON/CSV。
- [x] 审查小样本报告；发现单一 Mahalanobis stats 过严，改为 train-supported stats_union。
- [x] 扩展到每类 50 slots，输出 `breeze/runs/rescreen_v2_s50`，pool 268 样本。
- [x] 用中样本池跑 downstream 2 seeds 快速趋势，确认相对 real-only 有增益。
- [x] 中样本趋势和物理指标合理后进入全量。
- [x] 全量重筛 450 slots，生成 `breeze/runs/rescreen_v2_full/pool_v2.npz` 和证书日志。
- [x] 全量 8 seeds 自定义下游验证完成，输出 `breeze/results/custom_pool_eval.csv`。
- [x] 与 v1、open_loop_phys、envelope_only、noise_aug 比较；当前 v2_full 优于 v1 BREEZE 与 real-only，但不全局超过所有强基线。

## 4. 下游结果补强

- [x] 新增 `breeze/src/eval_custom_pool.py`，输出 per-class F1 和 confusion matrix。
- [x] 对 real_only 与 breeze_v2_full 做 8 seeds × 3 n_real 输出格式验证。
- [x] 确认输出写入独立 `custom_pool_eval.csv`，不破坏已有 `downstream_file.csv`。
- [x] 将 `breeze_v2_full` 以正式 baseline 方式并入主表，或写清它属于 v2 追加实验；当前已纳入 `analysis/main_tables.md` 和 `paper/main.tex`，并明确不覆盖原始 Block 4 表。
- [x] 批量补跑 14 baselines × 3 n_real × 8 seeds 的 per-class 结果，或至少补齐论文主对比所需设置；当前补齐了 `real_only` vs `breeze_v2_full` per-class F1，主文没有声称所有 baseline 的 per-class 结果。
- [x] 重新计算 real_only vs breeze_v2_full 的 IR 类 F1、macro-F1、accuracy、Wilcoxon。

## 5. 自建机床跨数据集实验

- [x] 明确私有机床数据的已知/未知边界：本地文档说明三种工况为正常加工、丝杠异常、底座不平衡；但文件前缀 `1/2/3` 的物理映射未确认，因此论文表格仍只写匿名 `MT-1/MT-2/MT-3`。
- [x] 新增机床原始 CSV 加载与 file_id 保留逻辑，确保 train 文件 1/2/4/5/10 与 test 文件 7/8 可追溯，见 `breeze/src/mt_verifier.py`。
- [x] 实现或配置机床 4 通道 schema：三轴振动 `X/Y/Z` + 单电流 `Current`。
- [x] 实现训练集校准的通用统计 gate：每通道时域统计、跨通道能量比例、相关结构、robust ellipsoid。
- [x] 实现训练集校准的通用频域 gate：normalized Welch PSD、overlapping soft-band fractions、PSD-CDF W1。
- [x] 只用 train split 校准通用统计 gate、频域 gate、多样性 gate。
- [x] 不使用 PU 轴承运动学 gate，除非用户提供机床轴承几何和转速。
- [x] 先用每类少量窗口做 smoke test，检查 report schema、pass/fail reason 和运行时间；soft-spectrum 高维硬判定过严，已改为 coordinate/ellipsoid 并集。
- [x] 全量验证真实 train/test 的通过率与 fail reason 是否合理；train 0.938-0.959，test MT-1/MT-3 有明确 file-level shift。
- [x] 输出 `mt_verifier` 校准 JSON、真实窗口 pass-rate CSV、fail-reason 汇总和跨数据集报告。
- [x] 若真实 train pass rate 明显偏离目标覆盖率，检查特征/阈值校准逻辑而不是改数字。
- [x] 设计机床 synthetic pool 来源与生成协议，不复用 PU 物理假设，见 `reports/machine_tool_synthetic_protocol.md`。
- [x] 跑机床 real-only 下游实验，独立脚本显式 `in_ch=4`，8 seeds × 3 n_real。
- [x] 只有在存在可审计机床 synthetic pool 时，才跑机床 BREEZE 增强下游实验；当前无审计池，因此没有运行也没有声称机床增强结果。
- [x] 输出跨数据集报告，说明即插即用的成立范围和限制：`reports/machine_tool_experiment_2026-07-04.md`。

## 6. 主结果统计与图表最终化

- [x] 为 v2_full 新增 `results/custom_pool_eval.csv` 与 `results/pool_metrics_v2.csv`。
- [x] 将 v2_full 合并进正式 `analysis/main_tables.md`。
- [x] 对 real_only vs breeze_v2_full 计算均值、标准差和 per-class F1。
- [x] 对 real_only vs breeze_v2_full 做配对 Wilcoxon，结果写入 v2 报告。
- [x] 对 v2_full 与强基线做配对显著性检验，输出 `results/significance_v2_vs_main.csv`。
- [x] 做 c85/c90/c95 覆盖率敏感性，避免阈值人为调参质疑，输出 `results/calibration_sensitivity.csv`。
- [x] 重跑所有图表并用 `pdfinfo` 验证；`figures.py` 已自动纳入 v2 pool / v2 downstream。
- [x] 渲染 `downstream_bars.pdf` 与 `boxplots.pdf` 为 PNG 后检查文字重叠和图例清晰度。

## 7. 论文写作

- [x] 确定目标模板：AEI/Elsevier；初稿使用 `elsarticle`，投稿版已迁移出独立 `cas-sc` 源文件。
- [x] 写 Introduction：数据稀缺、LLM 合成潜力、open-loop 物理可信缺口、BREEZE 贡献。
- [x] 写 Related Work：生成数据、LLM 时序生成、推理期闭环、轴承物理验证。
- [x] 写 Problem Formulation：固定生成器、可行域、证书化入池、training-free 边界。
- [x] 写 Method：M1-M4、反馈重采样、证书化入池、v2 verifier。
- [x] 写 Experimental Setup：PU、自建数据、split、baselines、指标、实现细节。
- [x] 写 Results：物理一致性、下游效用、消融、成本、机床私有数据。
- [x] 写 Discussion：不训练生成器的价值、失败模式、阈值敏感性、跨工况限制。
- [x] 写 Conclusion、Highlights、cover letter、supplementary outline。
- [x] 每个数字都加注来源 CSV/JSON，不留无法追溯的结果；主索引见 `analysis/main_tables.md`。

## 8. 终审与投稿准备

- [x] 数字逐项核对：论文表格 vs CSV vs 日志，来源见 `analysis/main_tables.md`。
- [x] 术语核对：PU 的 X/Y/Z 短名不能误写成三轴振动；`main.tex` 已明确 X/Y/Z 是 retained-channel short names，不是 PU 三轴振动。
- [x] 查重与语言润色：已完成内部占位符/警告扫描和基本英文重写；正式查重仍需外部系统。
- [x] 准备 supplementary：已写 `breeze/paper/supplementary_material.md` outline；完整 JSON/CSV 已保留在 runs/results/reports。
- [x] 准备 cover letter 和 highlights：`breeze/paper/cover_letter.md`、`breeze/paper/highlights.txt`。
- [x] 按目标期刊最新要求检查格式、图分辨率、参考文献格式；见 `breeze/paper/submission_checklist.md`，仍需作者补齐真实作者、基金、利益冲突和 MechaForge 精确参考文献信息。
- [x] 检查用户下载的 `breeze/els-cas-templates`，确认包含 `cas-sc.cls`、`cas-dc.cls`、`cas-model2-names.bst`；已用本地模板生成并编译 `breeze/paper/main_cas.tex` / `breeze/paper/main_cas.pdf`。

## 9. 私有机床数据集正式实验前审计（2026-07-10）

- [x] 同步 `origin/main` 后开始本轮审计；`main` 与 `origin/main` 为同一提交 `2901557c812195e4368c69a9d0a02cc5ec3f2b56`。
- [x] 将项目 owner 确认的正式类别映射写入唯一代码源：`1 -> normal_machining`、`2 -> lead_screw_anomaly`、`3 -> base_imbalance`；报告中明确该映射不是 MechaForge PDF 文本来源，也不是波形推断。
- [x] 新增 zero-API 预审计脚本 `breeze/scripts/mt_private_v1_preflight.py`，按 inventory / split-audit / duplicate-audit / confound-audit / learnability / summarize 断点执行。
- [x] 新增测试 `breeze/tests/test_mt_private_preflight.py`；`breeze/.venv-breeze/bin/python -m pytest breeze/tests/test_mt_private_preflight.py -q` 通过 10/10。
- [x] 生成独立结果目录 `breeze/results/mt_private_v1_preflight_2026-07-10/`；扫描 21 个 CSV，4 通道 schema 全部通过，train/test 文件数 15/6，train/test 窗口数 1737/486。
- [x] 生成 split manifest、exact duplicate 与 nearest-neighbor 审计；exact train/test raw-file duplicates=0，exact train/test window duplicates=0。
- [x] 完成 train-only LOFO confound 审计；metadata_safe ExtraTrees mean Macro-F1=0.3222，window_position_only mean Macro-F1=0.2298，均低于 0.80 high-risk 阈值。
- [x] 完成 train-only LOFO learnability 审计；signal_feature_only full mean Macro-F1=0.7981、worst-fold Macro-F1=0.5372；SimpleCNN full mean Macro-F1=0.8200。
- [x] 最弱类记录：signal_feature_only full 的 mean F1 最低为 `lead_screw_anomaly` 0.6216；worst per-fold F1 也在 `lead_screw_anomaly` 上最低，需在后续 LLM smoke 中重点跟踪。
- [x] 单独运行 private-MT verifier 到 `breeze/runs/mt_private_v1_preflight_2026-07-10/` 与本轮 results summary；旧 `mt_verifier_c90.json`、旧 pass CSV 未覆盖。
- [x] `mt_private_preflight_decision.json` 状态为 `PASS`，`allowed_next_stage=llm_smoke`；本轮 API 新增 0，累计 API 仍为 1071。

## 10. Private-MT v2 LLM closed-loop smoke（2026-07-10）

- [x] 冻结 development split：每类 file IDs `1/2/4/5` 为 inner-train，file ID `10` 为 inner-val；加载器将 formal file IDs `7/8` 作为运行时硬错误，本轮 formal test 读取次数为 0。
- [x] 新增 `breeze/scripts/mt_private_v2_llm_smoke.py`：仅基于 inner-train 的四通道 exemplar、通用 IAAFT-style surrogate renderer、MachineToolVerifier、real-real diversity 与固定 ExtraTrees class-identity certificate 运行可断点续跑闭环；无 TPF、转频、丝杠阶次或虚构机床参数。
- [x] prepare-only 通过：verifier、prompt、schema 和 renderer 都仅使用 inner-train；prompt 不含 raw class ID、file ID、路径、inner-val 或 formal test 信息；API=0。
- [x] 在冻结 60 次串行 API ceiling 内完成 LLM 闭环：实际 requests=60，accepted slots=`normal_machining=5`、`lead_screw_anomaly=5`、`base_imbalance=5`；每类 slot acceptance=0.50，balanced `n_syn=5`，未扩展 API 预算。
- [x] feedback gate 通过：round 0/1/2/3 新接受数为 3/8/3/1，initial-failure feedback rescue rate=0.6316；全部 accepted 无 exact train/synthetic duplicate，均通过四个 verifier hard gates、diversity 与 class-identity。
- [x] 在 frozen inner-val 上完成 5 methods × `n_real={10,25,50}` × 10 seeds downstream smoke；LLM 对 real+noise 核心 cells=0/6、对 rule=2/6、对 random=1/6，故 downstream gate 失败。
- [blocked] `mt_private_v2_smoke_decision.json` 为 `BLOCKED`，`allowed_next_stage=failure_analysis_only`；不得写 formal preregistration、不得运行 formal test、不得以更改 gate 或扩大本轮 API 预算继续攻击。
- [x] 新增测试 `breeze/tests/test_mt_private_v2_llm_smoke.py`；覆盖 file 7/8 guard、frozen split、recipe bounds、renderer、verifier/admission、resume/API log、pool balancing、downstream subset fairness 和 decision schema。
- [x] API 用量：本阶段新增 60 次，累计从 1071 到 1131/3000；密钥未写入结果、日志或 Git。

## 11. PU LOCO v4 cross-condition recovery（started 2026-07-13; internal-development only）

### 11.0 Protocol lock and audit trail

- [x] Synchronize local `main` with `origin/main` before inspecting or changing this workstream.
- [x] Read the frozen PU LOCO v1/v2 failure analyses and the train-only v3 morphology-condition map before selecting any development change.
- [x] Confirm that all candidate selection uses only four internal pseudo-held-out conditions; the registered PU held-out test remains unread for development, selection, and hyperparameter changes.
- [x] Lock the API ledger at 1131/3000 and set this workstream's incremental API ceiling to 200; prioritize zero-API candidates.
- [x] Create a distinct result directory for every subexperiment and retain checkpointed CSV rows, commands, manifests, and decision reports.
- [ ] After each repository change, inspect the intended diff, commit only the scoped files, push `main` to `origin/main`, and verify the pushed commit is present remotely.

### 11.1 S3 — scale-invariant downstream representation (zero API)

- [x] Define per-window, per-channel RMS normalization exactly as `x[c, :] / sqrt(mean(x[c, :]**2))`; reject non-finite or zero-RMS windows rather than silently replacing values.
- [x] Add `--normalize {none,per-window-rms}` to `breeze/src/eval_npz_downstream.py`; apply it after every method has formed its full training set and independently to each evaluation window, so all baselines and custom pools receive the same representation.
- [x] Include normalization mode in result identity/checkpoint keys and output rows so differently normalized runs cannot be mixed or skipped erroneously.
- [x] Unit-test normalizer shape preservation, channel-wise unit RMS, invalid-window rejection, checkpoint separation by normalization mode, and an empty locked checkpoint.
- [x] Record the implementation contract and exact command schedule in `breeze/results/pu_loco_v4_s3_scale_invariant_2026-07-13/`.
- [x] Smoke-run all internal folds with `real_only` and `noise_aug` at `n_real={5,10,25}`, two seeds, `n_syn=20`, and identical epochs; verify row completeness and deterministic resume behavior.
- [x] Run the completed internal baseline comparison at ten seeds for `real_only` and `noise_aug` under both `none` and `per-window-rms`; summarize Acc and Macro-F1 by fold and shot count without a formal-test claim.
- [x] Decide, from the internal summary only, whether the scale-invariant representation belongs in subsequent candidate comparison; do not add order-domain resampling unless its angular-reference/data contract is established without inference. RMS did not consistently improve `noise_aug`; retain `none`. Processed NPZs lack an angular-reference contract, so order-domain resampling is not admissible.

### 11.2 S2 — condition-aware morphology candidates (zero API first)

- [x] Audit `morphology_idw` and `morphology_nearest` pool construction: source windows, v2 calibration data, target kinematics, and pseudo-held-out access boundary.
- [x] Replace point extrapolation for features marked `not_predictable` in the morphology map with the union of three source-condition support intervals, then deliberately sample multiple admissible resonance/band-weight variants within that envelope.
- [x] Preserve a train-only v2 admission gate for every candidate; rejected windows are discarded, never waveform-repaired.
- [x] Run a five-sample-per-class acceptance smoke and inspect certificates. Both candidates fail the first internal fold's balanced healthy pool gate; details are in `breeze/results/pu_loco_v4_s2_morphology_2026-07-13/s2_s1_acceptance_failure.md`.
- [ ] Generate/checkpoint each candidate pool separately for all four pseudo-held-out conditions only if its five/class smoke pool passes; not eligible after the first-fold failure.
- [ ] Evaluate `morphology_idw` and `morphology_nearest` against the selected S3 baseline using `n_real={5,10,25}` and ten internal seeds; not eligible because the balanced smoke-pool prerequisite failed.
- [ ] Check the selection rule mechanically: a candidate must meet or exceed `noise_aug` on both metrics in at least three of four internal folds for every shot-count cell before formal preregistration is possible; not reached.
- [ ] Only if both zero-API candidates fail, prepare an explicit condition-extrapolation LLM prompt from the three train-condition feature tables; cap calls at 50 and record the API ledger before any request. Awaiting a configured API credential; no request made.

### 11.3 S1 — BREEZE-H real-carrier plus synthetic-fault injection (only after S2 decision)

- [x] Specify healthy-carrier sampling strictly from source-condition healthy training windows and fault injection strictly from the target-condition kinematics; do not draw pseudo-held-out windows.
- [x] Reuse the renderer impulse train for fault channels and retain existing current-channel rendering; make carrier identity and recipe provenance auditable per generated item.
- [x] Generate healthy synthetic samples as healthy real carriers plus noise augmentation at the fixed `noise_aug` scale, then submit every candidate to the v2 gate without post-hoc repair.
- [x] Add small-batch, per-class five-sample acceptance checks and inspect failure reasons. BREEZE-H fails the healthy 5/class prerequisite even after an 800-attempt capacity diagnostic; see the S2/S1 failure record.
- [ ] Evaluate BREEZE-H against the selected S3 baseline and all eligible S2 candidates on internal pseudo-LOCO only; not eligible because its balanced smoke-pool prerequisite failed.

### 11.4 S5 — BREEZE-U union-pool ablation (zero API)

- [ ] Construct BREEZE-U by sampling equal per-class contributions from `noise_aug` and v2-admitted BREEZE synthetic samples without changing either source waveform after admission; awaiting a balanced admitted BREEZE pool.
- [ ] Preserve source labels and exact composition in pool metadata; use the same total `n_syn=20/class` and downstream settings as comparators.
- [ ] Run the internal comparison and include BREEZE-U in the same fold/metric decision table.

### 11.5 Decision, formal boundary, and honest closeout

- [ ] If exactly one candidate meets the internal gate, write `pu_loco_v4_preregistration.md` before any formal held-out execution: name the one candidate, frozen code hash, all parameters, 40 seeds, Wilcoxon direction, and complete Holm family.
- [ ] Execute the formal registered held-out experiment exactly once only after that preregistration; freeze all outputs and write an outcome report regardless of result.
- [ ] If no candidate meets the internal gate, do not run formal held-out evaluation; write a failure analysis with empirical failure modes and manuscript-safe language that scopes cross-condition PU LOCO to a stress test.
- [ ] Update the API ledger, result manifests, checksums, `todos.md` statuses, and reproducibility commands; do not commit raw data, environments, checkpoints, or unreviewed training runs.

## 12. PU LOCO v5 S4 extrapolation-regime verifier (started 2026-07-13; internal-development only)

### 12.0 Protocol, boundary, and frozen design

- [x] Synchronize local `main` with `origin/main` before inspecting the v5 workstream; baseline is `ccc96f5b61af9726faf4742b79a575b8c9c89b52`.
- [x] Read the v2 failure analysis, v3 morphology-condition map, v4 S3 decision, and v4 S2/S1 acceptance-failure record in their prescribed order.
- [x] Verify the LLM configuration without making a request: project client uses `DASHSCOPE_API_KEY`, project default endpoint, and `mimo-v2.5`; S4 through the first internal comparison are zero-API stages.
- [x] Create and freeze `breeze/results/pu_loco_v5_s4_extrapolation_verifier_2026-07-13/s4_design.md` before calibrating or evaluating S4.
- [x] Lock the S4 API increment at zero through sanity, S2/S1 pool construction, and internal downstream comparison; no credential is written to a file, result, or Git history.
- [ ] Keep formal PU LOCO held-out windows unread until exactly one candidate satisfies the frozen internal decision rule and a v5 preregistration has been committed.
- [ ] Keep every calibration statistic derived only from the three source-condition train-bearing windows plus operating-condition metadata; never use pseudo-held-out or formal windows to select a boundary, interval multiplier, or gate.
- [ ] After every repository change, inspect the scoped diff, commit it, push `main` to `origin/main`, and verify that remote `main` contains the commit.

### 12.1 S4 implementation and unit tests

- [x] Add `regime={in_domain,extrapolation}` to `BreezeVerifierV2`, retaining the in-domain default and historical calibration loading behavior unchanged.
- [x] Implement fixed condition-space IDW interpolation using only rpm/torque/radial-load metadata and source-condition profiles.
- [x] Implement the frozen predictable-feature interval rule: target predicted q05/q95 expanded by `k=2.0` times leave-one-source-out median-prediction MAE.
- [x] Treat weak and not-predictable spectral/background features as report-only in extrapolation certificates, with source empirical-union evidence recorded rather than converted into an uncalibrated hard boundary.
- [x] Keep shape/finite/nonconstant sanity, fault-envelope position, and separable vector-current sideband position/evidence constraints hard; record their strict source in each certificate.
- [x] Record `regime`, morphology target condition, kinematics condition, boundary source, predictions, intervals, LOO errors, and report-only observations in every extrapolation certificate.
- [x] Add tests for in-domain compatibility, source-only calibration guardrails, report-only non-rejection, strict kinematic rejection, wrong-class/white-noise/constant negative controls, and save/load round trip. `breeze/.venv-breeze/bin/python -m pytest breeze/tests/test_extrapolation_verifier.py breeze/tests/test_eval_npz_downstream.py -q` passes 12/12.

### 12.2 Step 1: real-window sanity and negative controls

- [x] Build one extrapolation verifier per internal target condition using only the other three source-condition train-bearing windows for both v1 and v1.1; target/formal windows remain unread.
- [x] Re-run the healthy-carrier audit with the v4 deterministic 100-per-source sampling schedule; v1.1 raw rates are 0.783--0.923 and frozen-noise rates are retained in every target certificate.
- [x] Run the cross-condition OR/IR audit with target morphology boundaries and the source waveform's observed kinematics; literal target-kinematics results are logged separately as strict mismatch controls.
- [x] Apply the predeclared healthy sanity criterion: v1.1 satisfies it in all four targets, but this necessary condition cannot override negative-control failure.
- [x] Run fixed negative controls for wrong-class fault labels, white-noise windows, and constant windows. v1 and v1.1 both fail the required zero-admission criterion; S4 remains closed.
- [x] Complete the zero-API v1 audit for all four targets. The batch was already in flight when the first target failed; all four failure checkpoints are retained, no pools were started, and every target admitted prohibited negatives (221, 311, 319, and 350 of 800 respectively). `N09_M07_F10` also fails healthy sanity at 87/300 (0.290), with every source below 0.40.
- [x] Write `s4_v1_failure.md` and freeze `s4_design_amendment_1.md` before any v1.1 calibration. The correction tightens class/rate discrimination and fixes target-frequency healthy calibration; it does not use pseudo-held-out or formal windows and does not relax a threshold to increase admission.
- [x] Re-run all four targets under v1.1 in independent `v1_1/` run/result directories. Healthy raw rates now pass (0.783--0.923), but prohibited negatives still admit 103--231 of 800 per target; no pool construction is eligible.
- [x] Run a source-only rate/harmonic/modulation separability diagnostic. Neither OR nor IR has a feature whose true-class q10 exceeds both wrong-class and white-noise q90; no v1.2 gate is admissible.

### 12.3 Step 2: zero-API S2/S1 pool reopening

- [ ] Thread `--regime extrapolation` and target/source condition labels through morphology-IDW and morphology-nearest construction without modifying source recipe templates or rejected waveforms; prohibited because no valid S4 regime passed Step 1.
- [ ] Thread the same verifier mode through BREEZE-H while retaining healthy carriers strictly from source train windows and target-kinematic fault injection; prohibited because no valid S4 regime passed Step 1.
- [ ] For every candidate and all four internal targets, run a checkpointed five-per-class smoke pool and retain per-item certificates/manifests; prohibited by S4 negative-control failure.
- [ ] Expand only candidates with every fold balanced at five admitted samples per class to `n_syn=20/class`; preserve single-pass admission and real-real diversity decisions; not reached.
- [ ] Write per-fold pool counts, certificate failure reasons, and source composition to independent v5 result directories; no pool may be reported because no candidate is eligible.

### 12.4 Step 3: zero-API internal simulated LOCO comparison

- [ ] Build BREEZE-U only from an eligible balanced BREEZE pool and `noise_aug`, with exactly equal per-class contributions and immutable admitted source waveforms; not eligible after S4 failure.
- [ ] Compare `real_only`, `noise_aug`, eligible morphology-IDW, morphology-nearest, BREEZE-H, and BREEZE-U over four internal targets, `n_real={5,10,25}`, 10 fixed seeds, `n_syn=20/class`, and `--normalize none`; prohibited by the Step 1 stop rule.
- [ ] Use checkpointed evaluator rows and strict summarizer schema validation; do not mix S4 rows with historical v4 result identities; not reached.
- [ ] Mechanically evaluate the frozen rule for both Acc and Macro-F1: each candidate must meet or exceed `noise_aug` in at least three of four folds for every shot-count cell; not reached.

### 12.5 Decision and formal boundary

- [ ] If exactly one candidate passes, commit `pu_loco_v5_preregistration.md` before formal access, naming the candidate, code hash, 40 seeds, metrics, paired Wilcoxon direction, and complete Holm family; no eligible candidate exists.
- [ ] Run the registered formal held-out experiment exactly once only after preregistration; freeze and report its outcome without new selection or tuning; prohibited.
- [x] Commit an honest v5 failure analysis and manuscript-safe language that scopes cross-condition PU LOCO as a stress test while retaining the S4 diagnostic as a methodological result. No formal held-out experiment is run.
- [ ] Update API ledger, command manifests, todos, and GitHub verification; exclude raw datasets, generated arrays, checkpoints, virtual environments, and intermediate training runs from commits.

## 13. Private-MT v3 discriminative conditional synthesis (started 2026-07-13; inner-development only)

### 13.0 Protocol correction, scope lock, and data-card search

- [x] Synchronize local `main` with `origin/main` before beginning v3; record the baseline commit and preserve unrelated untracked PU-v4 outputs.
- [x] Read the private-MT v1 preflight reports, v2 smoke report, v2 failure analysis, v2 inner-train class-difference report, PU-v5 S4 failure analysis, and the active todo boundary in that order.
- [x] Correct the v2 causal statement: all three five-sample closed-loop pools were admitted; `BLOCKED` was caused by the downstream core gate (`0/6` versus real/noise), not an empty/admission-rejected pool.
- [x] Search the local `合成数据sci` project tree for factual spindle speed, feed, lead/pitch or transmission, sensor mounting, current definition, sampling, and file-to-operation records; distinguish direct evidence from missing fields and never infer a physical order from waveform appearance or filenames.
- [x] Inspect the owner-supplied earlier project copy at `Desktop/code/时序检测`; establish same-dataset SHA-256 provenance, record that its `datasets_test/` view is duplicate data, and exclude unassigned IDs `11/13/14` pending an owner split decision.
- [x] Write and freeze an auditable v3 machine-tool data-card search record with a field-by-field provenance table, exact local search scope, and an explicit `unavailable` status for every absent physical datum.
- [x] Keep file IDs `7/8` unread during all v3 development, calibration, candidate selection, and diagnostics; retain a loader-level hard error for any attempted access.
- [x] Lock the only development split: per class IDs `1/2/4/5` inner train and ID `10` inner validation; prohibit all tuning on formal files.
- [x] Lock v3 API use at zero through S-A, S-B, S-E, all admission audits, and the first internal downstream comparison; allow S-C only after both zero-API candidates pass admission but lose the frozen inner downstream gate, with a total S-C ceiling of 100 counted requests.
- [x] Do not add TPF, spindle/shaft order, lead-screw order, rotational imbalance, bearing frequency, guessed sensor semantics, learned generators, post-rejection repairs, or a new learned admission certificate.
- [ ] For every code/document/result change: review only scoped paths, commit without raw data or generated arrays/checkpoints, push `main`, and verify the remote SHA.

## 14. PU LOCO v6 CSCoh + multi-window evidence (started 2026-07-14; final cross-condition attempt)

### 14.0 Protocol, design, and hard boundary

- [x] Synchronize `main` with `origin/main` before v6 inspection; baseline is `375ed31`. Preserve the unrelated untracked v4 S3 artifacts and `breeze/OK.md`.
- [x] Read the v2, v3, v4 S2/S1, v5 failure/sanity, and v4 S3 freeze reports in the prescribed order.
- [x] Create and freeze `breeze/results/pu_loco_v6_cscoh_2026-07-14/v6_design.md` before CSCoh calibration or a real-window v6 diagnostic. It lists the complete candidate family, estimator, alpha grid, all thresholds, sampling schedule, aggregation test, and stop rules.
- [x] Keep API increment at zero through CSCoh diagnostics, v6 admission audit, candidate pool construction, and internal comparison. No LLM request was made; v6 stopped in Step 1.
- [x] Keep registered PU LOCO held-out windows unread until one unique internal candidate passes the frozen v6 rule and a v6 preregistration is committed. v6 stopped before either condition could be met.
- [x] After each scoped repository change, inspect the diff, commit it, push `main`, and verify the remote contains that SHA; no raw/processed data, virtual environments, generated pools, runs, or checkpoints were committed.

### 14.1 Step 0 — CSCoh implementation and unit evidence

- [x] Implement the frozen Hann multi-segment averaged cyclic-periodogram estimator in a new `verifier` module, including the fixed alpha-family construction, OR/IR paired score, and serializable settings.
- [x] Add deterministic unit tests: a synthetic BPFO impulse train must dominate the BPFO cyclic score over BPFI; seeded white noise must show no corresponding BPFO margin; invalid signal/parameter contracts must raise.
- [x] Run the focused test set with `breeze/.venv-breeze/bin/python` before source data are read by v6 code: `breeze/.venv-breeze/bin/python -m pytest breeze/tests/test_csc.py -q` passed 3/3.

### 14.2 Step 1 — train-only source separability go/no-go

- [x] Add a checkpointed diagnostic that loads only `config.SPLIT['train']` bearings from the three source conditions of each internal target, caches derived CSCoh scores under ignored `breeze/runs/`, and writes aggregate JSON/CSV/Markdown under the dedicated v6 result root.
- [x] Compute the frozen single-window q10-versus-q90 separation criterion for true OR/IR, wrong-label real windows, and deterministic unit-variance white noise; no quantile or tolerance was selected from results.
- [x] Run the frozen 20-window, 20-replicate-per-source paired one-sided Wilcoxon audit for every internal target, true/wrong/white category, and asserted OR/IR label. The all-target batch was already in flight when the first terminal result was observed; every independent checkpoint failed and no subsequent v6 stage started.
- [x] Both asserted classes failed both the single-window and pool criteria in every internal target; freeze `pu_loco_v6_failure_analysis.md`, mark the cross-condition PU line terminal, and prohibit Steps 2--4.

### 14.3 Step 2 — v6 verifier and mandatory admission audit (only after Step 1 permits)

- [x] Do not integrate a v6 verifier: prohibited by the Step 1 terminal CSCoh failure.
- [x] Do not run the four-part admission audit or build a pool: prohibited by the Step 1 terminal CSCoh failure.
- [x] Retain all boundaries and rejected waveforms unchanged; no threshold was retuned and no waveform was repaired.

### 14.4 Step 3 — only audit-eligible zero-API pool and internal comparison

- [x] Do not run BREEZE-H, `morphology_idw`, or `morphology_nearest` smoke/pool construction: all are prohibited by the Step 1 terminal CSCoh failure.
- [x] Do not build BREEZE-U: no eligible base family exists.
- [x] Do not run internal pseudo-LOCO downstream comparisons: prohibited before pool construction.

### 14.5 Step 4 — preregistration or terminal closeout

- [x] Do not create a v6 preregistration: no candidate entered internal comparison.
- [x] Do not execute formal held-out evaluation: formal windows remain unread.
- [x] Write failure analysis and retain the v5 manuscript-safe stress-test scope. No new PU cross-condition candidate, verifier amendment, or formal comparison is allowed after v6.

### 13.1 Pre-registered zero-API design and implementation

- [x] Create `breeze/results/mt_private_v3_design_2026-07-13/mt_private_v3_design.md` before running v3 candidate/audit outputs; specify every fixed candidate recipe rule, audit rule, downstream grid, threshold source, file-access boundary, and formal-selection gate.
- [x] Define S-A from inner-train only: select the strongest signed pairwise class-difference features already reported by the frozen normalized soft-band/statistics extractor; use deterministic target-class IAAFT carriers and fixed, feature-directional renderer gains rather than an LLM or physical-frequency assumption.
- [x] Define S-B from inner-train only: mix two nonidentical target-class real carriers through the same deterministic surrogate renderer; retain target class label, source-carrier hashes/IDs inside run manifests, and no cross-class carrier borrowing.
- [x] Keep the existing `MachineToolVerifier` and its existing ExtraTrees class-identity audit unchanged as exploratory admission components; record that neither is a component-physics certificate.
- [x] Add a v3 entry point with independent `prepare`, `audit`, `smoke`, `pool`, `downstream`, and `summarize` checkpoints, deterministic seeds, dedicated v3 run/result paths, and no write to any frozen v1/v2 artifact.
- [x] Add unit tests for formal-file guards, target-class-only carriers, signed directional rendering, no exact real/synthetic duplicate, all four admission controls, resume keys, and deterministic small-pool construction; focused v2/v3 tests pass `26/26`.

### 13.2 Admission-audit four-piece gate (must precede downstream)

- [x] Audit real inner-train target carriers under their own target label; core admission is 0.934 / 0.932 / 0.933 for normal / lead-screw anomaly / base imbalance, with every source file nonzero and all classes above the frozen 0.80 minimum. This remains an admission sanity result, not a physical validation claim.
- [x] Audit wrong-class controls by submitting each real inner-train class under each other class label; zero of 2,960 wrong-label windows was admitted.
- [x] Audit deterministic white-noise and constant-signal controls for every target label; zero of 300 white-noise and zero of 300 constant controls was admitted.
- [x] Audit source-only class separability using the frozen structure features and existing class-identity certificate; report it without fitting a new model. The certificate predicts the source class for 564/604 normal, 246/264 lead-screw, and 571/612 base-imbalance windows; this report is descriptive and is not a leave-one-file-out claim.
- [x] Freeze the v3 admission rule before S-A/S-B pool expansion: every target class has the declared real-carrier sanity evidence and every wrong-label, white-noise, and constant control has zero admission. The frozen decision is `PASS`; only S-A/S-B smoke is now eligible.
- [ ] If the four-piece audit fails, write a v3 failure analysis and stop before downstream/formal work; do not loosen quantiles or suppress controls to recover a pool.

### 13.3 S-A and S-B zero-API pool construction

- [x] Run S-A one-sample-per-class renderer/admission smoke under the frozen rule; all three classes are admitted on attempt 0 with hard gates, class identity, and diversity all passing. The smoke manifest records only inner-train carrier sources `1_2`, `2_1`, and `3_2`.
- [x] Run S-B one-sample-per-class renderer/admission smoke under the identical frozen rule; all three classes are admitted on attempt 0 with hard gates, class identity, and diversity all passing. Each manifest row records two distinct target-class carrier indices; the normal-class pair happens to originate from different windows of source file `1_2`.
- [x] Expand each independently passing S-A/S-B smoke pool to `n_syn=5/class` with checkpointed per-item certificates and manifests; both pools are balanced at 5/class. S-A used 16 attempts total (one lead-screw rejection); S-B used 17 (two lead-screw rejections); each rejected candidate was discarded without repair.
- [x] Expand only a balanced five/class pool to `n_syn=20/class`; both pools are balanced at 20/class and retain immutable admitted waveforms plus their target-class carrier provenance. S-A attempts are normal/lead/base `23/23/20`; S-B attempts are `22/26/20`, all below the frozen ceiling of 80.
- [ ] If a zero-API candidate cannot fill all three classes within its predeclared attempt budget, freeze the capacity result rather than changing renderer bounds or sampling from validation/formal data.

### 13.4 Internal downstream comparison and conditional S-C/S-E

- [x] Freeze and commit downstream amendment 1 before any metric is produced: use target-class-balanced `n_syn=10/class` for `n_real=10`, and `n_syn=20/class` for `n_real=25/50`, identically for every non-real method. This preserves the low-shot cell and the existing no-replacement `noise_aug` definition.
- [x] Compare each eligible S-A/S-B pool against `real_only` and `noise_aug` on inner validation only, with `n_real={10,25,50}`, ten fixed seeds, the amended target-class-balanced synthetic-budget mapping, fixed model/training settings, Acc, Macro-F1, per-class F1, confusion matrices, and paired Wilcoxon/Holm summaries. Both have 90 seed rows; no formal file or API call was used.
- [x] Apply the predeclared S-A/S-B success rule: mean Acc and mean Macro-F1 must each be at least `noise_aug` in at least five of six cells. S-A is `4/6`; S-B is `2/6`; neither zero-API candidate passes.
- [x] Enable S-C only after an S-A/S-B pool passes the four admission controls, fills its pool, and fails the inner downstream gate. This trigger was met; the API plan was frozen, the credential was supplied only through the process environment, and the user explicitly authorized the bounded extension without exposing a secret in source or results.
- [x] Freeze `mt_private_v3_s_c_api_plan.md` before the first S-C request: 3 total smoke requests, then a resumable 100-request total ceiling; HTTP/JSON failures count; prompts expose only inner-train statistics and deterministic directional effects; no physical frequencies, validation, formal IDs, secrets, or rejected-waveform repair are permitted.
- [x] Freeze S-C API amendment 1 after the original 3-request smoke returned HTTP 200 but all three responses failed only the old strict whole-response JSON parser (no renderer or verifier was reached). Preserve those three counted attempts; allow exactly three additional smoke requests using a first-JSON-object transport decoder while retaining the same JSON schema and all downstream gates.
- [x] Freeze S-C API amendment 2 after the amended smoke admitted base and lead-screw but normal failed only the unchanged Y-channel `psd_w1` hard gate. Allocate at most the two remaining predeclared feedback rounds solely to that pending normal slot; no threshold, renderer, prompt statistic, or acceptance criterion changes.
- [x] Run the bounded S-C smoke: all three classes are admitted after 7/100 counted requests (the first three remain parser-only failures; the normal feedback response is accepted under unchanged gates). Formal IDs remain unread.
- [x] Run the bounded S-C full-pool construction under its 100-request total cap. It stops at 98 with normal/lead/base counts `20/20/18`; the two remaining base slots exhausted their fixed feedback rounds, so S-C is a capacity failure and is ineligible for downstream/formal evaluation. Every HTTP/format failure is counted; no rejected waveform was repaired.
- [x] Freeze S-C API amendment 3 before further requests: after explicit user authorization for up to 100 additional counted requests, raise the total ceiling to 200 but expose exactly two replacement slots (`20`, `21`) for the only deficient `base_imbalance` class. Keep the target at 20/class, all previous slots and their fixed feedback cap unchanged, and stop as soon as the two replacements are either resolved or exhausted; unused authorization is not spent.
- [x] Run the amendment-3 base-only capacity extension: replacement slots `20` and `21` were both admitted on their initial requests, producing exactly 20 admitted samples in every class at 100 cumulative API requests. The pool is now eligible for inner downstream only; formal IDs remain unread.
- [x] Compare the balanced S-C pool on the unchanged 90-row inner grid. S-C reaches `6/6` Acc/Macro-F1 cells at least `noise_aug` (S-A/S-B remain `4/6` and `2/6`), making it the unique internally eligible candidate; all Holm-adjusted one-sided tests remain non-significant and are reported without reinterpretation. Formal IDs remain unread at this checkpoint.
- [x] Do not construct or compare S-E after the S-C internal decision: S-C is the sole eligible BREEZE candidate, so it already satisfies the frozen unique-candidate formal boundary. A post-formal union construction would be an impermissible new candidate selection after formal data were read.

### 13.5 Formal boundary and honest closeout

- [x] Exactly one named v3 candidate meets the internal rule: S-C is `6/6`, while S-A/S-B are `4/6`/`2/6`. Commit `mt_private_v3_preregistration.md` and its machine-readable hash lock locally before reading IDs `7/8`; freeze candidate identity, source code SHA, pool hash, split, seeds, CNN settings, metrics, Wilcoxon direction, and Holm family. This local commit is intentionally not pushed until the final result exists.
- [x] Run the formal file-ID `7/8` experiment exactly once after the locally committed preregistration. All 360 preregistered rows completed (3 methods × 3 real-shot cells × 40 seeds); raw data remain outside Git. S-C is significantly better than `noise_aug` at `n_real=10` in both primary metrics after Holm, non-significant at 25, and worse at 50; the full directionally mixed outcome is frozen without retuning.
- [x] The zero/multiple-candidate failure branch is not applicable: S-C was the unique internally eligible candidate before formal files were read. No post-formal candidate, pool, or union is considered.
- [x] Freeze the API ledger, reproducibility commands, manifests/checksums, and final result reports; verify that no raw data, virtual environment, checkpoint, generated array, or credential is staged.

## 15. Writing-only logic revision (started 2026-07-15; zero API)

- [x] Fetch `origin/main`, verify local/remote equality, preserve unrelated untracked artifacts, and freeze the source/evidence/generated/figure baseline.
- [x] Activate and read `awesome-ai-research-writing` and `pdf` skill instructions.
- [x] Create `analysis/writing_revision_log.md` with P1--P6 line-level diagnosis, examples, word/negation/page baselines, and acceptance criteria before editing manuscript prose.
- [x] Rewrite and compile the abstract; retain every result macro and boundary while meeting the six-sentence, 220-word, and two-limitation limits. Final abstract: six sentences, 190 words, zero counted negative limitations, 17-page compile.
- [x] Rewrite and compile the Introduction into the required problem--cost--opportunity--gap--solution--questions--contributions--scope chain; retain 17 pages and the baseline compile-diagnostic ceiling.
- [x] Rewrite and compile Related Work; all four subsections now close with an evidence-bounded BREEZE contrast, with citations and the positioning table unchanged.
- [x] Rewrite and compile Method; every subsection is motivation-first, equations are introduced by their interpretive purpose, and slot/window accounting is separate from provenance. Equations and parameters remain unchanged.
- [x] Rewrite and compile Experimental Design; protocol choices are motivated, dataset details are separated, all split/budget/seed/hyperparameter values are unchanged, and a newly introduced 5.9-pt overfull line was removed before proceeding.
- [x] Rewrite and compile Results; all subsection headings and opening sentences state bounded conclusions, Berkeley follows the registered 12/12--lower-shot--ten-shot order, and no rule-vs-unstructured significance was added.
- [x] Rewrite and compile Boundaries/Negative Results; one opening sentence now frames protocol value, while the full PU v1--v6 and UMich/MU-TCM stop evidence remains intact.
- [x] Rewrite and compile Discussion; the three evaluation questions are answered in order, beginning with the random-plus-verifier result of 0 admitted slots. Compile is 18 pages, within the +1-page ceiling.
- [x] Rewrite and compile Conclusion and final prose; retain a positive synthesis and one final boundary sentence. The PDF returned from 18 to the baseline 17 pages.
- [x] Extract all 81 final paragraph/list opening sentences into the revision log and verify that the sequence reconstructs the manuscript argument.
- [x] Recount the abstract (six sentences, 166 words, zero counted negative limitations) and full prose (67 to 8 negative-qualifier sentences, 88.1% reduction); audit terminology, numerical values/macros, citations, equations, tables, figures, generated files, and claim terms.
- [x] Run a clean final compile with zero errors, LaTeX warnings, or undefined references and no new box diagnostics; render all 17 pages with Poppler and inspect every page for clipping, overlap, missing content, or illegibility.
- [x] Review the scoped diff, stage only writing artifacts, commit as `2009ccf` with `docs: writing-only revision of BREEZE manuscript`, push `origin/main`, and verify the remote advanced from `1f06c84` to `2009ccf`.

## 16. Solid-story narrative revision (started 2026-07-16; zero API)

### 16.1 Freeze and scope controls

- [x] Read `breeze_solid_story_prompt.md`, `AGENTS.md`, the active evidence ledger, claim-to-evidence map, prior writing log, and the current CAS manuscript before editing.
- [x] Fetch `origin/main`; verify local `main` and `origin/main` both equal `bfb6f8facfcc7ad79b864caed6eefc5f5016cf26` and preserve all unrelated untracked experiment artifacts.
- [x] Activate the local `awesome-ai-research-writing` and `pdf` instructions. Treat `nature-figure` as an immutable-figure audit constraint because this task explicitly prohibits figure redraws.
- [x] Freeze source hashes, section/table/figure/equation structure, generated-macro usage, experimental-number tokens, citation keys, PDF page count, and baseline compile diagnostics in `analysis/solid_story_revision_log.md`.
- [x] Confirm the execution interpreter is `breeze/.venv-breeze/bin/python` (Python 3.12.13) and record its version; make no LLM API calls.

### 16.2 Literature verification

- [x] Verify the primary publisher/preprint records for the prompt's studies #1--8; record exact title, authors, venue, year, DOI/URL, mechanism failure, knowledge-residence category, and suitability for citation.
- [x] Require at least six independently verified studies from #1--8 in Introduction/Related Work; all eight verified studies are cited, and HAWAN-PIR remains uncited without a stable primary record.
- [x] Add or correct only verified BibTeX records in `breeze/paper/references.bib`; six missing records were added without unsupported performance summaries or protocol-incompatible accuracy comparisons.
- [x] Map each cited study to the knowledge-residence spectrum: learned weights, physics-informed objective/architecture, description-conditioned learned generator, or explicit recipe plus fixed renderer and calibrated admission.

### 16.3 Narrative reconstruction

- [x] Rewrite the Abstract as S1 -> root cause b -> components c -> frozen S4/S5 evidence -> boundary -> significance; final abstract is 189 words and retains every result macro and claim boundary.
- [x] Rewrite Introduction paragraph 2 with literature-specific trained-generator failure mechanisms; paragraph 3 is the explicit shared-root-cause paragraph.
- [x] Tie the three solution components in Introduction paragraph 4 directly to the root cause: explicit LLM recipe knowledge, fixed deterministic rendering, and train-calibrated closed-loop admission/audit.
- [x] Rewrite the three evaluation questions and four contributions so each maps to component 1, component 2, the complete system, or its registered boundary; retain the final scope paragraph and trained-baseline blocker.
- [x] Reorganize Related Work as a knowledge-residence spectrum and close each subsection with BREEZE's precise position without claiming trained-baseline superiority.
- [x] Add `Where physical knowledge resides` to Table 1 while preserving its methods, evidence meaning, and all other table/figure environments; left-aligned fixed-width columns introduce no new box diagnostic.
- [x] Add root-cause-motivated opening sentences to every Method subsection; identify the renderer as component 1 and the verifier/feedback loop as component 2 without changing equations, parameters, algorithms, or responsibilities.
- [x] Reframe Results subsection titles, first sentences, and closing synthesis around component ablations and frozen evidence; keep all numerical macros and qualified Berkeley/CWRU/PU wording within the ledger.
- [x] Open the boundary section with the framework-predicted morphology--condition limit, then preserve the complete six-stage PU failure chain and milling protocol stops.
- [x] Answer the three evaluation questions at the start of Discussion and add an evidence-bounded operating guide for choosing BREEZE versus a trained generator.
- [x] Rewrite Conclusion into two positive paragraphs plus one boundary sentence, without adding SOTA, universal superiority, zero-data, or formal-validity claims.

### 16.4 Incremental verification

- [x] Compile after Abstract/Introduction/Related Work and inspect errors, unresolved citations, page count, and new box diagnostics: 18 pages, zero unresolved citations, and no positioning-table box diagnostic.
- [x] Compile after Method and confirm equation, algorithm, figure, and cross-reference identities are unchanged.
- [x] Compile after Results/Boundaries/Discussion/Conclusion and confirm generated tables/macros remain untouched and all claim-sensitive terms match the ledger.
- [x] Run a narrative trace audit showing that Abstract, Introduction, Method, Results, Boundaries, Discussion, and Conclusion reconstruct the same a -> b -> c -> ablation -> boundary chain.
- [x] Compare baseline/final experimental-number tokens, generated macro uses, equations, algorithms, labels, figure includes, and non-positioning table bodies; explain every allowed citation/table-positioning difference.
- [x] Verify the trained TimeGAN/DDPM comparison remains explicitly marked as unavailable/blocking evidence rather than converted into a result.

### 16.5 PDF and delivery

- [x] Run a clean final LaTeX/BibTeX compile with zero fatal, undefined-reference, and undefined-citation warnings and no new layout diagnostic beyond the frozen baseline.
- [x] Render every final PDF page with Poppler and inspect for clipping, overlap, missing glyphs, unreadable references, and positioning-table overflow.
- [x] Record final hashes, page count, bibliography audit, zero-API status, claim audit, and visual-QA outcome in `analysis/solid_story_revision_log.md`.
- [x] Review the scoped diff; stage only the manuscript, verified bibliography, log, and this checklist; preserve all unrelated untracked artifacts.
- [x] Commit with a writing-only solid-story message, push `main` to `origin/main`, and verify the pushed commit is the remote head before reporting completion.

## 17. Reviewer-requested evidence additions (started 2026-07-16)

- [x] E3 verifier-gate ablation: replay the archived PU `K=3` candidates without
  API calls; require the full gate to reproduce the frozen balanced pool before
  materializing variants; remove M2/M3/M4/M5 one at a time; preserve the
  `B=150`/class budget, frozen file split, and 20 paired CNN seeds.
- [x] E3 diversity sensitivity: evaluate `0.5delta_y`, `1.0delta_y`, and
  `2.0delta_y` from the same cache. Record `0.5delta_y` as byte-identical to
  no-M5, `1.0delta_y` as the frozen reference pool, and `2.0delta_y` as the
  capacity stop `healthy=64<150`; do not substitute a lower-budget comparison.
- [x] E3 manuscript integration: generate and validate the gate-ablation table
  from CSV, add the zero-API protocol and bounded conclusion to the CAS paper,
  and record the audit in `analysis/e3_e4_integration_log_2026-07-16.md`.
- [in_progress] E1 TimeGAN/DDPM: formal PU v2 is running under the output-root
  lock with the full-train and few-shot regimes, `n_real={5,10,25}`, 40 seeds,
  and no non-default rescue tuning. Keep all manuscript trained-baseline results
  explicitly unavailable until the complete grid and cost audit are available.
- [x] E2 second backbone is optional insurance, not a current experimental
  gate; do not add it unless a reviewer specifically requires it.
- [x] E4: add verified few-shot/meta-learning and split-validity citations with
  limited contextual claims; bibliography now has at least 50 entries.

## 18. Major-revision round from review of `origin/main@b4e6981` (started 2026-07-16)

### 18.0 Scope freeze, environment, and evidence controls

- [x] Preserve all unrelated untracked result directories, user files,
  old smoke runs, and frozen snapshots; record the review attachment path, current
  `HEAD`, PDF hash/page count, source hash, and working-tree baseline in a new
  major-revision audit log before changing manuscript claims.
- [x] Resolve the execution-environment instruction before any new Python run:
  inspect whether `breeze/.venv-breeze` is backed by Anaconda, inventory a Conda
  after an initial Conda audit, the user explicitly selected
  `breeze/.venv-breeze/bin/python`; record that executable, package lock, device,
  and seed settings. Do not mix environments inside one formal experiment.
- [x] Audit the currently running E1 process without modifying its output; determine
  whether it complies with the resolved environment rule and whether it must be
  allowed to finish, paused at a checkpoint, or replaced by a clean run.
- [ ] Freeze a claim-to-review matrix mapping every reviewer criticism and question
  to source lines, code, existing evidence, required experiment, expected artifact,
  and final disposition (`fixed`, `measured`, `qualified`, or `blocked`).
- [ ] Re-read the active evidence ledger, split manifests, frozen reports, API ledger,
  and all current manuscript statements before editing. Stop and report any numeric
  conflict instead of reconciling it silently.
- [ ] Keep the audited API total at 1231/3000 unless the user explicitly authorizes
  additional calls. Design all zero-API work first; record any independent-pool or
  prompt ablation that cannot fit the existing budget as an authorization blocker.

### 18.1 Correct the two mathematical and claim-evidence hard errors

- [ ] Trace the implemented one-sided gate predicates from calibration through
  `verifier/v2.py` and compare them line by line with Eq. (1); document whether code
  uses an upper or lower bound for every gate family.
- [ ] Replace the tautological manuscript predicate `f_j(x)<=u OR f_j(x)>=l` with an
  explicit direction-indexed definition (upper-bound set, lower-bound set, and
  two-sided set), preserving the actual code semantics and handling unavailable
  evidence without inventing a gate.
- [ ] Add a small deterministic formula/code consistency test covering upper-only,
  lower-only, two-sided, failed, passed, and unavailable predicates; require every
  case to match the manuscript definition.
- [ ] Audit the definition of diversity for an empty admitted set and the first
  admitted sample; state the exact convention in method text and code comments.
- [ ] Trace `nn_diversity` in every metrics script and generated table; distinguish
  synthetic-to-synthetic pool diversity from synthetic-to-real memorization distance.
- [ ] Remove every unsupported interpretation of `nn_diversity` as distance to real
  data and every unproven phrase such as “without copying training windows” until a
  dedicated synthetic-to-real audit exists.
- [ ] Compile after the hard-error patch and verify equations, labels, algorithm
  references, and gate names remain internally consistent before proceeding.

### 18.2 Build independent memorization and physical-validity diagnostics (zero API)

- [ ] Specify synthetic-to-real diagnostics before computing them: exact byte/hash
  equality, nearest real-window distance on train-calibrated normalized features,
  maximum normalized cross-correlation with lag reporting, and raw/subsequence match
  checks appropriate to PU/CWRU/Berkeley exemplar construction.
- [ ] Define the unit, normalization, channel aggregation, lag range, and reference
  population for each diagnostic using training data only; prohibit thresholds chosen
  from downstream test performance.
- [ ] Implement checkpointed metric extraction with small-pool smoke fixtures,
  duplicate controls, carrier/exemplar controls, and deterministic resume keys.
- [ ] Run a PU smoke on a few real/synthetic windows; verify known exact-copy controls
  are detected and ordinary noncopies are not mislabeled before batch execution.
- [ ] Run the frozen PU, CWRU, and Berkeley pools only after smoke acceptance; write
  per-sample CSV, aggregate CSV, JSON provenance, checksums, and an MD audit report.
- [ ] Treat Berkeley explicitly as exemplar-based simulation augmentation; report
  carrier identity and similarity separately from the added wear component.
- [ ] Add at least one hold-out physical diagnostic not directly enforced by the
  renderer/verifier pair, selecting it from available raw measurements and declaring
  it before reading method rankings. If no defensible independent diagnostic exists,
  weaken “physical realism” to “gate consistency” and record the limitation.
- [ ] Report real-vs-synthetic discriminator AUROC only with grouped cross-validation
  by source file/carrier and confidence intervals; do not use a leaking window split.

### 18.3 Make all physical-metric reporting complete and reference-consistent

- [ ] Extend the generated physics table to include per-class kurtosis-W1, envelope
  frequency-alignment error, peak prominence, harmonic consistency, PSD-W1, RMS-W1,
  band-energy error, synthetic-to-synthetic diversity, and synthetic-to-real metrics.
- [ ] Preserve unfavorable results, including PU kurtosis-W1 and OR/IR cases where
  rule has lower frequency error than LLM; prohibit selective prose summaries.
- [ ] Audit Figure 5 reference sampling. Use the same declared real reference
  population for waveforms and distance tables, or label the distinct 150-window
  visualization sample explicitly and explain why it is not the W1 reference set.
- [ ] Generate all revised tables and figure annotations from structured CSV/JSON;
  add grid, class, method, unit, and population assertions to the generator script.
- [ ] Visually inspect every revised plot/table at publication size and verify that
  unfavorable rows, units, confidence intervals, and reference populations are legible.

### 18.4 Repair statistical scope and multiple-comparison claims

- [ ] Enumerate the true stochastic hierarchy for every result: independent LLM pool,
  fixed synthetic pool, few-shot draw, classifier initialization, dataset unit, and
  test unit. Record exactly which levels vary under the current 20/40 seeds.
- [ ] Rewrite the inference unit everywhere: current paired CNN/few-shot seeds support
  repeatability of a fixed admitted pool, not population-level variability of LLM
  generation. Remove any broader interpretation before adding new pools.
- [ ] Recompute CWRU correction over the global 72-test family using Holm and BH while
  retaining the original local-family outputs for transparency; report both scopes
  without calling local-family `72/72` global FWER control.
- [ ] Add paired effect sizes, bootstrap or paired-seed 95% confidence intervals,
  worst-class F1, and predeclared practical-effect thresholds to PU/CWRU/Berkeley
  tables. Keep inferential caveats tied to the fixed-pool design.
- [ ] Add confidence intervals and multiplicity-aware tests to the M2--M5 gate
  ablation; distinguish “directionally lower mean” from evidence that every gate is
  individually necessary.
- [ ] Verify Berkeley LLM-rule practical differences and explicitly state convergence
  at 10 shots; do not equate small statistical differences with large practical gains.
- [ ] Draft, but do not execute, a hierarchical independent-pool design with pool as
  the outer unit and CNN/few-shot seed as the inner unit; calculate required LLM calls,
  compute, storage, and API cost for 5 and 10 pools per method.
- [ ] Ask for explicit authorization before spending API on independent pools; if not
  authorized, keep the limitation and remove population-level generator claims.

### 18.5 Repair control fairness and isolate where the gain comes from

- [ ] Reframe random+verifier as a measured capacity failure rather than a matched
  downstream control; ensure `random open-loop` is never described as verifier-matched.
- [ ] Audit existing K=0/K=1/K=3 caches and reports. If complete and protocol-matched,
  generate a closed-loop table; otherwise design the smallest zero-API cache replay
  that does not manufacture missing candidates.
- [ ] Specify a train-statistics parameter estimator in the same recipe space and
  renderer, with no LLM and no access to validation/test labels; justify every
  objective and bound from train-only calibration.
- [ ] Specify a black-box optimizer baseline only if it can use the identical recipe
  domain, verifier evaluations, candidate budget, and renderer. No extra evaluations,
  privileged gradients, or test-selected objective are allowed.
- [ ] Smoke-test estimator/optimizer candidates on one class and one seed; inspect
  recipe validity, budget accounting, gate reports, and capacity before full pools.
- [ ] Run only candidates that pass the predeclared smoke and capacity rules; report
  failures without rescue tuning, then compare downstream results under the same pool
  budget and paired seeds.
- [ ] Design no-exemplar, no-class-statistics, and no-feedback LLM ablations with exact
  prompt redactions and equal call budgets. Do not execute them until API authorization
  and independent-pool statistical design are resolved.
- [ ] Reframe the central claim as “LLM-mediated recipe selection” unless the new
  controlled ablations isolate pretrained LLM knowledge from supplied kinematics,
  examples, statistics, and feedback.

### 18.6 Complete strong trained-generator baselines fairly

- [x] Deferred by the final Q2-closeout scope: stop the formal TimeGAN/DDPM v2
  queue, preserve all checkpoints/partial rows, and never summarize them as a
  result. Formal trained-generator comparison remains future work.
- [ ] After the first complete DDPM cell, estimate wall time from observed class-level
  costs and update this checklist/report with a defensible ETA rather than extrapolating
  from TimeGAN alone.
- [ ] Validate the complete E1 grid: TimeGAN/DDPM, full-fold/few-shot generator
  training, `n_real={5,10,25}`, 40 paired seeds, 20 synthetic windows/class, identical
  file split and downstream CNN, no literature-default rescue tuning.
- [ ] Add instability diagnostics from raw losses/checkpoints and count failed/nonfinite
  runs without dropping them. Freeze a missing-cell audit before any aggregation.
- [ ] Produce downstream, physical-quality, memorization, parameter-count, training
  data, wall-time, and compute-cost tables from the complete grid only.
- [ ] Assess TTS-GAN/CFG-DDPM/physics-informed generation/BearGen comparability from
  primary implementations and licenses. Add a formal baseline only when its data
  boundary and architecture can be matched without ad hoc degradation or hidden
  tuning; otherwise document why it is not a valid direct baseline.
- [ ] Keep all SOTA and trained-generator-superiority claims prohibited until the
  matched formal grid is complete and statistically audited.

### 18.7 Test classifier dependence (zero API; smoke before scale)

- [ ] Freeze architectures and literature-supported defaults for ResNet1D-18, TCN,
  a compact Transformer encoder, and a traditional feature classifier before reading
  their method rankings; record parameter counts and compute budgets.
- [ ] Implement each backbone behind the same train/evaluate interface with grouped
  file split, identical few-shot selections, paired seeds, and no method-specific
  tuning. Add deterministic unit and shape tests.
- [ ] Run one-seed PU smoke for LLM/rule/random at `n_real=5`; require all backbones to
  finish, emit finite metrics, and reproduce the exact split/seed manifest.
- [ ] Run a five-seed calibration-free pilot solely to detect crashes or capacity
  problems, not to select hyperparameters. Freeze the formal backbone plan afterward.
- [ ] Execute the predeclared 20-seed PU source-ablation grid and report Accuracy,
  Macro-F1, worst-class F1, paired effects, confidence intervals, and corrected tests.
- [ ] State whether ordering is stable, mixed, or reversed across classifiers; do not
  hide a backbone that weakens the preferred conclusion.

### 18.8 Audit and, where feasible, strengthen grouping/generalization protocols

- [ ] Inventory physical bearing/specimen identities in PU and CWRU from raw metadata
  and dataset documentation. Do not equate files, windows, loads, fault sizes, and
  specimens without source evidence.
- [ ] Determine whether PU within-condition leave-one-bearing-out is feasible with
  enough train bearings/classes and whether cached recipes can be recalibrated without
  test leakage or new API calls.
- [ ] Determine whether CWRU can support a genuine leave-one-specimen-out protocol;
  if specimen identity is unavailable or confounded with class/severity, mark the
  requested claim structurally unsupported rather than inventing a split.
- [ ] Pre-register any feasible grouped protocol, including calibration, generation,
  admission, downstream seeds, statistics, and stop conditions, before reading test
  results. Smoke one fold before batch execution.
- [ ] Evaluate whether a cross-machine or cross-dataset task has compatible channels,
  labels, sampling, and physical meaning. Run it only if the task is scientifically
  identifiable; otherwise retain the current explicit boundary.
- [ ] Rewrite all generalization claims to the exact supported unit: measurement-file,
  load, bearing, specimen, machine, or sensor. Do not use “cross-condition” as a
  substitute for cross-specimen evidence.

### 18.9 Reproducibility and public artifact plan

- [ ] Recover and record the exact PU provider/model identifier, temperature, top-p,
  provider seed support, prompt templates, response hashes, recipe schema, renderer
  seeds, verifier config, and API-call accounting. Mark irrecoverable fields explicitly.
- [ ] Inventory ignored PU/CWRU/Berkeley recipes, pool manifests, gate reports, and
  generated arrays; separate redistributable derived artifacts from licensed raw data,
  credentials, and oversized checkpoints.
- [ ] Create a deterministic release-manifest builder that lists paths, sizes, hashes,
  provenance, regeneration commands, and exclusions without copying secrets or raw data.
- [ ] Package or document the minimum reproducibility bundle needed to regenerate each
  paper table from lawful inputs; verify it in a fresh output directory.
- [ ] Add a data/code availability subsection explaining why `breeze/runs/` is ignored,
  what will be released, and how CWRU/Berkeley pools and recipe records are reproduced.

### 18.10 Literature, manuscript, supplement, and submission synchronization

- [ ] Verify primary sources for simulation-based inference, rejection/ABC,
  constrained program generation, and LLM-as-optimizer; add only literature that
  clarifies the method boundary and does not substitute for missing experiments.
- [ ] Rewrite Abstract, Introduction, Method, Results, Discussion, and Conclusion only
  after the corresponding evidence tasks complete; preserve Berkeley partial/no-go,
  PU LOCO boundary, UMich confounding, MU-TCM stop, and trained-baseline status.
- [ ] Add a reviewer-question response matrix answering all 12 questions with code,
  table, report, or scoped limitation references.
- [ ] Update `submission_checklist.md` to the actual final page count and unresolved
  blockers; remove stale 17-page assertions.
- [ ] Audit the supplementary outline and remove stale private-data/v2 language;
  synchronize equations, metric definitions, pool/statistical units, and ablations.
- [ ] Request author names, affiliations, corresponding-author email, ORCID, funding,
  conflicts, and acknowledgments from the user; placeholders remain a submission
  blocker and must not be guessed.
- [ ] Generate every final numerical statement from CSV/JSON, run claim-to-evidence and
  citation audits, and verify no manuscript claim depends on partial E1 output.
- [ ] Compile the canonical CAS manuscript with zero fatal/undefined warnings, compare
  layout diagnostics to baseline, render every PDF page, and visually inspect all
  equations, tables, figures, references, and supplementary links.
- [ ] Review the final scoped diff, preserve unrelated untracked files, commit only
  audited source/report/generated artifacts, fetch `origin/main`, push with approval,
  and verify the remote commit before declaring the major revision complete.

## 19. Immediate Q2-ready closeout (final controlling scope; zero training/API)

### 19.0 Scope and mandatory skills

- [x] Freeze the final scope: zero new training, zero API, no independent pools,
  no new backbone, no new cross-specimen split, and no trained-generator result.
- [x] Use `awesome-ai-research-writing` for claim/evidence and prose revision;
  use the current cached `pdf` skill for compilation, Poppler rendering, and
  page-by-page visual verification.
- [x] Stop the briefly resumed E1 service and preserve its partial v2 directory;
  keep TimeGAN/DDPM absence in one limitation only.
- [x] Convert every in-scope review item H1--H5, C1--C4, and M1--M5
  into an evidence/status row in the major-revision log and final checklist.
- [x] Mark the superseded large-experiment items in §18 as future work rather
  than blockers for this Q2 submission.

### 19.1 H1--H2 hard-error correction

- [x] H1: verify code predicates, replace the tautological one-sided
  equation with distinct lower/upper/two-sided relations, and state the empty-set
  diversity convention.
- [x] H1: add a deterministic semantics test/audit and compile the corrected
  equation before changing any dependent prose.
- [x] H2: remove the unsupported copying claim and correct
  `nn_diversity` to synthetic-to-synthetic within-pool spacing.
- [x] H2: implement a checkpointed zero-API synthetic-to-real audit over frozen
  PU/CWRU/Berkeley pools: exact equality, nearest train-window distance, and
  maximum normalized cross-correlation, with per-class provenance and smoke
  controls before batch execution.
- [x] H2: if any dataset lacks a reproducible frozen pool/reference mapping,
  mark that row unavailable and retain the narrowed limitation; do not replace
  the missing pool or infer non-copying.
- [x] H2: state explicitly that Berkeley is exemplar-background simulation and
  report its similarity audit separately from bearing pools.

### 19.2 H3--H4 complete physical evidence

- [x] H3: extend the generated table with every available per-class
  kurtosis-W1 and fault-frequency alignment value, including rule-favouring
  cells and explicit NA for healthy/nonapplicable cases.
- [x] H3: rewrite the physical-results paragraph to state that LLM does not lead
  every physical metric and that its aggregate advantages concentrate in
  RMS/PSD/band-energy under the frozen protocol.
- [x] H4: trace the real-window sampling manifest behind Figure 5 and the W1
  calculations; either regenerate Figure 5 from the same full reference or
  label its deterministic 150-window visualization subset unambiguously.
- [x] H4: regenerate all affected artifacts from structured inputs and audit
  reference population, class, unit, method, and pool hashes.

### 19.3 H5 statistical recalculation and wording

- [x] H5a: identify every core PU/CWRU/Berkeley hypothesis row and compute a
  global BH sensitivity column from frozen p-values; preserve registered
  within-family Holm results alongside it.
- [x] H5a: generate the global-BH table from CSV and replace abstract `72/72`
  shorthand with dataset/family-specific wording that cannot be read as global
  FWER control.
- [x] H5b: state the stochastic unit exactly: one fixed synthetic pool per
  protocol, with paired repeats varying few-shot sampling and CNN initialization.
- [x] H5b: scope inference to stable downstream utility of these frozen pools;
  add absence of independent-pool inference to one limitations paragraph.
- [x] H5c: rename random as `random open-loop` wherever appropriate; describe
  random+verifier as a zero-capacity failure rather than a matched downstream
  comparison.
- [x] Verify all q values, pass counts, effect sizes, and correction-family
  descriptions against frozen CSVs before accepting the statistical rewrite.

### 19.4 C1--C4 claim convergence

- [x] C1: align Abstract, Introduction contributions, Discussion, and Conclusion
  to the bounded positioning: a training-free, auditable LLM-mediated recipe
  generation and physics-gated augmentation framework evaluated under three
  public frozen few-shot protocols.
- [x] C1: prohibit SOTA, trained-generator superiority, zero-real-data, formal
  physical correctness, and cross-specimen/cross-machine generalization claims.
- [x] C2: generate Berkeley effect-size wording from frozen means; report
  12/12 against non-structured controls, small lower-shot rule differences,
  and convergence at 10 shots without inflating practical importance.
- [x] C3: consolidate TimeGAN/DDPM absence into one limitations statement;
  remove repeated defensive wording and exclude all smoke/partial numbers.
- [x] C4: use `LLM-mediated recipe selection`; disclose kinematics, training
  statistics, exemplar description, and feedback as prompt inputs; do not infer
  pretrained physical knowledge.
- [x] C4: retain the shared renderer/verifier frequency-definition circularity
  risk and the bounded evidence from rule/random controls without calling gate
  compliance physical truth.

### 19.5 M1--M4 submission mechanics and reproducibility

- [x] M1: update page count in `submission_checklist.md`, clean stale private-data
  and v2 language from the supplement, and synchronize `\shorttitle` with the
  final training-free recipe framework positioning.
- [x] M2: inventory every author/affiliation/ORCID/email placeholder and list it
  as the sole user-supplied submission blocker; never guess identity metadata.
- [x] M3 optional: skipped because the current related-work coverage is
  sufficient and the item is explicitly non-blocking; no unneeded citation
  expansion was introduced.
- [x] M4: inventory prompt templates, recipe examples, renderer seeds, pool
  manifests, verifier configs, and ignored run artifacts; add precise data/code
  availability wording that distinguishes repository paths from planned release.
- [x] Update cover letter, highlights, supplementary material, and submission
  checklist so every claim and limitation matches the canonical manuscript.

### 19.6 M5 final build, visual audit, and delivery

- [x] Generate every numeric LaTeX table through the table builder; reject hand
  copied numerical edits and fail on missing/duplicate grids.
- [x] Compile the canonical CAS PDF with no fatal, unresolved citation, or
  unresolved reference errors; compare all layout diagnostics with baseline.
- [x] Render all final pages under `tmp/pdfs/` with Poppler and visually inspect
  equations, tables, figures, captions, page numbers, references, and glyphs.
- [x] Create `analysis/final_checklist_q2_2026-07-16.md` with one evidence-linked
  row for each H1--H5, C1--C4, and M1--M5 item; continue revisions for any row
  that is not `verified`, `qualified`, or the single author-metadata blocker.
- [x] Run a final evidence-ledger, terminology, generated-number, bibliography,
  API, frozen-directory, and Git-scope audit.
- [x] Commit the audited closeout as b72e763, push it to `origin/main`,
  preserve all unrelated untracked files, and verify local HEAD equals the
  fetched remote head.
