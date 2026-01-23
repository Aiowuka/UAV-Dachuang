# UAV-Dachuang

\# AirSim 多机基线（阶段1）



本仓库用于在 AirSim 中建立“可复现、可对比”的基线：支持单机/三机运行固定场景集，并输出 results.csv 与 summary.csv，作为后续算法对照基准。



\## 目标（阶段1）

\- 单机：能稳定完成一次任务并输出结果（Case2）

\- 三机：三机可并行运行并输出每机/总体指标（Case3）

\- 场景：提供 6 个可复现实验场景（Case4）

\- 跑批：一键跑完 6 场景 × K 次并汇总（Case5）



\## 目录结构

\- docs/      环境、场景、指标说明

\- scenes/    scene\_01..06.json 场景配置

\- scripts/   运行入口（单机/多机/跑批）

\- outputs/   每次运行输出（不提交到 Git）



\## 环境要求

\- AirSim：1.18.1

\- Unreal Engine：4.27.2

\- Visual Studio：2022 Community（需安装 Desktop Development with C++）

\- Python：3.14

\- 操作系统：Windows 10/11（推荐）



\## 快速开始（第一次跑通：3 步）

1\. 启动 Unreal 场景（保持仿真窗口打开）

2\. 配好 AirSim settings.json（Drone1/Drone2/Drone3 命名一致，见 docs/ENV.md）

3\. 运行一次单机：

&nbsp;  python scripts/run\_single.py --scene scenes/scene\_01.json --seed 0



运行完成后应看到：

\- outputs/ 下生成一个新的运行目录

\- outputs/.../results.csv 中新增 1 行记录（字段齐全）



\## 常用命令

\### 单机（Case2）

python scripts/run\_single.py --scene scenes/scene\_01.json --seed 0



\### 三机（Case3）

python scripts/run\_multi.py --scene scenes/scene\_01.json --seed 0



\### 一键跑批（Case5）

python scripts/run\_all.py --scenes scenes/ --k 10 --seed 0



\## 输出说明（results / summary）

\### results.csv（逐次明细）

至少包含字段：

scene\_id, algo\_id, seed, N, per\_drone\_time, total\_time, collision, coverage, overlap, success



\### summary.csv（汇总）

按（场景×算法）汇总：完成率、平均耗时、碰撞次数、覆盖率等（详见 docs/METRICS.md）



\## 场景说明（简要）

\- scene\_01：\_\_\_\_\_\_

\- scene\_02：\_\_\_\_\_\_

\- ...

\- scene\_06：\_\_\_\_\_\_

复现规则与参数说明见 docs/SCENES.md（场景模板不可随意改）。



\## 常见问题（遇到就看这里）

\- 连接不上 AirSim：检查 Unreal 是否已启动、settings.json 是否生效

\- 只出现一架无人机：检查 Drone1/2/3 命名是否一致

\- 运行卡住：把 outputs/ 对应运行目录打包发 Issue/群里



\## 协作约定（很重要）

\- main 分支保持“随时可跑”；新功能用分支提 PR 合并

\- outputs/ 不提交到 Git（已在 .gitignore 中忽略）



