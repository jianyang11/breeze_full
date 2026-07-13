# PU LOCO v3 Internal Candidate Pool Report

- Scope: internal simulated LOCO only; no formal held-out LOCO test is touched.
- API usage: 0 calls for morphology_idw/morphology_nearest; accepted v1 LLM recipes are reused as structural templates.
- Output root: `/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze/runs/pu_loco_v4_s2_morphology_2026-07-13_smoke`
- Generation/calibration data: only train-bearing windows from the three internal training conditions per fold.
- Pseudo held-out data use: metadata only for rpm/torque/load kinematics and morphology prediction target.

| candidate | pseudo heldout | nearest | accepted slots | kept healthy | kept OR | kept IR | status |
|---|---|---|---:|---:|---:|---:|---|
| morphology_idw | N09_M07_F10 | N15_M07_F10 | 3/6 | 1 | 5 | 1 | pool_short |
| morphology_idw | N15_M01_F10 | N15_M07_F10 | 6/6 | 6 | 7 | 10 | pool_short |
| morphology_idw | N15_M07_F04 | N15_M07_F10 | 5/6 | 5 | 3 | 7 | pool_short |
| morphology_idw | N15_M07_F10 | N09_M07_F10 | 4/6 | 5 | 5 | 3 | pool_short |
| morphology_nearest | N09_M07_F10 | N15_M07_F10 | 3/6 | 3 | 5 | 0 | pool_short |
| morphology_nearest | N15_M01_F10 | N15_M07_F10 | 5/6 | 5 | 7 | 5 | pool_short |
| morphology_nearest | N15_M07_F04 | N15_M07_F10 | 6/6 | 3 | 10 | 10 | pool_short |
| morphology_nearest | N15_M07_F10 | N09_M07_F10 | 4/6 | 6 | 5 | 5 | pool_short |
