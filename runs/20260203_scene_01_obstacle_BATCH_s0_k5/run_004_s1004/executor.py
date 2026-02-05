import airsim
import time
import os
import csv
import json
import threading
from concurrent.futures import ThreadPoolExecutor

# ============================ 1. 日志记录类 ============================
class LocalLogger:
    def __init__(self, target_dir):
        self.target_dir = target_dir
        self.lock = threading.Lock()
        
        # 定义三个日志文件路径
        self.paths = {
            "states": os.path.join(target_dir, "states.csv"),
            "events": os.path.join(target_dir, "events.jsonl"),
            "latency": os.path.join(target_dir, "latency.csv")
        }
        self._init_files()

    def _init_files(self):
        """初始化CSV表头"""
        with self.lock:
            # 状态日志：记录物理信息
            with open(self.paths["states"], 'w', newline='') as f:
                csv.writer(f).writerow(['t', 'vehicle', 'x', 'y', 'z', 'vx', 'vy', 'vz'])
            
            # 时延日志：记录指令决策到响应完成的时间
            with open(self.paths["latency"], 'w', newline='') as f:
                csv.writer(f).writerow(['t_decision_ms', 't_ack_ms', 'latency_ms'])

    def log_state(self, name, state):
        p = state.kinematics_estimated.position
        v = state.kinematics_estimated.linear_velocity
        with self.lock:
            with open(self.paths["states"], 'a', newline='') as f:
                csv.writer(f).writerow([time.time(), name, p.x_val, p.y_val, p.z_val, v.x_val, v.y_val, v.z_val])

    def log_event(self, event_type, name, details=None):
        event = {"t": time.time(), "type": event_type, "v": name, "d": details or {}}
        with self.lock:
            with open(self.paths["events"], 'a') as f:
                f.write(json.dumps(event) + "\n")

    def log_latency(self, t_dec, t_ack):
        """记录时延采样"""
        with self.lock:
            with open(self.paths["latency"], 'a', newline='') as f:
                csv.writer(f).writerow([t_dec, t_ack, t_ack - t_dec])

# ============================ 2. 控制逻辑 ============================
def fly_mission(name, waypoints, speed, logger):
    # 为每架飞机建立独立Client连接
    client = airsim.MultirotorClient()
    client.confirmConnection()
    
    try:
        # 起飞准备
        client.enableApiControl(True, name)
        client.armDisarm(True, name)
        client.takeoffAsync(vehicle_name=name).join()
        logger.log_event("takeoff", name)

        for i, wp in enumerate(waypoints):
            # 记录指令下达时刻 (毫秒)
            t_decision = time.time() * 1000
            
            # 修正高度：确保Z为负值（向上飞）
            z = -abs(wp[2]) if wp[2] > 0 else wp[2]
            print(f"[{name}] 目标点 {i}: {wp[0], wp[1], z}")
            
            # 发送异步指令
            future = client.moveToPositionAsync(wp[0], wp[1], z, speed, vehicle_name=name)
            
            # 循环采样：直到到达航点或发生碰撞
            while not future._is_done:
                state = client.getMultirotorState(vehicle_name=name)
                logger.log_state(name, state)
                
                # 碰撞监测
                col = client.simGetCollisionInfo(vehicle_name=name)
                if col.has_collided:
                    logger.log_event("collision", name, {"target": col.object_name})
                    print(f"[{name}] ‼️ 发生碰撞，任务中断")
                    return
                time.sleep(0.1)
            
            # 指令完成时刻
            t_ack = time.time() * 1000
            logger.log_latency(t_decision, t_ack)
            logger.log_event("waypoint_reached", name, {"index": i})
                
        # 降落
        client.landAsync(vehicle_name=name).join()
        logger.log_event("landed", name)
        
    except Exception as e:
        logger.log_event("error", name, {"msg": str(e)})
    finally:
        client.armDisarm(False, name)
        client.enableApiControl(False, name)

# ============================ 3. 主启动入口 ============================
if __name__ == "__main__":
    # 脚本所在文件夹即为实验目录
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 场景同学提供的输入
    scene_file = os.path.join(cur_dir, "scene_runtime.json")
    # 算法同学提供的输入
    plan_file = os.path.join(cur_dir, "planned_waypoints.json")

    # 1. 检查场景配置
    if not os.path.exists(scene_file):
        print(f"❌ 错误：在当前目录找不到 scene_runtime.json")
    else:
        with open(scene_file, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        
        # 2. 加载或模拟航点
        if not os.path.exists(plan_file):
            print("⚠️ 算法文件未就绪，使用默认测试路径...")
            plan_data = {
                "Drone1": [[10, 0, -5], [10, 10, -5], [0, 0, -5]],
                "Drone2": [[0, 10, -5], [10, 10, -5], [0, 0, -5]]
            }
        else:
            with open(plan_file, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)

        # 3. 准备开始
        logger = LocalLogger(cur_dir)
        vehicles = scene_data.get("vehicle_names", ["Drone1"])
        speed = scene_data.get("default_speed", 5)

        print(f"🚀 实验启动中。场景: {scene_data.get('scene_name', 'Default')}")
        
        # 并发执行
        with ThreadPoolExecutor(max_workers=len(vehicles)) as executor:
            for v_name in vehicles:
                if v_name in plan_data:
                    executor.submit(fly_mission, v_name, plan_data[v_name], speed, logger)
        
        print(f"\n✅ 实验完成！")
        print(f"📂 日志已生成至: {cur_dir}")