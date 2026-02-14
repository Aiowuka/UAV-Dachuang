import numpy as np
import math
import random

class PotentialField:
    def __init__(self):
        self.position = np.array([0, 0], dtype=float)
        self.velocity = np.array([0, 0], dtype=float)
        self.acceleration = np.array([0, 0], dtype=float)
        self.maxspeed = 10
        self.repdistance = 10
        self.eta = 10
        self.k = 4

    # 计算斥力，参数为需要参与计算的目标点，目标点可以是1个，也可以是多个，类型是numpy数组
    def Urep(self, *args):
        repulsive = np.array([0, 0], dtype=float)
        for point in args:
            distance = np.linalg.norm(self.position - point)
            rep = 0
            if distance <= self.repdistance:
                repulsive = point - self.position
                temp = (1 / (distance - self.repdistance)) - (1 / self.repdistance)
                rep = self.eta * pow(temp, self.k)
                # 归一化并设置模长
                if np.linalg.norm(repulsive) > 0:
                    repulsive = repulsive / np.linalg.norm(repulsive) * rep
            self.acceleration -= repulsive
        return repulsive

    # 计算引力，参数为需要参与计算的目标点，目标点可以是1个，也可以是多个，类型是numpy数组
    def Uatt(self, *args):
        attractive = np.array([0, 0], dtype=float)
        for point in args:
            # 检查point是否是字符串，如果是，将其转换为numpy数组
            if isinstance(point, str):
                point = point.split()
                point = np.array(point, dtype=float)
            # 计算当前位置到目标点的向量
            attractive = point - self.position
            # 计算向量的模长（距离）
            distance = np.linalg.norm(attractive)
            # 计算引力大小，与距离的平方成正比，再乘以 0.5
            attractive_force = 0.5 * distance ** 2
            # 设置引力向量的模长为计算得到的引力大小
            if np.linalg.norm(attractive) > 0:
                attractive = attractive / np.linalg.norm(attractive) * attractive_force
            self.acceleration += attractive
        return attractive

    def update(self):
        self.velocity += self.acceleration
        speed = np.linalg.norm(self.velocity)
        if speed > self.maxspeed:
            self.velocity = self.velocity / speed * self.maxspeed
        self.position += self.velocity
        self.acceleration *= 0