# vista-fc 部署检查清单

这份文档只解决一个问题:把 `vista-fc` 从本地部署到阿里云 FC 3.0,并能成功调用函数。

优先级:

1. 账号一致: `FC_ACCESS`、`ALIYUN_ACCOUNT_ID`、RAM 角色、ACR、NAS、VPC 必须在同一个阿里云账号下。
2. 资源同区: FC / ACR / NAS / VPC / OSS / SLS 优先全部使用 `cn-hangzhou`。
3. 先推镜像,再 `s deploy --skip-push`。不要依赖 fc3 自动 push。
4. 出错先看根因层级: access -> image -> role -> NAS/VPC -> runtime。

---

## 0. 当前部署事实模型

`s.yaml` 用这些环境变量渲染云资源:

| 变量 | 用途 | 必须满足 |
|---|---|---|
| `FC_ACCESS` | Serverless Devs access alias | `s config get --access "$FC_ACCESS"` 能查到正确账号 |
| `ALIYUN_ACCOUNT_ID` | 拼 RAM role ARN | 必须等于函数归属账号 |
| `FC_REGION` | FC region | 默认 `cn-hangzhou` |
| `IMAGE_REGISTRY` | ACR 仓库,不带 tag | 必须是当前账号可读的 ACR 仓库 |
| `GIT_SHA` | 镜像 tag | 必须已 push 到 `IMAGE_REGISTRY:$GIT_SHA` |
| `NAS_MOUNT_TARGET` | NAS 挂载点 host | 只填 host,不要带 `:/` |
| `VPC_ID` / `VSWITCH_ID` / `SG_ID` | 函数 VPC 配置 | 必须能访问 NAS 挂载点 |

函数名由 `FC_SUFFIX` 决定:

```bash
factor-plan${FC_SUFFIX}
```

preflight 推荐:

```bash
export GIT_SHA="$(git rev-parse --short HEAD)-r2"
export FC_SUFFIX="-preflight-$GIT_SHA"
```

---

## 1. 控制台资源准备

### 1.1 RAM 部署用户

控制台: https://ram.console.aliyun.com

1. 创建 RAM 用户,例如 `vista-deployer`。
2. 勾选 `OpenAPI 调用访问`,保存 AK/SK。
3. 部署期可先给 `AdministratorAccess`;稳定后再收窄。
4. 记下账号 ID,后面填 `ALIYUN_ACCOUNT_ID`。

强校验:

```bash
s config get --access dev-preflight
```

输出里的 `AccountID` 必须等于你要部署函数的账号。

### 1.2 ACR 镜像仓库

控制台: https://cr.console.aliyun.com

1. 选择 `cn-hangzhou`。
2. 创建命名空间,例如 `vista_fc`。
3. 创建私有仓库 `vista-fc-base`。
4. 复制完整公网仓库地址:

```text
crpi-xxx.cn-hangzhou.personal.cr.aliyuncs.com/vista_fc/vista-fc-base
```

5. 设置 ACR 固定密码。

填入:

```bash
ACR_USER=<ACR 登录用户名>
ACR_PASS=<ACR 固定密码>
IMAGE_REGISTRY=crpi-xxx.cn-hangzhou.personal.cr.aliyuncs.com/vista_fc/vista-fc-base
```

`IMAGE_REGISTRY` 不要只填 registry host,也不要带 `:tag`。

### 1.3 VPC / VSwitch / 安全组

控制台:

- VPC: https://vpc.console.aliyun.com
- 安全组: https://ecs.console.aliyun.com

建议:

```text
VPC 网段: 10.0.0.0/16
VSwitch 网段: 10.0.1.0/24
```

安全组至少要允许函数访问 NAS:

```text
出方向 TCP 2049 -> 10.0.0.0/16
```

如果安全组是默认全出方向允许,通常不用额外改。若你收紧过规则,必须显式放行 `2049`。

### 1.4 NAS

控制台: https://nas.console.aliyun.com

1. 创建通用型 NAS,协议选 `NFS`。
2. 挂载点类型选 `专有网络`。
3. VPC / VSwitch 必须选择函数使用的那一组。
4. 权限组放行函数所在 VPC 网段:

```text
授权地址: 10.0.0.0/16
读写权限: 读写
用户权限: no_root_squash 或默认允许
```

填入 `.env.prod`:

```bash
NAS_MOUNT_TARGET=xxxx.cn-hangzhou.nas.aliyuncs.com
```

只填 host。`s.yaml` 会自动拼成 `host:/`。

### 1.5 OSS

控制台: https://oss.console.aliyun.com

至少准备两个 bucket:

```text
vista-fc-prod
vista-fc-preflight
```

要求:

- region: `cn-hangzhou`
- 权限: 私有
- 服务端加密: OSS 托管即可

### 1.6 SLS

控制台: https://sls.console.aliyun.com

```text
Project: vista-fc
Logstore: handlers
```

### 1.7 RAM 角色

#### `fc-vista-role`

角色名必须是:

```text
fc-vista-role
```

信任策略必须允许 FC 扮演:

```json
{
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "fc.aliyuncs.com"
        ]
      }
    }
  ],
  "Version": "1"
}
```

部署期建议挂:

```text
AliyunOSSFullAccess
AliyunNASFullAccess
AliyunContainerRegistryReadOnlyAccess
AliyunLogFullAccess
```

#### `fnf-vista-role`

角色名:

```text
fnf-vista-role
```

信任主体选 `函数工作流` / `CloudFlow`,服务标识是:

```text
fnf.aliyuncs.com
```

权限:

```text
AliyunFCInvocationAccess
```

FnF 在控制台里可能叫 CloudFlow。搜不到信任主体时,先打开 https://fnf.console.aliyun.com 开通服务。

---

## 2. 本地配置

### 2.1 配置 Serverless Devs access

推荐用命令写入,不要手改后忘记校验:

```bash
s config add \
  --AccountID <账号ID> \
  --AccessKeyID '<RAM AK>' \
  --AccessKeySecret '<RAM SK>' \
  --access dev-preflight \
  --force

s config add \
  --AccountID <账号ID> \
  --AccessKeyID '<RAM AK>' \
  --AccessKeySecret '<RAM SK>' \
  --access prod \
  --force
```

校验:

```bash
s config get --access dev-preflight
s config get --access prod
```

### 2.2 `.env.prod`

仓库根目录创建 `.env.prod`:

```bash
FC_ACCESS=prod
ALIYUN_ACCOUNT_ID=<账号ID>
FC_REGION=cn-hangzhou

OSS_BUCKET=vista-fc-prod
OSS_REGION=cn-hangzhou

NAS_MOUNT_TARGET=<NAS 挂载点 host,不带 :/>
VPC_ID=<vpc-xxx>
VSWITCH_ID=<vsw-xxx>
SG_ID=<sg-xxx>

LOG_PROJECT=vista-fc
LOG_STORE=handlers

ACR_USER=<ACR 用户名>
ACR_PASS=<ACR 固定密码>
IMAGE_REGISTRY=<完整 ACR 仓库地址,不带 tag>

PYTHON_IMAGE=python:3.12-slim-bookworm
UV_IMAGE=ghcr.io/astral-sh/uv:latest

ANTHROPIC_API_KEY=<LLM key>
ANTHROPIC_BASE_URL=
CZSC_TOKEN=<czsc token>
CZSC_DATA_API=https://api.zbczsc.com
```

国内网络拉基础镜像不稳定时,只临时覆盖:

```bash
export PYTHON_IMAGE=public.ecr.aws/docker/library/python:3.12-slim-bookworm
export UV_IMAGE=ghcr.io/astral-sh/uv:latest
```

不要把 `.env.prod` 提交:

```bash
grep -E '^\.env' .gitignore
git status --short .env.prod
```

---

## 3. Preflight 部署

推荐先部署隔离后缀:

```bash
set -a && source .env.prod && set +a
export FC_ACCESS=dev-preflight
export OSS_BUCKET=vista-fc-preflight
export GIT_SHA="$(git rev-parse --short HEAD)-r2"
export FC_SUFFIX="-preflight-$GIT_SHA"
unset IMAGE_CACHE
```
```bash
set -a && source .env.prod && set +a
export FC_ACCESS=dev-preflight
export GIT_SHA="$(git rev-parse --short HEAD)-r2"
export FC_SUFFIX="-preflight-$GIT_SHA"

s deploy --access dev-preflight --assume-yes --skip-push
```
### 3.1 推镜像

```bash
bash tests/deploy_preflight/02_image_push.sh
```

确认镜像存在:

```bash
docker buildx imagetools inspect "$IMAGE_REGISTRY:$GIT_SHA"
```

### 3.2 部署 FC

镜像已经推过,部署必须跳过 push:

```bash
s deploy --access "$FC_ACCESS" --assume-yes --skip-push
```

如果只想先验证 `factor-plan`,可以部署后直接查它。注意:当前 Serverless Devs 可能仍会顺序检查多个资源,不要同时开多个 `s deploy`。

### 3.3 校验函数配置

```bash
s cli fc3 info \
  --region "${FC_REGION:-cn-hangzhou}" \
  --function-name "factor-plan${FC_SUFFIX}" \
  --access "$FC_ACCESS" | grep -E 'functionArn|role|state|lastUpdateStatus|serverAddr|vpcId|vSwitchIds|securityGroupId'
```

必须看到:

```text
functionArn: ...<ALIYUN_ACCOUNT_ID>...
role:        acs:ram::<ALIYUN_ACCOUNT_ID>:role/fc-vista-role
state:       Active
lastUpdateStatus: Successful
```

### 3.4 调用函数

```bash
s cli fc3 invoke \
  --region "${FC_REGION:-cn-hangzhou}" \
  --function-name "factor-plan${FC_SUFFIX}" \
  --timeout 120 \
  -e "$(cat tests/fixtures/events/factor_plan_min.json)" \
  --access "$FC_ACCESS"
```

---

## 4. Prod 部署

preflight 通过后,去掉隔离设置:

```bash
set -a && source .env.prod && set +a
export FC_ACCESS=prod
export GIT_SHA="$(git rev-parse --short HEAD)"
unset FC_SUFFIX
unset IMAGE_CACHE
```

推镜像:

```bash
scripts/push_image.sh
```

部署 FC:

```bash
s deploy --access prod --assume-yes --skip-push
```

部署 cron:

```bash
s deploy -t s.realtime-cron.yaml --access prod --assume-yes --skip-push
```

部署 FnF flow:

```bash
s cli fnf deploy \
  --region "${FC_REGION:-cn-hangzhou}" \
  --name "research-pipeline${FC_SUFFIX:-}" \
  --definition flows/research_pipeline.fdl \
  --type FDL \
  --access "$FC_ACCESS"
```

Serverless Devs v3.1.10 的 v3 registry 没有 `component: fnf`;不要把 FnF 写进 `s.yaml`。

---

## 5. 故障定位表

按层级排查,不要跳层。

| 层级 | 现象 | 根因 | 下一步 |
|---|---|---|---|
| access | `Not found access: s` | 当前 shell 的 `$FC_ACCESS` 展开成了 `s` | `export FC_ACCESS=dev-preflight`;或命令里写死 `--access dev-preflight` |
| access | `The service or function doesn't belong to you` | `FC_ACCESS` 的账号和函数 ARN 账号不一致,invoke endpoint 拼错 | `s config get --access "$FC_ACCESS"` 的 `AccountID` 必须等于 `functionArn` 账号 |
| account | `role not exists: acs:ram::<old-account>:role/fc-vista-role` | `.env.prod` 的 `ALIYUN_ACCOUNT_ID` 是旧账号,函数 role 被渲染错 | 改 `.env.prod`,重新 `s deploy --skip-push` |
| RAM | `Assume role ... fc-vista-role fail` | `fc-vista-role` 信任策略没有 `fc.aliyuncs.com` | 修改 RAM 角色信任策略,无需重推镜像 |
| image | `REPO_NOT_EXIST` | `IMAGE_REGISTRY` 不是当前账号真实 ACR 仓库 | 填完整 ACR repo,不带 tag |
| image | `IMAGE_NOT_EXIST` | `IMAGE_REGISTRY:$GIT_SHA` 没推上去 | 先跑 `02_image_push.sh` 或 `scripts/push_image.sh` |
| image | `unknown/unknown platform` | buildx 推了 provenance/SBOM attestation | 当前 `scripts/build_image.sh` 已关闭 provenance/SBOM;换新 tag 重推 |
| Docker | `Cache export is not supported for the docker driver` | Docker Desktop 默认 driver 不支持 registry cache | `unset IMAGE_CACHE` |
| Docker | `metadata_v2.db: input/output error` | Docker Desktop 存储损坏 | Docker Desktop -> Troubleshoot -> Clean/Purge data |
| Docker | 拉 `python` / `uv` 超时 | Docker Hub / GHCR 网络问题 | 临时设置 `PYTHON_IMAGE` / `UV_IMAGE` |
| NAS | `NASConfig's nas server address ... expected format` | FC3 要 `host:/` | `.env.prod` 只填 host,模板拼 `:/` |
| NAS | `Failed to mount NAS on guest`, `Unknown error 521` | NAS 挂载点不可从函数 VPC 访问,或权限组没放行 | 检查 NAS 挂载点 VPC/VSwitch、权限组 `10.0.0.0/16`、安全组出方向 `2049` |
| NAS | `mount failed` | NAS 可用区/VPC 和函数 VSwitch 不匹配 | 给同一 VPC/VSwitch 新建 NAS 挂载点,更新 `NAS_MOUNT_TARGET` |
| Serverless Devs | `Component or plugin fnf is not found` | v3 registry 没有 `fnf` component | 用 `s cli fnf deploy/execution/remove` |
| deploy | `fc:CreateFunction AccessDenied` | 部署 AK 权限不足 | 给部署用户 FC create/update + `ram:PassRole` |

---

## 6. 当前问题的快速定位命令

### 6.1 账号链路

```bash
printf 'FC_ACCESS=%s\nALIYUN_ACCOUNT_ID=%s\nFC_SUFFIX=%s\n' "$FC_ACCESS" "$ALIYUN_ACCOUNT_ID" "$FC_SUFFIX"
s config get --access "$FC_ACCESS"

s cli fc3 info \
  --region "${FC_REGION:-cn-hangzhou}" \
  --function-name "factor-plan${FC_SUFFIX}" \
  --access "$FC_ACCESS" | grep -E 'functionArn|role|state|lastUpdateStatus'
```

结论标准:

```text
s config AccountID == functionArn 账号 == role 账号 == ALIYUN_ACCOUNT_ID
```

### 6.2 invoke endpoint

```bash
rg -n "invokeEndpoint|AccessDenied|ConnectTimeout" ~/.s/logs -S | tail -20
```

`invokeEndpoint` 应该是:

```text
<ALIYUN_ACCOUNT_ID>.cn-hangzhou.fc.aliyuncs.com
```

### 6.3 NAS 链路

```bash
s cli fc3 info \
  --region "${FC_REGION:-cn-hangzhou}" \
  --function-name "factor-plan${FC_SUFFIX}" \
  --access "$FC_ACCESS" | sed -n '/nasConfig:/,/resourceGroupId:/p;/vpcConfig:/,/^[^ ]/p'
```

重点看:

```text
serverAddr == ${NAS_MOUNT_TARGET}:/
vpcId == ${VPC_ID}
vSwitchIds 包含 ${VSWITCH_ID}
securityGroupId == ${SG_ID}
```

---

## 7. 成功标准

部署成功不是 `s deploy` 命令结束,而是下面三件事都成立:

1. `s cli fc3 info` 显示:

```text
state: Active
lastUpdateStatus: Successful
```

2. `role`、`functionArn`、`s config AccountID` 都是同一个账号。
3. `s cli fc3 invoke` 返回函数业务响应,不再出现 access / role / NAS / image 层错误。

冒烟测试:

```bash
FC_SMOKE_READY=1 FC_ACCESS=prod uv run pytest tests/smoke -v
FC_ACCESS=prod bash scripts/invoke_all.sh fnf
```

---

## 8. 控制台入口

| 服务 | URL | 备注 |
|---|---|---|
| RAM | https://ram.console.aliyun.com | 用户、角色、信任策略 |
| ACR | https://cr.console.aliyun.com | 镜像仓库和固定密码 |
| VPC | https://vpc.console.aliyun.com | VPC / VSwitch |
| ECS | https://ecs.console.aliyun.com | 安全组 |
| NAS | https://nas.console.aliyun.com | NFS 文件系统和挂载点 |
| OSS | https://oss.console.aliyun.com | Bucket |
| SLS | https://sls.console.aliyun.com | Project / Logstore |
| FC 3.0 | https://fcnext.console.aliyun.com | 函数列表和日志 |
| FnF / CloudFlow | https://fnf.console.aliyun.com | 工作流 |

---

## 9. 关联文件

- [GUIDE.md](GUIDE.md)
- [s.yaml](../s.yaml)
- [s.realtime-cron.yaml](../s.realtime-cron.yaml)
- [.env.example](../.env.example)
- [scripts/push_image.sh](../scripts/push_image.sh)
- [scripts/build_image.sh](../scripts/build_image.sh)
- [scripts/invoke_all.sh](../scripts/invoke_all.sh)
- [scripts/invoke_all.py](../scripts/invoke_all.py)
- [tests/deploy_preflight/](../tests/deploy_preflight/)
