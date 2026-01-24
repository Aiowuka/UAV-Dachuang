\# 场景文件说明（scene.json）



本项目的场景以 JSON 文件描述，位于 scenes/ 目录。

场景文件是“输入协议”，任何人修改字段名/含义必须先提 Issue/PR 并同步更新本文档。



\## 坐标系与单位（全局约定）

\- frame: NED（North-East-Down）

&nbsp; - x: North（向北为正）

&nbsp; - y: East（向东为正）

&nbsp; - z: Down（向下为正；飞到空中时 z 通常为负）

\- unit: meter（米）

\- angle: degree（度）

说明：AirSim API 默认采用 NED 坐标系与 SI 单位，控制与状态读取均使用该约定。



\## scene.json 顶层字段解释

\- scene\_id：场景唯一编号（用于输出目录、results.csv对齐）

\- seed：随机种子（保证同一 scene\_id+seed 可复现）

\- world：世界坐标约定（frame/unit/origin）

\- mission：任务配置（任务类型、无人机数量、飞行高度、速度、时限等）

\- area：覆盖区域定义

&nbsp; - boundary：外边界多边形（二维点数组 \[x,y]）

&nbsp; - holes：孔洞/禁飞区域（多边形数组）

&nbsp; - cell\_size\_m：覆盖率计算用网格大小

\- obstacles：障碍物列表（可选；阶段1可先少量或为空）

\- start\_positions：每架无人机初始位置与朝向

\- success\_criteria：success 判定阈值（时限/覆盖率/安全事件/时延等）

\- output：输出与记录设置（algo\_id、采样频率等）



\## success\_criteria 说明（与指标一致）

单次运行 success=1 当且仅当同时满足：

\- total\_time\_sec <= time\_limit\_sec（如果 require\_finish\_within\_time=true）

\- coverage >= min\_coverage\_ratio（覆盖任务）

\- 安全约束满足：collision/out\_of\_bounds/separation\_violation 不超过阈值或 safety\_events\_total 不超过阈值

\- （可选）latency 满足：mean/p95 不超过阈值（当 require\_latency\_check=true）



