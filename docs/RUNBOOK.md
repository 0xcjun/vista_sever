# Runbook

常见运行时问题的速查表。详细架构见
[specs](superpowers/specs/2026-04-22-vista-fc-encapsulation-design.md) §9.8。

## Current blockers

### 1. Aliyun credentials are not provisioned

Preflight and deploy stages need the following GitHub secrets configured:

- `ALIYUN_ACCOUNT_ID`
- `ALIYUN_DEV_PREFLIGHT_AK_ID` / `..._SECRET`
- `ALIYUN_DEV_AK_ID` / `..._SECRET`
- `ALIYUN_PROD_AK_ID` / `..._SECRET`
- `ACR_USER` / `ACR_PASS` (ACR push access)
- `VPC_ID` / `VSWITCH_ID` / `SG_ID` / `NAS_MOUNT_TARGET`
- `CLICKHOUSE_URL` / `CLICKHOUSE_USER` / `CLICKHOUSE_PASS`

Plus the RAM roles `fc-vista-role` (function execution) and `fnf-vista-role`
(FnF flow execution) must exist before the first deploy.

> vista 已改从私有源 `zbczsc-dev` 安装（无需凭证），docker 镜像可以本地/CI 正常构建。历史阻塞项（editable 路径 + private-token）已解除。

### 2. arm64 linux 无私有 wheel

`chan-factor-rs` / `chanfactor` 只发布了 `linux_x86_64` wheel，导致镜像构建
固定为 `linux/amd64`（见 [GUIDE §8.2](GUIDE.md#82-arm64-linux-无私有-wheel)）。
FC 函数实例必须选 x86 架构。

---

## 告警 / 处置

### 函数错误率告警（>5% in 5min）

1. SLS 按 `run_id` 拉错误日志：
   ```
   * | where function_name='<fn>' and status='error' | order by __time__ desc
   ```
2. 看 `error.code`：
   - `VISTA_LLM_RATE_LIMIT` / `CLICKHOUSE_CONNECT` / `OSS_READ_FAIL` 等
     retriable：看 FnF retry 是否生效，若 FC 直调可考虑加并发限流
   - `VISTA_LOGIC_ERROR`：回滚镜像
     `GIT_SHA=<old_sha> s deploy --access prod`
   - `INPUT_VALIDATION`：调用方输入错，不是函数问题

### FnF execution 卡住

```bash
s cli fnf DescribeExecution --name research-pipeline --execution-name <name> --access prod
```

- Status=Running 很久：看当前 step 是哪个函数，去 SLS 查；必要时：
  ```bash
  s cli fnf StopExecution --name research-pipeline --execution-name <name> --access prod
  ```
- Status=Failed：从 `HistoryEvents` 找到 StepExecutionFailed 事件的 Error

### OSS ETag 冲突反复出现

说明同一 workspace 有并发 executions。临时处置：
1. 找到两条 executions 中较新的一条 Stop 掉
2. 长期：调用方去重逻辑改成 `executionName = <workspace_id>-<ts>` 并强唯一

### 依赖 wheel 构建失败

1. 本地复现：`uv sync --reinstall`
2. 确认 `zbczsc-dev` 私有源可达：`curl -s https://pypi.zbczsc.com/team/dev/+simple/vista/ | head`
3. 若 vista 版本回归：回退 `pyproject.toml` 里的 `vista>=X.Y.Z` pin，`uv lock`，重 build

### 镜像拉不动（ImagePullBackOff 类错误）

1. `docker pull registry.cn-hangzhou.aliyuncs.com/vista/vista-fc-base:<sha>` 本地验证
2. 检查 FC 函数角色是否有 `cr:PullArtifact`
3. 重新 `s deploy` 触发 FC 重新拉取

### dev 环境被搞脏

```bash
# 全拆
FC_ACCESS=dev s remove --access dev --assume-yes
# 重新部署
GIT_SHA=<sha> s deploy --access dev --assume-yes
```

## 发版流程

1. PR 合入 main
2. CI 自动：lint -> unit -> integration -> build-push -> preflight
   -> deploy-dev -> smoke-dev
3. 手动触发 `workflow_dispatch` 在 main 上跑 deploy-prod
4. CI 自动：deploy-prod -> smoke-prod

## 回滚

不走 git revert，只换镜像 tag：

```bash
# 找到上一个好版本
git log --oneline --grep="feat\|fix" | head -5
# 用老 sha 重部
GIT_SHA=<old_sha> s deploy --access prod --assume-yes
```

## 联系人

- Slack: #vista-fc
- On-call: 看 ARMS 告警推送
