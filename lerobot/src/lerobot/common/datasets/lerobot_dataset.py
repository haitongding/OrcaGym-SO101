# 兼容垫片：将 openpi 使用的旧路径 lerobot.common.datasets.lerobot_dataset
# 重定向到 lerobot v0.3.4 的新路径 lerobot.datasets.lerobot_dataset
from lerobot.datasets.lerobot_dataset import *  # noqa: F401, F403
from lerobot.datasets.lerobot_dataset import LeRobotDataset, LeRobotDatasetMetadata  # noqa: F401
