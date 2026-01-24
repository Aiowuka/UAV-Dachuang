flowchart LR

&nbsp; S\[场景确定<br/>(SCENES)] -->|scene.json| R\[Runner]



&nbsp; R -->|scene dict| P\[算法<br/>(Planner)]

&nbsp; R -->|scene dict + run\_dir| E\[执行<br/>(Executor)]

&nbsp; R -->|success\_criteria + run\_dir| D\[数据处理<br/>(Evaluator)]



&nbsp; P -->|plan：航点列表| E

&nbsp; E -->|logs：states/events/latency| D

&nbsp; D -->|results.csv / summary.csv| T\[输出表<br/>(outputs/\_tables)]



