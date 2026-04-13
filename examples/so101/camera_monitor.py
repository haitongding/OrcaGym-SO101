#!/usr/bin/env python3
"""
SO101 相机实时监控脚本

同时显示 7070（camera_head）和 7080（camera_wrist）两路相机画面。

运行步骤：
  1. 启动 OrcaSim 并运行 SO101 场景
  2. python examples/so101/camera_monitor.py

按 'q' 或 ESC 退出。
"""

import os
import sys

# ★ 必须在所有其他 import 之前设置！
# rgbd_camera.py 会 import matplotlib.pyplot，默认用 Qt 后端初始化 Qt 应用实例。
# cv2 同样需要 Qt，两者冲突会导致 cv2.namedWindow 永远阻塞。
# 强制 matplotlib 使用无 GUI 的 Agg 后端，彻底避免冲突。
os.environ.setdefault('MPLBACKEND', 'Agg')

import time
import signal
import threading
import argparse

# ── 项目根目录加入 Python 路径 ────────────────────────────────────────────
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import cv2
import numpy as np
import gymnasium as gym
from gymnasium.envs.registration import register

from orca_gym.environment.orca_gym_env import RewardType
# ★ CameraWrapper 故意不在这里 import！
# rgbd_camera.py 模块级会 import av（PyAV），av 的 ffmpeg 线程会阻塞
# cv2.namedWindow 的 Qt 初始化。必须在 cv2 窗口创建完成后再 import。
from envs.so101.so101_env import SO101Env
from envs.manipulation.dual_arm_env import ControlDevice, RunMode, ActionType

# ─────────────────────────────────────────────────────────────────────────────
# 参数配置
# ─────────────────────────────────────────────────────────────────────────────
ENV_NAME = "SO101CameraMonitor-v0"

TIME_STEP     = 0.001
FRAME_SKIP    = 20
REALTIME_STEP = TIME_STEP * FRAME_SKIP
CONTROL_FREQ  = 1 / REALTIME_STEP

SO101_XML_PATH = "/home/dht/SO-ARM100-main/Simulation/SO101/so101_new_calib.xml"

# 相机配置：名称 → WebSocket 端口
CAMERA_CONFIG = {
    "camera_head":  7070,
    "camera_wrist": 7080,
}

# begin_save_video 需要一个路径（监控模式不需要保留视频文件）
VIDEO_DUMP_PATH = "/tmp/so101_camera_monitor_dump"


# ─────────────────────────────────────────────────────────────────────────────
# 创建 SO101 环境（参考 so101_leader_teleoperation.py）
# ─────────────────────────────────────────────────────────────────────────────
def create_env(orcagym_addr: str = "localhost:50051") -> gym.Env:
    if ENV_NAME not in gym.envs.registry:
        register(
            id=ENV_NAME,
            entry_point="envs.so101.so101_env:SO101Env",
            max_episode_steps=100000,
        )

    task_config = {
        "robot_xml_path":         os.path.abspath(SO101_XML_PATH),
        "task_type":              "pick_place",
        "use_scene_augmentation": False,
    }

    env_config = {
        "frame_skip":          FRAME_SKIP,
        "reward_type":         RewardType.SPARSE,
        "orcagym_addr":        orcagym_addr,
        "agent_names":         ["so101_new_calib_usda"],
        "pico_ports":          [],
        "time_step":           TIME_STEP,
        "run_mode":            RunMode.POLICY_NORMALIZED,   # ← 不初始化任何物理硬件
        "action_type":         ActionType.JOINT_POS,
        "ctrl_device":         ControlDevice.LEADER_ARM,
        "control_freq":        CONTROL_FREQ,
        "sample_range":        0.0,
        "task_config_dict":    task_config,
        "action_step":         1,
        "camera_config":       {},
    }

    return gym.make(ENV_NAME, **env_config)


# ─────────────────────────────────────────────────────────────────────────────
# 创建并启动相机（参考 xbox_data_collection.py 的 setup_cameras）
# ─────────────────────────────────────────────────────────────────────────────
def setup_cameras(camera_config: dict) -> dict:
    # ★ 在这里才 import CameraWrapper（懒加载），保证 av 在 cv2 窗口创建后再被 import
    from orca_gym.sensor.rgbd_camera import CameraWrapper
    cameras = {}
    for name, port in camera_config.items():
        try:
            cam = CameraWrapper(name=name, port=port)
            cam.start()
            cameras[name] = cam
            print(f"✓ 相机 {name} 已连接（端口 {port}）", flush=True)
        except Exception as e:
            print(f"✗ 无法连接相机 {name}（端口 {port}）: {e}", flush=True)
    return cameras


# ─────────────────────────────────────────────────────────────────────────────
# 等待所有相机收到首帧
# ─────────────────────────────────────────────────────────────────────────────
def wait_for_cameras(cameras: dict, timeout: float = 30.0) -> None:
    print(f"\n等待相机就绪（最长 {timeout:.0f}s）...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        ready   = [n for n, c in cameras.items() if c.is_first_frame_received()]
        pending = [n for n, c in cameras.items() if not c.is_first_frame_received()]
        if not pending:
            print("✓ 所有相机已就绪")
            return
        print(f"  就绪: {ready or '(无)'}  |  等待中: {pending}", flush=True)
        time.sleep(1.0)
    print("⚠️  超时：部分相机未收到数据，继续运行（画面可能为噪声）")


# ─────────────────────────────────────────────────────────────────────────────
# 主监控循环
# ─────────────────────────────────────────────────────────────────────────────
def run_monitor(orcagym_addr: str, camera_config: dict,
                fps: float = 30.0, scale: float = 1.0) -> None:

    # ── Ctrl+C：os._exit 强杀，跳过 CameraWrapper.__del__ 无超时 join ────
    stop_event = threading.Event()

    def _sigint_handler(sig, frame):
        print("\nCtrl+C 已捕获，正在退出...", flush=True)
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        os._exit(0)

    signal.signal(signal.SIGINT, _sigint_handler)

    # ── 1. ★ 先创建 cv2 窗口（必须在 gRPC env 之前！）─────────────────────
    # gRPC 线程池启动后会阻塞 Qt/xcb 初始化，导致 cv2.namedWindow 永远卡住
    windows = {}
    for name, port in camera_config.items():
        title = f"{name}  (port {port})  |  q/ESC 退出"
        cv2.namedWindow(title, cv2.WINDOW_NORMAL)
        # 显示占位黑色帧，让窗口立即可见
        cv2.imshow(title, np.zeros((480, 640, 3), np.uint8))
        windows[name] = title
    cv2.waitKey(1)
    print("✓ 相机窗口已创建\n", flush=True)

    # ── 2. 连接 OrcaSim 并触发视频流 ─────────────────────────────────────
    print(f"正在连接 OrcaSim（{orcagym_addr}）...", flush=True)
    env = create_env(orcagym_addr)
    env.reset()
    print("✓ 环境就绪", flush=True)

    os.makedirs(VIDEO_DUMP_PATH, exist_ok=True)
    env.unwrapped.begin_save_video(VIDEO_DUMP_PATH, 0)
    print("✓ begin_save_video 已调用，视频流已启动\n", flush=True)

    # ── 3. 连接相机 ───────────────────────────────────────────────────────
    cameras = setup_cameras(camera_config)
    if not cameras:
        print("没有可用相机，退出", flush=True)
        env.close()
        return

    # ── 4. 等待首帧 ───────────────────────────────────────────────────────
    wait_for_cameras(cameras, timeout=30.0)

    interval_ms = max(1, int(1000.0 / fps))
    print(f"开始显示（FPS={fps:.0f}，缩放={scale}）  按 q 或 ESC 退出\n", flush=True)

    # ── 5. 显示循环 ───────────────────────────────────────────────────────
    try:
        while not stop_event.is_set():
            for name, cam in cameras.items():
                frame, idx = cam.get_frame(format="bgr24")
                img = frame.copy()

                # 叠加信息标签
                label = f"{name} | port:{camera_config[name]} | frame#{idx}"
                cv2.putText(img, label, (10, 32),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                            (0, 255, 0), 2, cv2.LINE_AA)

                if scale != 1.0:
                    h, w = img.shape[:2]
                    img = cv2.resize(img, (int(w * scale), int(h * scale)))

                cv2.imshow(windows[name], img)

            key = cv2.waitKey(interval_ms) & 0xFF
            if key in (ord("q"), 27):   # q 或 ESC
                print("退出键被按下", flush=True)
                stop_event.set()
                break

    finally:
        # ── 6. 清理（给 3 秒，超时直接强杀）──────────────────────────────
        cv2.destroyAllWindows()

        # 3 秒后强制退出，防止 thread.join 阻塞
        threading.Timer(3.0, lambda: os._exit(0)).start()

        for cam in cameras.values():
            cam.running = False
        for cam in cameras.values():
            if cam.thread and cam.thread.is_alive():
                cam.thread.join(timeout=2.5)

        try:
            env.unwrapped.stop_save_video()
        except Exception:
            pass
        try:
            env.close()
        except Exception:
            pass

        print("✓ 已退出", flush=True)
        os._exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SO101 相机实时监控")
    parser.add_argument("--orcagym_addr", default="localhost:50051",
                        help="OrcaGym gRPC 地址（默认 localhost:50051）")
    parser.add_argument("--ports", type=int, nargs="+", default=None,
                        help="相机端口列表，例如 --ports 7070 7080")
    parser.add_argument("--fps",   type=float, default=30.0,
                        help="显示帧率（默认 30）")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="窗口缩放比例，例如 0.75（默认 1.0）")
    args = parser.parse_args()

    cam_cfg = ({f"camera_{p}": p for p in args.ports}
               if args.ports else CAMERA_CONFIG)

    print(f"\n{'='*60}")
    print("SO101 相机实时监控")
    print(f"{'='*60}")
    print(f"  OrcaSim 地址 : {args.orcagym_addr}")
    for name, port in cam_cfg.items():
        print(f"  {name:20s} → ws://localhost:{port}")
    print(f"  FPS  : {args.fps}   缩放 : {args.scale}")
    print(f"{'='*60}\n")

    run_monitor(
        orcagym_addr=args.orcagym_addr,
        camera_config=cam_cfg,
        fps=args.fps,
        scale=args.scale,
    )


if __name__ == "__main__":
    main()
