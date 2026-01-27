# -*- coding: utf-8 -*-
# 文件名建议：tools/runner_init_gui_batch.pyw（Windows 双击运行无黑框）

import json
import re
import shutil
import random
import math
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


def _safe_name(s: str) -> str:
    s = str(s).strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^0-9A-Za-z._-]+", "_", s)
    return s or "scene"


def load_scene(scene_path: Path) -> dict:
    with scene_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def create_workspace(base_dir: Path) -> None:
    (base_dir / "plan").mkdir(parents=True, exist_ok=True)
    (base_dir / "execute").mkdir(parents=True, exist_ok=True)
    (base_dir / "data_processing").mkdir(parents=True, exist_ok=True)

    readme = base_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Workspace\n\n"
            "本目录为一次 run 的工作区。\n\n"
            "- plan/: 规划(Planner)\n"
            "- execute/: 执行(Executor)\n"
            "- data_processing/: 数据处理\n\n"
            "统一配置快照：请读取本目录下 scene_runtime.json。\n\n"
            "## 本 run 的随机输入\n"
            "- 种子：common.seed\n"
            "- 起点（已扰动后的最终值）：planner.start_positions（原始起点：planner.start_positions_nominal）\n"
            "- 风场（恒定 NED, m/s）：executor.wind.ned_mps（Executor 侧用 AirSim simSetWind() 应用）\n",
            encoding="utf-8",
        )



def pick(obj, keys, default=None):
    cur = obj
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def pick_any(obj, paths, default=None):
    for keys in paths:
        v = pick(obj, keys, default=None)
        if v is not None:
            return v
    return default


def _rng_state_jsonable():
    # random.getstate() 返回 tuple，json 不支持 tuple：递归转 list
    def _to_list(x):
        if isinstance(x, tuple):
            return [_to_list(i) for i in x]
        if isinstance(x, list):
            return [_to_list(i) for i in x]
        return x
    return _to_list(random.getstate())


def _apply_start_jitter(start_positions, seed, xy_uniform_m=0.5, yaw_uniform_deg=0.0):
    rng = random.Random(seed)

    out = []
    draws = []
    for sp in start_positions:
        xyz = sp.get("xyz", [0.0, 0.0, 0.0])
        yaw = sp.get("yaw_deg", 0.0)

        dx = rng.uniform(-xy_uniform_m, xy_uniform_m)
        dy = rng.uniform(-xy_uniform_m, xy_uniform_m)
        dyaw = rng.uniform(-yaw_uniform_deg, yaw_uniform_deg) if yaw_uniform_deg and yaw_uniform_deg > 0 else 0.0

        new_sp = dict(sp)
        new_sp["xyz"] = [xyz[0] + dx, xyz[1] + dy, xyz[2]]
        new_sp["yaw_deg"] = yaw + dyaw

        out.append(new_sp)
        draws.append({"vehicle_name": sp.get("vehicle_name", ""), "dx": dx, "dy": dy, "dyaw_deg": dyaw})

    return out, draws


def _sample_constant_wind_ned(seed, speed_min=0.0, speed_max=5.0, allow_wz=False, wz_max_abs=0.0):
    rng = random.Random(seed)

    speed = rng.uniform(speed_min, speed_max)
    theta = rng.uniform(0.0, 2.0 * math.pi)
    wx = speed * math.cos(theta)
    wy = speed * math.sin(theta)

    wz = 0.0
    if allow_wz and wz_max_abs and wz_max_abs > 0:
        wz = rng.uniform(-wz_max_abs, wz_max_abs)

    return [wx, wy, wz], {"speed": speed, "theta_rad": theta}


def build_scene_runtime_partitioned(scene: dict, scene_path: Path, run_id: str, run_seed: int,
                                   start_xy_jitter_m: float, start_yaw_jitter_deg: float,
                                   wind_speed_min: float, wind_speed_max: float,
                                   allow_wz: bool, wz_max_abs: float) -> dict:
    scene_id = scene.get("scene_id", scene_path.stem)

    mission = scene.get("mission", {}) or {}
    output = scene.get("output", {}) or {}
    world = scene.get("world", {}) or {}
    area = scene.get("area", {}) or {}
    obstacles = scene.get("obstacles", []) or []
    start_positions_nominal = scene.get("start_positions", []) or []
    success_criteria = scene.get("success_criteria", {}) or {}

    N = mission.get("N", None)
    algo_id = output.get("algo_id", None)

    # record dt
    dt_sec = None
    record_hz = output.get("record_states_hz", None)
    try:
        record_hz = float(record_hz)
        if record_hz > 0:
            dt_sec = 1.0 / record_hz
    except Exception:
        pass

    # 约定：同一 run_seed 派生各子系统 seed，互不干扰
    seed_start = int(run_seed) + 10000
    seed_wind = int(run_seed) + 20000

    # 1) 起点扰动：生成“最终起点”，并记录抽样值（可追溯/可复现）
    start_positions_final, start_draws = _apply_start_jitter(
        start_positions_nominal,
        seed=seed_start,
        xy_uniform_m=float(start_xy_jitter_m),
        yaw_uniform_deg=float(start_yaw_jitter_deg),
    )

    # 2) 风场：生成恒定 NED 风向量
    wind_ned, wind_draws = _sample_constant_wind_ned(
        seed=seed_wind,
        speed_min=float(wind_speed_min),
        speed_max=float(wind_speed_max),
        allow_wz=bool(allow_wz),
        wz_max_abs=float(wz_max_abs),
    )

    # 3) 记录一个 python random 的 state（用于调试/极限复现）；注意这是 runner 自己的，不要求下游依赖
    random.seed(run_seed)
    py_rng_state = _rng_state_jsonable()

    runtime = {
        "common": {
            "run_id": run_id,
            "scene_id": scene_id,
            "seed": int(run_seed),
            "N": N,
            "algo_id": algo_id,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source_scene_file": str(scene_path.resolve()),
            "time_base": "sim",
            "sim_time_source": "airsim_state_timestamp_ns",
            "world": world,

            "rng": {
                "master_seed": int(run_seed),
                "streams": {
                    "start_seed": int(seed_start),
                    "wind_seed": int(seed_wind)
                },
                "python_random": {
                    "seed": int(run_seed),
                    "state": py_rng_state
                }
            }
        },

        "planner": {
            "task_type": mission.get("task_type", None),
            "area": area,
            "obstacles": obstacles,

            "start_positions_nominal": start_positions_nominal,
            "start_jitter": {
                "enabled": True,
                "xy_uniform_m": float(start_xy_jitter_m),
                "yaw_uniform_deg": float(start_yaw_jitter_deg),
                "seed": int(seed_start),
                "draws": start_draws
            },
            # 注意：planner/executor 都应使用这个“最终起点”
            "start_positions": start_positions_final,

            "motion": {
                "altitude_z": mission.get("altitude_z", None),
                "speed_mps": mission.get("speed_mps", None),
                "time_limit_sec": mission.get("time_limit_sec", None),
            },
            "safety": {
                "min_separation_m": (success_criteria.get("safety", {}) or {}).get("min_separation_m", None)
            }
        },

        "executor": {
            "vehicle_names": mission.get("vehicle_names", []),
            "takeoff": mission.get("takeoff", {}),
            "landing": mission.get("landing", {}),
            "log_level": output.get("log_level", None),
            "record_states_hz": output.get("record_states_hz", None),
            "dt_sec": dt_sec,

            "wind": {
                "mode": "constant",
                "ned_mps": wind_ned,
                "seed": int(seed_wind),
                "draws": wind_draws
            }
        },

        "data_processing": {
            "success_criteria": success_criteria,
            "area_for_metrics": area,
        },

        "source_scene": scene
    }

    return runtime


def compute_seeds(base_seed: int, k: int, strategy: str, offset: int, seeds_list):
    if strategy == "list":
        if not isinstance(seeds_list, list) or len(seeds_list) < k:
            raise ValueError("seed_strategy=list 时，需要 batch.seeds 至少提供 k 个整数")
        return [int(x) for x in seeds_list[:k]]

    # 默认 offset
    return [int(base_seed) + int(offset) + i for i in range(int(k))]


def run_gui():
    root = tk.Tk()
    root.title("Runner Init (Batch Runs)")
    root.geometry("720x420")
    root.resizable(False, False)

    scene_path_var = tk.StringVar(value="")
    out_dir_var = tk.StringVar(value=str(Path.cwd()))
    run_id_preview_var = tk.StringVar(value="（未生成）")

    # batch
    k_var = tk.IntVar(value=5)
    seed_offset_var = tk.IntVar(value=1000)

    # start jitter
    start_xy_jitter_var = tk.DoubleVar(value=0.5)
    start_yaw_jitter_var = tk.DoubleVar(value=0.0)

    # wind
    wind_min_var = tk.DoubleVar(value=0.0)
    wind_max_var = tk.DoubleVar(value=5.0)
    allow_wz_var = tk.IntVar(value=0)
    wz_max_var = tk.DoubleVar(value=0.0)

    def pick_scene():
        p = filedialog.askopenfilename(
            title="选择 scene.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if p:
            scene_path_var.set(p)
            _update_preview()

    def pick_out_dir():
        d = filedialog.askdirectory(title="选择输出目录（生成 batch workspace）")
        if d:
            out_dir_var.set(d)

    def _update_preview():
        try:
            sp = scene_path_var.get().strip()
            if not sp:
                run_id_preview_var.set("（未生成）")
                return
            scene = load_scene(Path(sp))
            scene_id = _safe_name(scene.get("scene_id", Path(sp).stem))
            seed = scene.get("seed", "na")
            date_str = datetime.now().strftime("%Y%m%d")
            run_id_preview_var.set(f"{date_str}_{scene_id}_BATCH_s{seed}_k{k_var.get()}")
        except Exception:
            run_id_preview_var.set("（scene.json 读取失败）")

    def do_generate():
        scene_path = scene_path_var.get().strip()
        out_dir = out_dir_var.get().strip()
        if not scene_path:
            messagebox.showerror("错误", "请先选择 scene.json 文件。")
            return
        if not out_dir:
            messagebox.showerror("错误", "请先选择输出目录。")
            return

        scene_path = Path(scene_path).resolve()
        out_dir = Path(out_dir).resolve()

        try:
            scene = load_scene(scene_path)
        except Exception as e:
            messagebox.showerror("错误", f"读取 JSON 失败：{e}")
            return

        scene_id = _safe_name(scene.get("scene_id", scene_path.stem))
        base_seed = int(scene.get("seed", 0))
        date_str = datetime.now().strftime("%Y%m%d")

        # batch plan from scene.json (optional) with GUI override
        batch = scene.get("batch", {}) or {}
        k = int(batch.get("k", k_var.get()))
        strategy = str(batch.get("seed_strategy", "offset"))
        offset = int(batch.get("seed_offset", seed_offset_var.get()))
        seeds_list = batch.get("seeds", None)

        seeds = compute_seeds(base_seed=base_seed, k=k, strategy=strategy, offset=offset, seeds_list=seeds_list)

        batch_id = f"{date_str}_{scene_id}_BATCH_s{base_seed}_k{k}"
        batch_dir = out_dir / batch_id
        if batch_dir.exists():
            ok = messagebox.askyesno("确认覆盖", f"目录已存在：\n{batch_dir}\n\n是否删除并重新生成？")
            if not ok:
                return
            shutil.rmtree(batch_dir)
        batch_dir.mkdir(parents=True, exist_ok=True)

        # write batch plan
        batch_plan = {
            "batch_id": batch_id,
            "scene_id": scene_id,
            "base_seed": base_seed,
            "k": k,
            "seed_strategy": strategy,
            "seed_offset": offset,
            "seeds": seeds,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source_scene_file": str(scene_path.resolve())
        }
        write_json(batch_dir / "batch_plan.json", batch_plan)

        # generate each run
        for i, run_seed in enumerate(seeds):
            run_name = f"run_{i:03d}_s{run_seed}"
            run_dir = batch_dir / run_name
            create_workspace(run_dir)

            run_id = f"{date_str}_{scene_id}_s{run_seed}_r{i:03d}"

            scene_runtime = build_scene_runtime_partitioned(
                scene=scene,
                scene_path=scene_path,
                run_id=run_id,
                run_seed=run_seed,
                start_xy_jitter_m=float(start_xy_jitter_var.get()),
                start_yaw_jitter_deg=float(start_yaw_jitter_var.get()),
                wind_speed_min=float(wind_min_var.get()),
                wind_speed_max=float(wind_max_var.get()),
                allow_wz=bool(allow_wz_var.get()),
                wz_max_abs=float(wz_max_var.get()),
            )
            write_json(run_dir / "scene_runtime.json", scene_runtime)

        messagebox.showinfo(
            "完成",
            "批量生成成功！\n\n"
            f"batch_dir:\n{batch_dir}\n\n"
            "包含：batch_plan.json + run_xxx 子目录（每个都有 scene_runtime.json）"
        )

    # UI layout
    tk.Label(root, text="scene.json:").place(x=20, y=20)
    tk.Entry(root, textvariable=scene_path_var, width=78).place(x=110, y=20)
    tk.Button(root, text="选择文件", command=pick_scene).place(x=635, y=16)

    tk.Label(root, text="输出目录:").place(x=20, y=60)
    tk.Entry(root, textvariable=out_dir_var, width=78).place(x=110, y=60)
    tk.Button(root, text="选择目录", command=pick_out_dir).place(x=635, y=56)

    tk.Label(root, text="batch预览:").place(x=20, y=100)
    tk.Entry(root, textvariable=run_id_preview_var, width=78, state="readonly").place(x=110, y=100)

    tk.Label(root, text="重复 k 次:").place(x=20, y=145)
    tk.Entry(root, textvariable=k_var, width=10).place(x=110, y=145)

    tk.Label(root, text="seed_offset:").place(x=220, y=145)
    tk.Entry(root, textvariable=seed_offset_var, width=10).place(x=310, y=145)

    tk.Label(root, text="起点抖动 xy(m):").place(x=20, y=190)
    tk.Entry(root, textvariable=start_xy_jitter_var, width=10).place(x=140, y=190)

    tk.Label(root, text="yaw(deg):").place(x=260, y=190)
    tk.Entry(root, textvariable=start_yaw_jitter_var, width=10).place(x=330, y=190)

    tk.Label(root, text="风速 min/max(m/s):").place(x=20, y=235)
    tk.Entry(root, textvariable=wind_min_var, width=10).place(x=170, y=235)
    tk.Entry(root, textvariable=wind_max_var, width=10).place(x=255, y=235)

    tk.Checkbutton(root, text="允许垂直风 wz", variable=allow_wz_var).place(x=370, y=233)
    tk.Label(root, text="wz max abs:").place(x=500, y=235)
    tk.Entry(root, textvariable=wz_max_var, width=10).place(x=590, y=235)

    tk.Button(root, text="生成 Batch Workspace", command=do_generate, width=22, height=2).place(x=265, y=300)

    root.mainloop()


if __name__ == "__main__":
    run_gui()
