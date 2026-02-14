import numpy as np
import json
import math
import os
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class SceneConfig:
    """场景配置类（目前没强用到，可以保留）"""
    scene_id: str
    boundary: List[List[float]]
    cell_size_m: float
    altitude_z: float
    speed_mps: float
    start_positions: List[List[float]]
    obstacles: List[List[float]] = None  # 障碍物位置


class PotentialField:
    """人工势场类 - 完整版"""
    def __init__(self, maxspeed: float = 3.0):
        self.position = np.array([0.0, 0.0], dtype=float)
        self.velocity = np.array([0.0, 0.0], dtype=float)
        self.acceleration = np.array([0.0, 0.0], dtype=float)
        self.maxspeed = maxspeed
        
        # 势场参数
        self.repdistance = 15.0  # 排斥距离
        self.eta = 10.0          # 排斥增益
        self.k = 2               # 排斥指数
        self.att_gain = 1.0      # 吸引增益
        
    def urep(self, obstacles: List[np.ndarray]) -> np.ndarray:
        """排斥势场"""
        repulsive_force = np.zeros(2, dtype=float)
        
        for obstacle in obstacles:
            delta = self.position - obstacle
            distance = np.linalg.norm(delta)
            
            if distance <= self.repdistance and distance > 0.1:
                # 排斥力方向：远离障碍物
                repulsive_dir = delta / distance
                # 排斥力大小：1/r - 1/r0
                rep_magnitude = self.eta * (1.0 / distance - 1.0 / self.repdistance) ** self.k
                repulsive_force += repulsive_dir * rep_magnitude
        
        return repulsive_force
    
    def uatt(self, goal: np.ndarray) -> np.ndarray:
        """吸引势场"""
        delta = goal - self.position
        distance = np.linalg.norm(delta)
        
        if distance > 0:
            att_dir = delta / distance
            att_magnitude = self.att_gain * distance  # 线性吸引
            return att_dir * att_magnitude
        return np.zeros(2)
    
    def update(self, dt: float = 0.1):
        """动力学更新"""
        # 总加速度（这里直接用 self.acceleration）
        self.velocity += self.acceleration * dt
        
        # 限速
        speed = np.linalg.norm(self.velocity)
        if speed > self.maxspeed:
            self.velocity = self.velocity / speed * self.maxspeed
        
        # 位置更新
        self.position += self.velocity * dt
        
        # 重置加速度
        self.acceleration *= 0.0


class UAVCoveragePlanner:
    """无人机覆盖规划器 - 完整版"""
    
    def __init__(self, scene_json: Dict[str, Any]):
        self.scene = scene_json
        self._parse_config()
        
        # 网格初始化（完全由 JSON 决定）
        self.grid_h = int(self.height / self.cell_size)
        self.grid_w = int(self.width / self.cell_size)
        self.covered_grid = np.zeros((self.grid_h, self.grid_w), dtype=bool)
        
        print(f"🚁 初始化完成: {self.scene_id}")
        print(f"📏 区域: {self.width:.1f}m × {self.height:.1f}m ({self.grid_w}×{self.grid_h}格)")
    
    def _parse_config(self):
        """解析场景配置：所有参数都从 JSON 读取，不写死数字"""
        planner = self.scene["planner"]
        self.scene_id = self.scene["common"]["scene_id"]
        
        # 区域信息
        boundary = np.array(planner["area"]["boundary"], dtype=float)
        self.width = float(np.max(boundary[:, 0]) - np.min(boundary[:, 0]))
        self.height = float(np.max(boundary[:, 1]) - np.min(boundary[:, 1]))
        self.cell_size = float(planner["area"]["cell_size_m"])
        
        # 运动参数
        self.altitude = float(planner["motion"]["altitude_z"])
        self.speed = float(planner["motion"]["speed_mps"])
        self.start_pos = np.array(planner["start_positions"][0]["xyz"], dtype=float)
        
        # 障碍物（如果有）
        self.obstacles = []
        if "obstacles" in planner and planner["obstacles"]:
            for obs in planner["obstacles"]:
                # 这里只取 xy
                self.obstacles.append(np.array(obs["position"][:2], dtype=float))
    
    @staticmethod
    def load_scene_config(json_path: str) -> Dict[str, Any]:
        """加载场景配置：必须给出 json_path"""
        if not json_path:
            raise ValueError("必须传入场景 JSON 路径，例如 'scene_01_obstacle.json' 或 'scene_runtime.json'")
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"找不到场景文件: {json_path}")
        
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def generate_coverage_path(self) -> List[List[float]]:
        """生成完整覆盖路径"""
        path: List[List[float]] = []
        
        print("🌾 阶段1: 基础Lawnmower扫描...")
        lawnmower_path = self._lawnmower_scan()
        path.extend(lawnmower_path)
        self._update_coverage(lawnmower_path)
        
        coverage = self._get_coverage_ratio()
        print(f"   扫描后覆盖率: {coverage:.1%}")
        
        print("🧲 阶段2: 势场补漏...")
        pf_path = self._potential_field_coverage()
        path.extend(pf_path)
        self._update_coverage(pf_path)
        
        final_coverage = self._get_coverage_ratio()
        print(f"✅ 最终覆盖率: {final_coverage:.1%}")
        
        return path
    
    def _lawnmower_scan(self) -> List[List[float]]:
        """之字形扫描（基于 JSON 区域尺寸和 cell_size）"""
        path: List[List[float]] = []
        current_y = self.cell_size / 2.0  # 居中扫描
        direction = 1
        boundary_margin = self.cell_size
        
        while current_y < self.height - boundary_margin:
            if direction == 1:  # 左→右
                x_start, x_end, x_step = boundary_margin, self.width - boundary_margin, self.cell_size
            else:  # 右→左
                x_start, x_end, x_step = self.width - boundary_margin, boundary_margin, -self.cell_size
            
            for x in np.arange(x_start, x_end, x_step):
                path.append([float(x), float(current_y), float(self.altitude)])
            
            current_y += self.cell_size
            direction *= -1
        
        return path
    
    def _potential_field_coverage(self, max_iter: int = 1000) -> List[List[float]]:
        """势场补漏"""
        pf = PotentialField(self.speed)
        pf.position = self.start_pos[:2].copy()
        
        path: List[List[float]] = []
        iter_count = 0
        
        while iter_count < max_iter:
            # 找到最近未覆盖格子中心
            target = self._find_nearest_uncovered(pf.position)
            if target is None:
                break
            
            pf.acceleration = np.zeros(2, dtype=float)
            
            # 吸引 + 排斥
            att = pf.uatt(target)
            repulsive = pf.urep(self.obstacles)
            pf.acceleration += att - repulsive
            
            # 边界约束
            boundary_force = self._boundary_repulsion(pf.position)
            pf.acceleration -= boundary_force
            
            pf.update(dt=0.1)
            path.append([float(pf.position[0]), float(pf.position[1]), float(self.altitude)])
            
            iter_count += 1
        
        return path
    
    def _find_nearest_uncovered(self, current_pos: np.ndarray) -> np.ndarray:
        """找到最近未覆盖格子中心"""
        min_dist = float("inf")
        best_center = None
        
        for i in range(self.grid_h):
            for j in range(self.grid_w):
                if not self.covered_grid[i, j]:
                    center = np.array(
                        [
                            j * self.cell_size + self.cell_size / 2.0,
                            i * self.cell_size + self.cell_size / 2.0,
                        ],
                        dtype=float,
                    )
                    dist = np.linalg.norm(center - current_pos)
                    if dist < min_dist:
                        min_dist = dist
                        best_center = center
        
        return best_center
    
    def _boundary_repulsion(self, pos: np.ndarray) -> np.ndarray:
        """边界排斥力"""
        force = np.zeros(2, dtype=float)
        margin = self.cell_size * 2.0
        
        # 四边界排斥
        if pos[0] < margin:
            force[0] += 10.0 * (margin - pos[0])
        if pos[0] > self.width - margin:
            force[0] -= 10.0 * (pos[0] - (self.width - margin))
        if pos[1] < margin:
            force[1] += 10.0 * (margin - pos[1])
        if pos[1] > self.height - margin:
            force[1] -= 10.0 * (pos[1] - (self.height - margin))
        
        return force
    
    def _update_coverage(self, path: List[List[float]]):
        """更新覆盖栅格"""
        for point in path:
            grid_x = int(point[0] / self.cell_size)
            grid_y = int(point[1] / self.cell_size)
            if 0 <= grid_x < self.grid_w and 0 <= grid_y < self.grid_h:
                self.covered_grid[grid_y, grid_x] = True
    
    def _get_coverage_ratio(self) -> float:
        """获取覆盖率"""
        return float(np.sum(self.covered_grid) / (self.grid_h * self.grid_w))
    
    def calculate_metrics(self, path: List[List[float]]) -> Dict[str, float]:
        """计算性能指标"""
        self._update_coverage(path)
        
        # 路径长度
        path_array = np.array(path, dtype=float)
        if len(path_array) > 1:
            distances = np.linalg.norm(np.diff(path_array[:, :2], axis=0), axis=1)
            path_length = float(np.sum(distances))
        else:
            path_length = 0.0
        
        # 时间
        time_sec = path_length / self.speed if self.speed > 0 else 0.0
        
        return {
            "coverage_ratio": float(self._get_coverage_ratio()),
            "path_length_m": path_length,
            "estimated_time_sec": time_sec,
            "path_points": len(path),
            "total_cells": self.grid_h * self.grid_w,
            "covered_cells": int(np.sum(self.covered_grid)),
        }


def baseline_partition_lawnmower_v2(scene_path: str,
                                    output_dir: str) -> Dict[str, Any]:
    """完整版主函数：scene_path 指向场景 JSON，output_dir 指定结果输出文件夹"""
    # 加载配置
    scene_config = UAVCoveragePlanner.load_scene_config(scene_path)
    
    # 创建规划器
    planner = UAVCoveragePlanner(scene_config)
    
    # 生成路径
    path = planner.generate_coverage_path()
    
    # 计算指标
    metrics = planner.calculate_metrics(path)
    
    # 结果
    result = {
        "algo_id": "baseline_partition_lawnmower_v2",
        "status": "SUCCESS" if metrics["coverage_ratio"] >= 0.95 else "FAILED",
        "scene_id": planner.scene_id,
        **metrics,
        "vehicle_name": "Drone1",
        "config": {
            "cell_size": planner.cell_size,
            "speed": planner.speed,
            "altitude": planner.altitude,
        },
        "path": path[:1000] if len(path) > 1000 else path,  # 限制输出长度
    }
    
    # 确保输出目录存在，并写入对应目录
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "plan_result_v2.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("🎯 规划完成!")
    print(f"✅ 状态: {result['status']}")
    print(f"📊 覆盖率: {metrics['coverage_ratio']:.1%}")
    print(f"⏱️  预计时间: {metrics['estimated_time_sec']:.0f}s ({metrics['estimated_time_sec']/60:.1f}min)")
    print(f"📈 路径长度: {metrics['path_length_m']:.0f}m")
    print(f"🔢 路径点数: {metrics['path_points']:,}")
    print(f"💾 结果保存: {output_file}")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    # 示例：一个场景
    scene_path = r"D:\大创无人机集群\UAV-Dachuang\runs\20260203_scene_06_rect_empty_BATCH_s0_k5\run_004_s1004\scene_runtime.json"
    output_dir = r"D:\大创无人机集群\UAV-Dachuang\runs\20260203_scene_06_rect_empty_BATCH_s0_k5\run_004_s1004"
    result = baseline_partition_lawnmower_v2(scene_path, output_dir)
