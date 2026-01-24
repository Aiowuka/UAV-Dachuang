\# 指标说明（阶段1统一口径）



本文件定义阶段1评测的三项核心指标：任务完成率、安全性、端到端闭环时延。

所有实验（不同 scene\_id、seed、algo\_id）必须按本口径输出可统计的数据，确保可对比与可复现。



---



\## 0. 术语与通用字段

一次“任务/实验运行”指：在给定 scene\_id 与 seed 下，使用某个 algo\_id 控制 N 架无人机完成一次巡检任务，并输出一行结果记录。



建议每次运行至少记录这些字段：

\- scene\_id：场景编号

\- seed：随机种子

\- algo\_id：算法编号/版本

\- N：无人机数量

\- start\_time\_ms / end\_time\_ms：任务开始/结束时间戳（毫秒）

\- time\_limit\_sec：任务时限（秒）



---



\## 1）任务完成率（%）

\### 定义

在规定时间内完成巡检目标的比例，用于衡量端到端方案有效性。



\### 单次运行 success 判定（0/1）

单次运行 success=1 当且仅当同时满足：

1\. 在 time\_limit\_sec 内完成（若场景允许超时则按场景规则处理）

2\. 达到巡检目标（例如覆盖率 >= 阈值 或 关键点全部到达等）

3\. 满足安全性约束（例如安全事件不超过阈值）



success 的阈值与规则建议写在 scene.json 的 success\_criteria 中，避免不同人各算各的。（先按照现有的，再根据实际情况改）



\### 计算公式

对同一组实验（同一 scene\_id + algo\_id，重复多次 seed 或多次 run）：

任务完成率（%） = 成功次数 / 总次数 × 100



\### 需要记录的数据

\- success（0/1）

\- total\_time\_sec（或由 start\_time/end\_time 计算）

\- time\_limit\_sec

\- 任务目标相关的数据（例如 coverage）



---



\## 2）安全性（次/任务）

\### 定义

安全性用“安全事件数/任务”衡量，可由以下三类事件组成：

\- collision\_count：碰撞次数

\- out\_of\_bounds\_count：越界次数（飞出场景边界/禁飞区）

\- min\_separation\_violation\_count：最小安全距离违规次数（任意两机距离 < min\_separation\_m）



也可以合并成：

safety\_events = collision\_count + out\_of\_bounds\_count + min\_separation\_violation\_count



\### 汇总方式

\- 单次：直接报告 safety\_events（次/任务）

\- 多次：报告均值（avg\_safety\_events），可选报告 P95（p95\_safety\_events）



\### 需要记录的数据

\- collision\_count（来自仿真碰撞信息）

\- out\_of\_bounds\_count（由位置与 area.boundary 判定）

\- min\_separation\_violation\_count（由两机距离与阈值 min\_separation\_m 判定）

\- min\_separation\_m（建议写入 scene.json）



---



\## 3）端到端闭环时延（ms）

\### 定义

从“任务下发/决策生成”到“动作开始执行或执行确认”的闭环时间，用于衡量系统实时性与工程可用性。



\### 采样建议（给实现一个明确抓手）

每次运行过程中，至少在以下环节记录时延样本：

\- t\_decision\_ms：本次规划/决策输出完成的时间

\- t\_action\_ack\_ms：动作开始执行或收到执行确认的时间

单个样本：latency\_ms = t\_action\_ack\_ms - t\_decision\_ms



\### 汇总指标

\- mean\_latency\_ms：该次运行的平均闭环时延

\- p95\_latency\_ms：该次运行的 95 分位时延（P95 的含义是 95% 的样本值不超过该阈值）\[web:350]\[web:361]



\### 需要记录的数据

\- latency\_ms\_list（或直接记录 mean\_latency\_ms 与 p95\_latency\_ms）

\- 样本数 sample\_count（可选，便于排查统计是否可靠）



---



\## 推荐的 results.csv 字段（最小集合）

\- scene\_id, seed, algo\_id, N

\- success, total\_time\_sec

\- collision\_count, out\_of\_bounds\_count, min\_separation\_violation\_count, safety\_events

\- mean\_latency\_ms, p95\_latency\_ms



