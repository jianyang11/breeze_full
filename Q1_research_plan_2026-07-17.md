# BREEZE 一区科研提升方案（动态控制版）

版本：2026-07-17 v1.0  
工作目录：`breeze_full-2`  
目标：在不编造数据、不降低核心目标、不用后处理修补掩盖失败的前提下，将当前 Q2-ready 证据约束稿推进为具备一区投稿竞争力的可复现研究成果。

## 1. 当前结论

当前项目不是空白起点。仓库已经形成 21 页 CAS 稿、三套公开协议、固定配方/生成池、物理和下游结果、PU LOCO 失败链、统计校正、图表 QA 与部分可复现资产。`origin/main` 与本地 `HEAD` 在本轮开始时一致，均为 `1457ef1`。现有稿件可以作为诚实的 Q2-ready 基线，但不能据此报告“已达到一区水平”。

一区升级的决定性工作不是继续美化已有图，也不是扩大措辞，而是补齐四条目前缺失的证据链：

1. 一个具有明确有限样本口径的源组级联合校准算法；
2. 与训练式生成器、参数估计器和黑盒优化器的公平强对照；
3. 多独立生成池、多分类器和层级统计推断；
4. 能从公开 release 复放 CWRU/Berkeley 关键波形、配方和证书的复现包。

### 1.1 第一性原理控制

“一区”是外部评价，不是可直接优化的科学变量。本项目真正要优化的是：一个可证伪主张在独立数据上经受强对照后仍成立，并且第三方能从原始来源复放证据。由此反推五条硬约束：

1. **证据极限由独立实验单元决定**：重复切窗、增加同一 pool 的 classifier seed 或延长 epoch，不能替代新的 source、entity、regime 或生成 pool；正式统计的一级重复必须与主张的独立性口径一致。
2. **每个方法假设必须可检查**：交换性、metadata 可用性、物理模型适用域、renderer 方程、优化预算和损失权重分别进入 assumption/parameter ledger；没有理论、物理、pilot 或公平预算依据的参数不得进入 formal config。
3. **先定义否证，再运行实验**：每个主张先写最小支持证据、最强可行反例、失败阈值和失败后回到哪一层重构。outer-test 只回答预注册问题，不能兼任调参集。
4. **按“质疑—删除—简化—加速—自动化”审查流程**：删除的是不改变可证伪结论的冗余工作，而不是原始数据、负结果、审计记录或复现资产；分片、并行和自动化只能在数据合同与统计口径稳定后进行。
5. **失败只能触发原理性重构**：若核心假设被否证，应更换一般算法、补充真正独立证据或收窄未经支持的主张；不得移动阈值、选择性汇报、给失败样本加后处理或用较弱基线制造“成功”。

每次正式 run 前保存 claim→assumption→measurement→test→decision 的冻结映射；每轮失败后更新 decision log 与 `todos.md`，明确旧假设为何失效和新方案新增了什么可证伪信息。

## 2. 研究问题与可证伪假设

### RQ1：风险校准是否比经验多 gate 分位数更可靠？

在不访问 outer-test 的条件下，源组级联合 nonconformity 是否能达到预注册的真实源组拒绝风险，并在不同 source/regime 上保持可解释的 coverage？

**H1**：在满足交换性和最小独立组数的协议上，BREEZE-RC 的真实 calibration/test source pass rate 落入预注册的 exact binomial 置信界；窗口级 legacy gate 不作为保证基线，只报告经验行为。

**否证条件**：任一正式 cell 的 source 数不足以形成非空有限样本界，或 untouched real test sources 出现系统性失败。此时不得调整阈值；应增加独立源、重新选择有足够源的数据集，或回到算法设计阶段。

### RQ2：LLM 是否真的优于同配方空间的非 LLM 搜索？

在 renderer、verifier、candidate/proposal budget 和 synthetic count 完全相同的条件下，比较 random legal recipe、engineer rule、train-stat estimator、Bayesian/TPE optimizer、LLM open-loop、LLM feedback 和 BREEZE-RC。

**H2**：LLM feedback/BREEZE-RC 在至少两个正式公开协议上，相对最强非 LLM recipe source 提高可接受样本容量或下游 Macro-F1，且 pool-level 置信区间排除零；不能只胜过 random/rule。

**否证条件**：最强 estimator/optimizer 与 LLM 等效或更优。此时不改 comparator，不隐藏结果；回到 prompt 信息、反馈目标和 recipe parameterization 做原理性迭代，再生成新的独立开发池，正式测试保持不可读。

### RQ3：收益是否独立于分类器和生成池随机性？

**H3**：方法排序在至少三种时序诊断骨干和一个非深度强基线上方向稳定；以独立 pool 为一级重复的主分析仍支持结论。

**否证条件**：收益只在一个 CNN 或一个 pool 出现。此时不能用更多同池训练 seed 修复显著性，必须诊断表示依赖或生成池不稳定性。

### RQ4：物理 admission 是否具有 gate 外有效性？

**H4**：通过证书的 pool 在预注册、未进入 gate 的物理诊断上，相对强非结构化基线更接近 outer-train real reference，并且没有更高的复制/高相关风险；对 rule 的非劣/优势按指标分别陈述。

**否证条件**：只在 gate 内指标变好，gate 外指标恶化或 two-sample discriminator 轻易区分。此时不添加临时 gate，回到 feature/physics plugin 的一般算法设计。

## 3. 方法：BREEZE-RC

### 3.1 数据合同

每个窗口必须拥有：

```text
X, y, source_id, entity_id, regime_id, time_order,
sensor_schema, physics_metadata, outer_split, reference_calibration_split,
raw_source_hash, preprocessing_hash
```

`source_id` 是不能跨 split 的独立采集源；`entity_id` 是可用时的物理轴承/刀具/试验对象；`regime_id` 是由实验元数据声明的工况。禁止将窗口编号冒充 source，禁止从标签或候选频谱推断缺失机械参数。

### 3.2 三层证书

`Layer 0 — legality` 检查形状、长度、通道、单位、采样率、NaN/Inf、常量、重复哈希和元数据完整性。

`Layer 1/2 — generic signal support` 使用 outer-train reference source 建立源均衡的时域、归一化 PSD-CDF、多通道结构和多样性参考。每个 block 先转成 reference empirical rank，再以预注册的最大值或其他单调联合函数形成一个 joint nonconformity。联合函数在看 calibration/test 分数前冻结。

`Layer 3 — physics plugin` 只在 metadata requirement 满足时计算机制特定证据。`BearingPhysicsPlugin` 使用几何、RPM/不确定区间、vibration schema 和可选电流拓扑；`MillingPhysicsPlugin` 使用 spindle/tooth/process metadata。返回值只能是 `pass`、`fail` 或 `unavailable`。`unavailable` 阻断物理 claim，不会变成 generic pass。

### 3.3 风险口径

在每个声明 cell 内，以 source 为单位聚合 nonconformity。reference source 只建立特征参考，calibration source 只确定 exact empirical order statistic。目标覆盖率、置信度、组聚合函数和 cell 合并规则在 outer-test 解封前预注册。

可声明的保证仅是：在交换性假设成立的 source/regime 范围内，对真实 source group 的 marginal rejection/coverage 风险进行有限样本控制。不可声明：合成波形是物理真值、每个工况条件覆盖、分布漂移下仍有同样保证、或 verifier pass 等于诊断正确。

若闭环反馈按前轮分数自适应提出候选，证书同时保存选择轮次和候选集合。主稿将区分“候选集合含至少一个 admissible 项”的集合级问题与“单个最终样本通过 deterministic verifier”的样本级事实，避免混用 SCOPE-Gen 的保证。

### 3.4 独立诊断账本

正式 gate 冻结前预注册至少一组不参与 admission 的诊断：

- gate 未使用的谱峰/阶次或循环平稳指标；
- source-grouped real-vs-synthetic two-sample AUROC；
- byte/hash、NRMSE、最大归一化互相关与最近源分布；
- class-wise RMS、kurtosis、crest、skew、PSD-W1、MMD 和 envelope alignment；
- source/regime 分层失败率。

任何不利结果保留。不得因留出诊断失败而将它临时加入 gate 后在同一 test pool 上重报。

### 3.5 闭环与无修补原则

LLM 只生成结构化 recipe；renderer 用固定方程和显式 seed 生成波形；verifier 只报告、拒绝和产生有界反馈。任何 failed waveform 都不能通过滤波、幅值回缩、频谱搬移、局部替换或标签重写进入 accepted pool。方法改进必须发生在通用 recipe schema、feedback policy、calibration algorithm 或 renderer model 层，并重新走开发/正式协议。

## 4. 数据集与正式协议

### 4.1 主协议

1. **PU/Paderborn**：保留当前 `N09_M07_F10` 文件级协议作为 legacy bridge；新协议优先建立 bearing/file source-aware reference-calibration-test。外部条件使用冻结 LOCO 失败链，不重复调 test。
2. **CWRU 12 kHz drive-end**：within-load0 与 source-load0→loads1–3；明确 source MAT file、故障尺寸、载荷、RPM 和几何。不得写成跨机器或跨 specimen。
3. **Berkeley milling**：case/run-disjoint 二分类；定位为 exemplar-background simulation augmentation，不写成纯生成物理真值。

### 4.2 候选扩展协议

MU-TCM 只有在完成 experiment/insert-edge split、active-cut manifest、同步与数据卡后进入正式方法验证。DIRG、IMS、XJTU、HIT、JUST 不因本地已有数据就自动进入论文。选择新数据集的标准是：独立 source 足够、物理元数据完整、许可/引用清晰、协议与主问题匹配，而不是“数据集数量更多”。

### 4.3 split 验收

- raw source hash 与窗口 manifest 一一对应；
- source/entity 不跨 outer split；
- reference/calibration source 不重叠；
- overlap window 不能跨 split；
- scaler、feature reference、gate threshold、generator fitting 和超参选择均只读 outer-train；
- formal outer-test 由 loader guard 阻断，直到 preregistration hash 冻结；
- 随机标签、重复窗口、时间反转和错误 metadata 负控能触发预期失败。

## 5. 对照方法

### 5.1 配方来源对照

| 方法 | 作用 | 公平性约束 |
|---|---|---|
| random legal | 宽范围合法随机配方 | 同 schema、proposal budget、renderer、seed ledger |
| engineer rule | 专家模板与 train-supported 参数范围 | 不读 test；参数来源逐项引用 |
| train-stat estimator | 用 train reference 估计相同 recipe 字段 | 同自由度；不接触 classifier/test |
| Bayesian/TPE optimizer | 在相同 recipe space 最小化 train-only joint score | 相同 proposal budget；避免把更多查询当算法优势 |
| LLM K=0 | 无反馈配方 | 模型/参数/上下文/请求日志完整 |
| LLM K=1..3 | 有界结构化反馈 | 每轮候选完整保留；不修改波形 |
| BREEZE-RC | LLM feedback + risk-calibrated certificate | 只有算法冻结后才能用于正式池 |

### 5.2 波形增强强基线

- real-only；
- jitter、scaling、crop/permutation、mixup（只保留适合标签和物理时序的版本）；
- faithful TimeGAN/conditional GAN；
- faithful 1-D DDPM；若资源允许且官方实现可核验，增加 ReF-DDPM/DDPM-LFR 或等价 2025 强扩散；
- 现有 `ConvTimeGAN` 与简化 DDPM 在文献忠实性审计前只以实现名报告，不能冒充原论文完整方法。

所有生成器分别在 `full outer-train` 和 `few-shot only` 两种训练边界下报告。超参来自原论文/官方实现或 train-only inner validation；不得按 outer-test 结果挑配置。

### 5.3 诊断骨干

至少包括紧凑 1-D CNN、ResNet1D、TCN 或 InceptionTime 中三种，以及 MiniROCKET/ROCKET 或固定特征 SVM/RF 中一种。每个骨干使用相同 few-shot subset、synthetic pool、初始化 seed family 和训练预算。模型容量、参数量、epoch、早停规则和失败 run 都写入结构化日志。

### 5.4 非生成跨工况对照

对跨 load/condition 结果增加至少一个不生成波形的域泛化/物理特征强基线，以回答“为什么不直接做 representation/domain generalization”。若无法忠实复现 PI-SSDG，选择有公开实现且协议兼容的方法，并明确不是 PI-SSDG 的替代结果。

## 6. 实验矩阵与分阶段放量

### 6.1 Stage A：算法与数据小样本验证

每个数据集只用 2–5 个 source、每类 5 个候选和 1 个训练 seed 验证接口、shape、日志、checkpoint、负控和图。smoke 的数值永远不进入论文。

验收后再跑每类 20 个候选、2 个独立 pool、2 个分类器 seed 的 pilot。pilot 只用于估计运行成本、失败率、Monte Carlo 方差和预注册 SESOI，不用于正式显著性。

### 6.2 Stage B：校准冻结

先冻结 DatasetProtocol、data card、source split、feature schema、joint score、coverage/confidence、plugin metadata requirement、负控和 artifact hash。然后只用 real reference/calibration sources 生成 calibration report。只有真实源 coverage 和负控通过，才可生成正式 synthetic pool。

### 6.3 Stage C：独立生成池

正式目标为每个主要 recipe source 至少 10 个独立 pool。每个 pool 的 provider request、model ID、temperature、top-p、provider seed 可用性、prompt hash、local renderer seed、proposal/accepted count、token/cost 和失败原因写入 append-only ledger。

LLM API 是有成本的外部操作。在正式调用前提交精确预算和请求用户授权。已有 1231/3000 审计用量不得静默改变。若余额不足，不减少独立 pool 目标来制造单池结论；应申请预算、改用用户授权的本地模型，或暂停该 gate。

### 6.4 Stage D：下游全量

主 shot 依据三个协议现有设置保留 PU/CWRU `{5,10,25}`、Berkeley `{2,5,10}`。是否增加 50/100 shot 由 pilot 中 real-only 学习曲线与论文问题决定，并在 test 解封前冻结。每个 pool 内使用固定的 10–20 个 paired subset/classifier seeds；pool 为一级重复，seed 为嵌套重复。

### 6.5 Stage E：强基线与消融

训练式生成器先完成一整个 cell，按实测 wall time 和磁盘增长估算正式矩阵。不能因为慢而减少 epoch 或只挑成功 seed。若训练不稳定，报告失败率和 loss dynamics，按原协议继续或从干净 preregistration 版本重启。

消融至少包括：legacy marginal gates、joint generic only、physics plugin only、no feedback、K=0/1/2/3、无 exemplar、无 class statistics、无 physics metadata、risk calibration、以及同预算 optimizer。每个消融只改变一个组件。

## 7. 统计设计

### 7.1 推断层级

```text
dataset/protocol
  └── independently generated pool
       └── few-shot subset and classifier initialization seed
            └── metric (Accuracy, Macro-F1, Balanced Accuracy, per-class F1)
```

主效应先在每个 pool 内对 paired seeds 求方法差，再以 pool-level 差为统计样本。使用 pool-level paired permutation/randomization test 和 cluster bootstrap 95% CI；混合效应模型仅作敏感性分析。不得把 pool 内 20–40 个训练 seed 当作 20–40 个独立生成实验。

### 7.2 多重比较

每个 dataset × backbone × shot 的主 family 在 preregistration 中列出。Macro-F1 为主指标，Accuracy/Balanced Accuracy 为次指标；Holm 控制 family-wise error，global BH 只作敏感性。报告 raw effect、CI、p、adjusted decision 和失败方向，不只报星号。

### 7.3 实质效应阈值

SESOI 不在方案中任意指定。它由 Stage A pilot 的 paired Monte Carlo noise、real-only repeatability 和领域允许误差共同形成，并在 outer-test 解封前冻结。一区“通过”要求统计证据与实质效应同时满足；微小但显著的提升不能单独成为主贡献。

### 7.4 物理非劣与多目标

物理指标方向不统一，不能合成一个事后挑权重的总分。每个预注册指标独立报告相对 real-reference 的距离；必要时以 rule 为非劣基线，margin 由 real-real source variation 决定。效用、物理保真、接受容量和成本用 Pareto 图展示，不用雷达图掩盖冲突。

## 8. 长任务、日志、并行和断点续跑

### 8.1 当前阻塞

`formal_pu_v2` 已完成 TimeGAN/full-train/n_real=5 的 3 个 seed，但 runner 日志为空，最后更新时间为 2026-07-16 14:24，未形成完成报告。该目录保留为不完整开发证据，不能继续混入新的正式协议。

### 8.2 统一运行合同

每个长任务必须：

- 启动时写 immutable `run_manifest.json`、代码/数据 hash、参数、预计 cell 数；
- 至少每 60 秒写 heartbeat（当前 cell、epoch、batch、完成/总数、wall time、ETA、RSS/磁盘增长）；
- 每个 epoch 或固定 batch 原子 checkpoint；
- append-only CSV/JSONL，写后 `flush + fsync`；
- SIGTERM/SIGINT 后保存可恢复状态并标记 interrupted；
- 单 cell lock 防重复，分片任务用独立 shard root；
- 合并器严格检查唯一 key、完整 seed/pool coverage、manifest hash 和失败 ledger；
- 运行时不设置会中断科研任务的短 timeout；监控端每 1–5 分钟检查日志新鲜度、CPU 时间、文件增长和 checkpoint；
- 超过两个 heartbeat 周期无进度时先诊断 stack/IO/lock，不直接宣布失败或删除结果。

### 8.3 并行策略

先用 1/2/4 worker 的完整 smoke 测量 throughput、内存和线程过订阅，再选择 worker 数。训练库线程数与进程数联动，避免每进程占满全部核心。不同 independent pool/seed 可并行，同一 checkpoint 禁止并发写。若 Apple MPS 可用，先做 CPU/MPS 数值与恢复一致性审计；任何设备切换都使用新 formal root，不能混入已开始的 CPU protocol。

## 9. 磁盘与目录规范

当前项目约 51 GB，已经超过 50 GB 预算；系统盘可用空间约 13 GB。正式目标把工作水位降到不高于 47 GB，至少保留 3 GB 项目余量，并持续记录 `storage_ledger.csv`。

目录约定：

```text
data/                    只保留必要原始归档、许可和 source manifest
proc/                    可重建的冻结预处理数组，必须带 raw/preprocess hash
breeze/runs/q1_*/        大型 pool/checkpoint/逐候选记录（默认不入 git）
breeze/results/q1_*/     小型结构化正式结果、汇总、manifest、hash
breeze/logs/q1_*/        heartbeat、stdout/stderr、resource ledger
analysis/q1_*/           只读审计、失败报告、统计/图 QA
breeze/paper/figs/q1_*/  投稿图和 source manifest
specs/q1_*/              protocol、data card、preregistration
```

候选释放空间必须先做 hash/provenance/可恢复性审计并取得删除授权。优先候选是：MU-TCM 已解压副本（保留 4.4 GB 原始归档和精确清单后可按需流式解压）、已明确跳过的 XJTU 分卷、IMS 重复归档、可由 raw 重建的 DIRG 大型 NPZ、Python/pytest/LaTeX 缓存。不得删除唯一原始数据、冻结 formal result、API 原始记录、未发布的关键 pool 或用户现有修改。

## 10. 可视化与目视检查

每一阶段生成以下诊断图，并使用 `view_image`/PDF 渲染逐图检查：

1. 数据：source/entity/regime split Sankey/矩阵、类/工况分布、窗口重叠审计图；
2. 校准：source-level nonconformity ECDF、coverage/threshold、reference-calibration-test 分布、负控；
3. 生成：waveform、PSD、envelope/order spectrum、跨通道相干、real/synthetic population bands；
4. 运行：loss dynamics、失败率、耗时/内存/磁盘、accepted-per-proposal 曲线；
5. 主结果：pool-level paired forest、backbone × dataset × shot effect heatmap、pool variance decomposition；
6. 多目标：utility–physical distance–cost Pareto，点按 independent pool 展示；
7. 失败：PU LOCO 和任何新失败的完整 stop-chain，不做选择性展示；
8. 复现：artifact dependency graph 与 hash coverage。

所有正式图导出 PDF/SVG、600 dpi TIFF、300 dpi PNG；检查字体嵌入、字号、色盲、灰度、线宽、裁切、坐标单位和单/双栏阅读尺寸。图源只能读取冻结 CSV/JSON/NPZ，不从手抄数值生成。当前 Page 13 表格字号偏小，后续改为主文摘要表 + 补充完整表，不能用缩放到不可读解决。

## 11. 硬验收门

| Gate | 必须满足 | 失败后的合法动作 |
|---|---|---|
| G0 状态与存储 | 远端同步；工作树范围清楚；≤47 GB；所有删除可恢复/获授权 | 只做审计和清理，不启动大任务 |
| G1 数据协议 | source/entity/regime 无泄漏；outer-test loader guard；数据卡完整 | 修协议、换有足够独立源的数据集；不按窗口伪造独立性 |
| G2 算法正确 | joint calibration、plugin unavailable、负控、legacy regression 全通过 | 回到通用算法；不加局部阈值补丁 |
| G3 real-only 校准 | untouched real source coverage 达预注册界；无系统性 class/regime 失败 | 增加真实独立源或重构 score；不读 synthetic/test 调阈值 |
| G4 强基线公平 | 官方/忠实实现审计；训练完成；失败率/成本完整；同预算 | 修实现或取得算力；不以弱/未收敛基线充数 |
| G5 独立 pool 推断 | ≥10 pools；pool-level CI/检验；多分类器方向稳定 | 继续生成独立 pool 或改方法；不增加同池 seed 伪装样本量 |
| G6 一区效应 | 至少两个公开协议相对最强控制达到预注册实质效应和 multiplicity-aware 统计，另一个协议不出现未解释灾难性退化 | 回到 recipe/feedback/calibration 创新迭代；不降低对照或改主终点 |
| G7 gate 外物理证据 | 留出诊断、复制/相关性、two-sample 审计通过预注册非劣/优势条件 | 回到 physics plugin/renderer；不把失败指标加入 gate 后复测同一池 |
| G8 复现与稿件 | release manifest 可复放；claim-evidence 逐项闭合；PDF/图逐页无缺陷；作者元数据齐全 | 补包、补元数据、重编译；未闭合前不报告投稿就绪 |

只有 G0–G8 全部完成，才能在 `todos.md` 标记“一期一区目标完成”。“代码运行结束”“已有 PDF”“某个 p<0.05”都不是完成条件。

## 12. 动态调整规则

每完成一个子任务立即更新 `todos.md`：记录状态、证据路径、关键数值、失败原因和下一步。计划变化必须写 amendment，说明触发证据、未查看的 test 边界、变化是否影响统计 family 和新 hash。任何正式协议在 test 解封后不得因结果不理想改主终点、样本量、阈值或排除规则；只能冻结失败、建立全新开发/正式版本。

旧路线不通时允许改变方法，但不允许降低“一区竞争力 + 真实可复现 + 强对照 + 独立统计”的核心目标。可接受的替代包括增加独立源、采用更忠实的生成基线、重构联合 score、改进明确的 feedback policy、使用同自由度优化器做反事实对照或申请更多 API/算力。不可接受的替代包括减少 baseline、减少 epoch、隐藏失败 seed、改用窗口伪重复、删除不利指标或只改论文措辞。

## 13. 近期执行顺序

1. 冻结本方案、文献报告和置顶 todos；
2. 完成存储可恢复性审计并取得清理授权，使项目回到 ≤47 GB；
3. 审计并修复长任务 heartbeat/checkpoint/sharding，验证 formal v2 不完整状态；
4. 实现 DatasetProtocol 与 outer-test loader guard；
5. 实现 source-group joint calibration 和 generic report，先在 PU/CWRU real-only smoke；
6. 实现/迁移 `BearingPhysicsPlugin`，做 real-only/负控/legacy regression；
7. 冻结 Stage A pilot，确定独立 pool 数、SESOI、API/算力预算；
8. 经授权后生成独立 pools；
9. 完成强生成基线、多骨干、层级统计和 gate 外诊断；
10. 只有硬 gate 通过后重写主稿、重画正式图、制作 release 并做终审。
