# metric.md（阶段1统一口径｜sim 时间）

本文件定义阶段1评测的三项核心指标：任务完成率、安全性、端到端闭环时延。  
所有实验（不同 scene_id、seed、algo_id）必须按本口径交付**原始数据（raw）**与**指标（metrics）**，确保可对比与可复现。[file:190]

---

## 0. 术语与通用约定

### 0.1 一次任务/一次 run
一次“任务/实验运行（run）”指：在给定 `scene_id` 与 `seed` 下，使用某个 `algo_id` 控制 `N` 架无人机完成一次任务，并输出一套文件产物与一行指标记录。[file:190]

### 0.2 时间基准（阶段1固定：sim）
`states.csv` 与 `events.jsonl` 的 `t_ms` 必须使用 **sim（仿真时间，毫秒）**。`scene_runtime.json` 中必须声明：

- `time_base: "sim"`

**sim 时间来源（实现约定）**：以 AirSim `getMultirotorState().timestamp` 为准（文档描述为纳秒级时间戳），统一换算为：

- `t_ms = timestamp_ns / 1e6`（保留整数或小数均可，但全项目必须一致）。[web:36]

> 注意：AirSim 在暂停/不同 clock 类型下 timestamp 行为可能存在差异，因此阶段1建议避免在 run 中使用 pause/continue 等会扰动仿真时钟的操作，或在使用时做一致性验证。[web:295]

### 0.3 坐标与单位
- 坐标系：以 `world.frame` 为准（示例为 NED）。[file:190]
- 单位：以 `world.unit` 为准（示例为 meter）。[file:190]

---

## 1. 交付物（每次 run 一个目录）

目录命名：`runs/{run_id}/`

### 1.1 必交付（raw + metrics）
1) `scene_runtime.json`：本次 run 的配置快照（输入 + 阈值 + 元信息）。[file:190]  
2) `states.csv`：多机状态时序（原始数据）。[file:190]  
3) `events.jsonl`：任务/安全/时延事件（原始数据，JSONL/NDJSON）。[web:262]  
4) `metrics.csv`：本次 run 的指标汇总（数据处理侧产出，一次 run 一行）。[file:190]

### 1.2 推荐交付
- `waypoints.json`：Planner 输出航点（用于复现与排障：计划 vs 实际）。[file:190]

---

## 2. 原始数据（raw）规范

### 2.1 scene_runtime.json（配置快照）
用途：保证指标计算口径统一，阈值不靠口头约定。[file:190]

必须包含（直接来自 scene.json 或 Runner 补全）：
- `run_id`
- `scene_id, seed`
- `world`（frame/unit/origin）[file:190]
- `mission`（task_type, N, vehicle_names, altitude_z, speed_mps, time_limit_sec, takeoff, landing）[file:190]
- `area`（boundary, holes, cell_size_m）[file:190]
- `success_criteria`（min_coverage_ratio, safety.*, latency.*）[file:190]
- `output`（algo_id, record_states_hz）[file:190]
- `time_base: "sim"`
- `sim_time_source: "airsim_state_timestamp_ns"`（建议固定写入，避免歧义）。[web:36]

可选但建议：
- `start_time_ms, end_time_ms`（sim 时间）
- `code_version/git_commit, planner_version, executor_version`

约束：
- `scene_runtime.json` **不包含** states/events/图像等大体量原始数据，只保存配置快照与元信息。[file:190]

### 2.2 states.csv（状态时序）
采样频率：
- 按 `output.record_states_hz` 记录（示例为 5Hz）。[file:190]

每行含义：
- 一行 = 某 `vehicle_name` 在某 `t_ms` 的状态。[file:190]

必须字段（最小集合）：
- `run_id, scene_id, algo_id, vehicle_name`
- `t_ms`（sim 时间，由 `timestamp_ns/1e6` 换算）。[web:36]
- `x, y, z`（NED, meter）。[file:190]

强烈建议字段（用于开始运动检测/排障/扩展指标）：
- `vx, vy, vz`
- `qx, qy, qz, qw`

多无人机对齐约定：
- 允许不同无人机 `t_ms` 轻微不齐；涉及两两距离时，按“同时间窗匹配”对齐（默认容忍窗口 `sync_eps_ms = 100ms`）。[file:190]

### 2.3 events.jsonl（事件与时延打点）
格式：
- JSONL/NDJSON：每行一个 JSON 事件对象。[web:262]

通用字段（每个事件必须有）：
- `run_id, scene_id, algo_id, t_ms, event_type`

其中 `t_ms` 为 sim 时间（由 `timestamp_ns/1e6` 换算）。[web:36]

#### 2.3.1 任务生命周期事件
- `MISSION_START`：字段 `N`。[file:190]
- `MISSION_END`：字段 `status`（SUCCESS/FAIL/TIMEOUT/ABORT），可选 `reason`。[file:190]

#### 2.3.2 安全事件（用于计数）
- `COLLISION`：字段 `vehicle_name`。[file:190]
- `OUT_OF_BOUNDS`：字段 `vehicle_name, x, y`。[file:190]
- `SEPARATION_VIOLATION`：字段 `vehicle_a, vehicle_b, distance_m`。[file:190]

安全事件计数去抖口径（阶段1固定）：
- 对 `OUT_OF_BOUNDS` 与 `SEPARATION_VIOLATION`，采用“进入违规状态记 1 次，恢复后再次进入再记 1 次”的规则（避免采样频率影响次数）。[file:190]

#### 2.3.3 时延打点事件（阶段1口径：开始运动确认）
- `DECISION_DONE`：字段 `decision_id`（本轮规划/决策输出完成）。[file:190]
- `ACTION_ACK_START_MOVING`：字段 `decision_id, vehicle_name`（检测到该机开始运动）。[file:190]

开始运动判定规则（阶段1默认参数）：
- `v_start_eps = 0.2 m/s`，`K = 2`：当速度模长 ||v|| 连续 K 帧 > v_start_eps 即认为开始运动并打点。[file:190]
- 速度可来自 `states.csv` 的 (vx,vy,vz)；若未记录速度，可用相邻位置差分估计速度，但必须保证全实验一致。[file:190]

---

## 3. 指标（metrics）规范（数据处理侧统一产出）

### 3.1 metrics.csv（每次 run 一行）
最小字段集合（必须）：
- `scene_id, seed, algo_id, N`
- `success, total_time_sec, final_coverage_ratio`
- `collision_count, out_of_bounds_count, min_separation_violation_count, safety_events`
- `mean_latency_ms, p95_latency_ms, latency_sample_count` [web:246]

---

## 4. 三项核心指标口径（阶段1固定）

### 4.1 任务完成率（%）
#### 定义
在规定时间内完成巡检目标的比例，用于衡量端到端方案有效性。[file:190]

#### 单次 run 的 success 判定（0/1）
单次 run `success=1` 当且仅当同时满足：[file:190]
1. `total_time_sec <= success_criteria.time_limit_sec` 且 `require_finish_within_time=true`。[file:190]
2. 达到任务目标：覆盖任务满足 `final_coverage_ratio >= success_criteria.min_coverage_ratio`（示例为 0.90）。[file:190]
3. 满足安全阈值：`safety_events <= success_criteria.safety.max_safety_events_total`（示例为 0）。[file:190]

#### 完成率计算
对同一组实验（同一 scene_id + algo_id，重复多次 seed/run）：  
任务完成率（%） = 成功次数 / 总次数 × 100。[file:190]

#### 覆盖率计算建议（阶段1统一抓手）
- 用 `area.cell_size_m` 对 `area.boundary` 栅格化；轨迹点命中某 cell 视为覆盖该 cell；覆盖率=覆盖 cell 数 / 区域内 cell 总数（holes 为空则忽略洞）。[file:190]

---

### 4.2 安全性（次/任务）
#### 定义
安全性以“安全事件数/任务”衡量，由三类事件组成：[file:190]
- `collision_count`：碰撞次数
- `out_of_bounds_count`：越界次数（飞出 area.boundary 或禁飞区）
- `min_separation_violation_count`：最小安全距离违规次数（任意两机距离 < `min_separation_m`）

合并指标：
- `safety_events = collision_count + out_of_bounds_count + min_separation_violation_count`。[file:190]

#### 多无人机 separation 判定（阶段1固定）
- 在同一时间窗（`sync_eps_ms`）内，对所有无人机两两计算距离；若最小距离 < `success_criteria.safety.min_separation_m`（示例 2.0m），触发一次 `SEPARATION_VIOLATION`，并记录最小距离对应的 (vehicle_a, vehicle_b)。[file:190]
- 按 2.3.2 的去抖规则计数得到 `min_separation_violation_count`。[file:190]

---

### 4.3 端到端闭环时延（ms）
#### 定义（阶段1固定：开始运动确认）
从“本次规划/决策输出完成（DECISION_DONE）”到“检测到无人机开始运动（ACTION_ACK_START_MOVING）”的时间差。[file:190]

#### 单样本定义
对同一 `decision_id` 与 `vehicle_name`：  
`latency_ms = ACTION_ACK_START_MOVING.t_ms - DECISION_DONE.t_ms`。[file:190]

#### 单次 run 汇总
- `mean_latency_ms`：该 run 所有 latency 样本均值。[file:190]
- `p95_latency_ms`：该 run 所有 latency 样本的 95 分位数（95% 样本值不超过该阈值）。[web:246]
- `latency_sample_count`：样本数（用于可靠性检查）。[file:190]

样本集合口径（多无人机固定）：
- 一个 `decision_id` 可能对应多台无人机；每台无人机各产生一个 latency 样本；本次 run 的 mean/P95 在“所有样本（跨 decision_id × 跨无人机）”上统计。[file:190]

---

## 5. 备注：谁负责产出什么

- Runner/Executor（仿真侧）负责交付：`scene_runtime.json + states.csv + events.jsonl (+ waypoints.json)`。[file:190]
- 数据处理侧负责交付：`metrics.csv`（并可汇总多 run 为总表）。[file:190]

