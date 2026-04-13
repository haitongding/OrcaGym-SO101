"""
SO101 机器人配置（用于 OrcaGym 仿真）
"""

from dataclasses import dataclass, field
from lerobot.cameras import CameraConfig
from lerobot.robots.config import RobotConfig


@RobotConfig.register_subclass("so101_sim")
@dataclass
class SO101SimConfig(RobotConfig):
    """SO101 仿真机器人配置"""
    
    # OrcaGym 服务器地址
    orcagym_addr: str = "localhost:50051"
    
    # SO101 XML 模型路径
    xml_path: str = "/home/dht/SO-ARM100-main/Simulation/SO101/so101_new_calib.xml"
    
    # 仿真参数
    time_step: float = 0.002
    frame_skip: int = 20
    
    # 控制参数
    control_freq: int = 50
    action_type: str = "joint_pos"  # joint_pos, end_effector_osc
    
    # 相机配置
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
    
    # 是否使用度数（兼容性）
    use_degrees: bool = False
