# pi0.5 模型权重（h11_lora）

将训练好的 pi0.5 模型权重放置在本目录下。

## 目录结构

```
models/
└── h11_lora/
    ├── 5000/              ← checkpoint 步数目录
    │   ├── params/
    │   ├── assets/
    │   └── _CHECKPOINT_METADATA
    └── 6000/
        ├── params/
        ├── assets/
        └── _CHECKPOINT_METADATA
```

## 启动推理服务器

```bash
# 在 openpi uv 环境中执行
cd openpi
uv run scripts/serve_policy.py policy:checkpoint \
    --policy.config=pi05_h7_lora \
    --policy.dir=../OrcaGym-SO101/models/h11_lora/6000
```

将 `6000` 替换为你要使用的 checkpoint 步数目录名。

## 获取模型权重

- 通过训练流程自行训练（参考 `openpi_patches/README.md` 中的训练配置说明）
- 或联系项目维护者获取预训练权重
