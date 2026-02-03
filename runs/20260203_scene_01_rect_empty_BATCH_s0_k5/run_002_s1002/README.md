# Workspace

本目录为一次 run 的工作区。

- plan/: 规划(Planner)
- execute/: 执行(Executor)
- data_processing/: 数据处理

统一配置快照：请读取本目录下 scene_runtime.json。

## 本 run 的随机输入
- 种子：common.seed
- 起点（已扰动后的最终值）：planner.start_positions（原始起点：planner.start_positions_nominal）
- 风场（恒定 NED, m/s）：executor.wind.ned_mps（Executor 侧用 AirSim simSetWind() 应用）
