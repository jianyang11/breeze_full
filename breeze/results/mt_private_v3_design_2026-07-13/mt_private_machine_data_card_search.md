# Private machine-tool data-card search — v3 evidence record

**Frozen date:** 2026-07-13 (before v3 validation)  
**Scope:** local, read-only evidence search; no waveform-derived machine parameters.

## Search record

The following local locations were enumerated and searched for the Chinese and
English terms `主轴`, `转速`, `rpm`, `进给`, `feed`, `丝杠`, `导程`, `传动比`,
`传感器`, `安装位置`, `电流通道`, `采样率`, `工序`, `machine tool`, and
`sampling rate`:

1. the complete workspace rooted at
   `/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci`, excluding
   VCS, virtual environments, generated run directories, and processed arrays;
2. the original senior-project directory `合成数据sci/`, including `data/`,
   `data_hecheng/`, `data_llm/`, and `code/`;
3. project manuscript, supplementary, response, and source-code text files.

An additional owner-supplied location was then inspected:
`/Users/jianyang/Desktop/code/时序检测/tmp_content/毕设时序预测/`.
Its `datasets/` directory contains 30 same-schema CSVs, ten per class, with
file IDs `1,2,4,5,7,8,10,11,13,14`.  Three spot SHA-256 comparisons establish
byte-identical provenance between this source copy and the repository copy:
`1_1`, `1_2`, and `3_7`.  Its separate `datasets_test/` directory contains
only `1_2`, `2_1`, and `3_1`; each is byte-identical to the same-named file in
`datasets/`, so it is a duplicate view and not an independent evaluation set.

The original project directory contains CSV signal files, generated CSVs,
Baibu-yun transfer sidecars, and three Python scripts.  It contains no README,
lab log, parameter table, machine manual, acquisition configuration, or
file-to-operation manifest.  The located MechaForge manuscripts describe the
Paderborn bearing experiments rather than this private machine-tool recording,
so they are explicitly excluded as evidence for this data card.

The additional time-series project contains the source CSVs, code assigning
prefixes `1/2/3` to normal/lead-screw/base-imbalance labels, a generic 566-page
CNC maintenance textbook, and RAG answers derived from that textbook.  The
book and generated answers are generic reference material, not a record of
this acquisition.  They are therefore excluded as machine-specific evidence.

## Field-level data card

| Field | Status | Direct evidence | Permitted v3 use |
|---|---|---|---|
| Class mapping | available | Owner-confirmed v1 record: `1=normal_machining`, `2=lead_screw_anomaly`, `3=base_imbalance`; not inferred from waveform/PDF | class labels only |
| Raw file identity | available | 21 CSVs follow `<class>_<file>[_pre].csv`; inventory reports 5 train and 2 formal files per class | fixed split/file provenance only |
| Signal columns | available | Raw CSV header is exactly `X,Y,Z,Current`; confirmed in original `data/` and repository `breeze/data_mt/` copies | four-channel schema only |
| Sampling rate | available | v1 inventory and `breeze/src/data_mt.py` record 4000 Hz | sample-time conversion and normalized-spectrum reporting only |
| Windowing | available | v1/v2 source fixes 2048 samples, stride 1024 | reproducible evaluation only |
| Spindle speed | unavailable | no local parameter record found | no spindle/shaft/1x rule |
| Feed speed | unavailable | no local parameter record found | no feed or screw-order rule |
| Lead/pitch or transmission ratio | unavailable | no local parameter record found | no lead-screw order rule |
| Machine model and axis/drive geometry | unavailable | no local parameter record found | no geometry-derived inference |
| Sensor type and mounting position | unavailable | `X/Y/Z` names alone do not establish sensor type, orientation, or mounting | no acceleration-direction/mounting claim |
| Current-channel semantics | unavailable | header `Current` supplies a name, not phase, scaling, sensor, or control-loop meaning | generic fourth-channel statistics only |
| Per-file running operation/process | unavailable | filenames encode class and acquisition ID only; no factual process map found | no process-conditioned result or order claim |
| Independent run count | partially available | seven files/class exist, but only five are designated training and the original project has no acquisition log proving their independence | report file-level grouping; do not claim independent-run calibration guarantee |
| Extra source files `11/13/14` | unassigned | same-schema source copy includes these three IDs per class; no split manifest, acquisition log, or independence evidence found | excluded from frozen v3 split until owner assigns their role |

## Consequence

This record does **not** unlock any component-specific physics gate.  v3 may
use only generic, normalized four-channel statistics and train-supported
class-conditional synthesis.  It must not call a normalized spectral band a
spindle, screw, imbalance, or current-control frequency.  A signed factual
response containing the unavailable fields is still required before the
private data can support a physical-admission claim.  A separate owner decision
is also required before IDs `11/13/14` can be used as training, external
testing, or any other experimental partition.
