# SO101 仿真场景文件放置说明

运行仿真脚本需要两类文件：
1. **OrcaStudio 场景文件**（Assets + Levels）：放入 OrcaStudio 安装目录
2. **机械臂模型文件**（so101_new_calib.xml + assets/）：放入本目录

---

## 一、OrcaStudio 场景文件

找到 OrcaSim 的安装目录，将交接包中的 `Assets/` 和 `Levels/` 直接**覆盖替换**对应目录：

```
OrcaSim 安装目录/
├── Assets/    ←  用交接包 Assets/ 覆盖替换（包含 SO101 模型、积木等 Prefab）
└── Levels/    ←  用交接包 Levels/ 覆盖替换（包含 lerobotscene 等场景）
```

> 替换后在 OrcaStudio 中打开 `Levels/lerobotscene` 场景，点击"运行"即可。

---

## 二、机械臂模型文件

将以下文件放入本目录（`assets/so101/`）：

```
assets/so101/
├── so101_new_calib.xml     ← SO101 机械臂模型文件（必需）
└── assets/                 ← 网格 .stl 文件目录（必需，和 xml 配套）
    ├── base_so101_v2.stl
    ├── upper_arm_so101_v1.stl
    └── ...（其余 .stl 文件）
```

来源：交接包 `仿真/SO101/so101_new_calib.xml` 和 `仿真/SO101/assets/` 目录。

---

## 验证

文件放置完成后，运行以下命令验证路径正确：

```bash
conda activate so101
cd OrcaGym-SO101
python -c "import os; assert os.path.exists('assets/so101/so101_new_calib.xml'), '❌ XML 文件找不到'; print('✓ XML 文件路径正确')"
```

---

## 自定义路径

如果 XML 文件放在其他位置，通过 `--xml_path` 参数指定：

```bash
python examples/so101/so101_leader_teleoperation.py \
    --xml_path /custom/path/so101_new_calib.xml
```

脚本默认查找路径为 `assets/so101/so101_new_calib.xml`（相对项目根目录）。
