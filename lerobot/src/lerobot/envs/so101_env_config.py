"""
SO101 LeRobot 环境配置
"""

from dataclasses import dataclass, field
from lerobot.envs.configs import EnvConfig
from lerobot.configs.types import FeatureType, PolicyFeature
from lerobot.constants import ACTION, OBS_STATE, OBS_IMAGE, OBS_IMAGES


@EnvConfig.register_subclass("so101")
@dataclass
class SO101EnvConfig(EnvConfig):
    """SO101 环境配置"""
    task: str | None = "SO101PickPlace-v0"
    fps: int = 50
    episode_length: int = 500
    obs_type: str = "pixels_agent_pos"
    render_mode: str = "rgb_array"
    
    # SO101 特有参数
    frame_skip: int = 20
    time_step: float = 0.002
    control_freq: int = 50
    action_type: str = "joint_pos"  # joint_pos, joint_motor, end_effector_osc, end_effector_ik
    
    # 动作空间：6 (EE pose) + 5 (arm joints) + 1 (gripper) = 12
    features: dict[str, PolicyFeature] = field(
        default_factory=lambda: {
            "action": PolicyFeature(type=FeatureType.ACTION, shape=(12,)),
        }
    )
    
    features_map: dict[str, str] = field(
        default_factory=lambda: {
            "action": ACTION,
            "agent_pos": OBS_STATE,
            "top": f"{OBS_IMAGE}.top",
            "pixels/top": f"{OBS_IMAGES}.top",
        }
    )
    
    def __post_init__(self):
        """后初始化，设置特征"""
        if self.obs_type == "pixels":
            self.features["top"] = PolicyFeature(type=FeatureType.VISUAL, shape=(480, 640, 3))
        elif self.obs_type == "pixels_agent_pos":
            # 状态：ee_pos(3) + ee_quat(4) + arm_joint_qpos(5) + gripper(1) = 13
            self.features["agent_pos"] = PolicyFeature(type=FeatureType.STATE, shape=(13,))
            self.features["pixels/top"] = PolicyFeature(type=FeatureType.VISUAL, shape=(480, 640, 3))
            
    @property
    def gym_kwargs(self) -> dict:
        """Gym 关键字参数"""
        return {
            "frame_skip": self.frame_skip,
            "reward_type": "sparse",
            "orcagym_addr": "localhost:50051",
            "agent_names": ["so101"],
            "pico_ports": [],
            "time_step": self.time_step,
            "run_mode": "policy_normalized",
            "action_type": self.action_type,
            "ctrl_device": "xbox",
            "control_freq": self.control_freq,
            "sample_range": 1.0,
            "task_config_dict": {
                "task_type": "pick_place",
                "use_scene_augmentation": False,
            },
            "obs_type": self.obs_type,
            "render_mode": self.render_mode,
            "max_episode_steps": self.episode_length,
        }
