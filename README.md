# vista-fc

阿里云函数计算 (FC 3.0) 对 [vista](https://github.com/.../vista) 投研框架 8 个业务流程的封装。通过函数工作流 (FnF) 编排，用 [serverless-devs](https://www.serverless-devs.com/) 做本地开发与部署。

## 快速开始

```bash
# 1. 装依赖
uv sync

# 2. 复制本地环境配置
cp .env.example .env.local  # 编辑填入私有源 token / 阿里云 ak/sk

# 3. 起本地依赖（minio + clickhouse）
docker compose -f dev/compose.yaml up -d

# 4. 跑单测
uv run pytest tests/unit

# 5. 本地调单个函数
scripts/build_image.sh --dev
s local invoke factor-detect --event-file tests/fixtures/events/factor_detect_min.json --env-file .env.local
```

## 文档

- 设计文档：[docs/superpowers/specs/2026-04-22-vista-fc-encapsulation-design.md](docs/superpowers/specs/2026-04-22-vista-fc-encapsulation-design.md)

## 函数

| FC 函数 | vista 入口 |
|---|---|
| factor-plan | `vista.agents.factor_plan.plan_factor_routes` |
| factor-builder | `vista.agents.factor_builder.FactorBuilder` |
| factor-detect | `vista.utils.factor_detect.factor_detect` |
| factor-duplicate | `vista.utils.factor_duplicate.factor_duplicate` |
| factor-evaluate | `vista.utils.factor_evaluate.factor_evaluate` |
| factor-filter | `vista.utils.factor_filter.factor_filter` |
| strategy-backtest | `vista.utils.strategy_backtest.run_strategy_backtest` |
| vista-realtime | `vista.realtime.workflow.RealtimeWorkflow` |
