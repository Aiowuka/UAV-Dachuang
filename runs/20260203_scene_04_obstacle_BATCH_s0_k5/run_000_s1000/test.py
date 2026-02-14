import json              # 解析 JSON
import random            # 临时生成一些示意坐标
import matplotlib.pyplot as plt  # 最基础的 2D 可视化库

JSON_PATH = "scene_runtime.json"

def main():
    # 1. 读取 JSON 文件
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)   # data 是一个 dict

    # 2. 提取我们关心的基础信息
    common = data.get("common", {})
    run_id = common.get("run_id", "")
    N = common.get("N", 0)

    world = common.get("world", {})
    origin = world.get("origin", [0.0, 0.0, 0.0])  # [x0, y0, z0]
    x0, y0, z0 = origin

    print(f"run_id: {run_id}")
    print(f"N: {N}")
    print(f"world origin: {origin}")

    # 3. 这里“假装”有 N 个 agent/机器人，
    #    为了演示，我们先随机在原点附近生成 N 个点坐标（真实项目里应从 JSON 中真实读取）
    agents = []
    for i in range(N):
        # 随机偏移一点位置，构造示意点
        dx = random.uniform(-10, 10)
        dy = random.uniform(-10, 10)
        agents.append((x0 + dx, y0 + dy))

    # 4. 为了可视化，拆分成 x、y 列表
    xs = [p[0] for p in agents]
    ys = [p[1] for p in agents]

    # 5. 开始画图：原点 + N 个点
    plt.figure(figsize=(6, 6))

    # 原点画成一个红色的十字
    plt.scatter([x0], [y0], c="red", marker="x", s=100, label="origin")

    # N 个 agent 画成蓝点
    plt.scatter(xs, ys, c="blue", marker="o", label="agents")

    # 6. 美化一下坐标轴和标题
    plt.axhline(0, color="gray", linewidth=0.5)
    plt.axvline(0, color="gray", linewidth=0.5)
    plt.gca().set_aspect("equal", adjustable="box")

    plt.xlabel("X (meter)")
    plt.ylabel("Y (meter)")
    plt.title(f"Scene layout (run_id={run_id})")
    plt.legend()
    plt.grid(True)

    # 7. 显示图形
    plt.show()

if __name__ == "__main__":
    main()
