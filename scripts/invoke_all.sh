#!/usr/bin/env bash
# 上线后调用所有函数的演示脚本。
#
# 这个脚本同时是：
#   1) 部署后冒烟工具 — 一把跑过所有函数验证部署没问题
#   2) 客户端代码模板 — 每个 step 给一个最小 envelope 示例，复制到你自己的代码里改改就能用
#
# 用法：
#   bash scripts/invoke_all.sh                       # 列命令清单
#   FC_ACCESS=prod bash scripts/invoke_all.sh plan   # 跑某一步
#   FC_ACCESS=prod bash scripts/invoke_all.sh fnf    # 起 FnF 一条龙（推荐生产用）
#   FC_ACCESS=prod bash scripts/invoke_all.sh chain  # 按顺序串调每一个函数
#
# 环境变量：
#   FC_ACCESS         必填   serverless-devs 凭据 alias（~/.s/access.yaml 里的 key，e.g. prod）
#   FC_SUFFIX         可选   函数名后缀，匹配 s.yaml 里的 functionSuffix；默认空
#   OSS_BUCKET        可选   生产 OSS bucket，默认 vista-fc-prod
#   USER_HASH         可选   租户 hash，默认 u_demo
#   WORKSPACE_ID      可选   工作空间 ID，默认 EXP_DEMO
#   RUN_ID            可选   运行 ID（FnF 重跑同名时已成功 step 自动跳过），默认 demo-时间戳
#
# 依赖：serverless-devs CLI (`s`) + jq

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────────────────────────────────
ACCESS="${FC_ACCESS:?FC_ACCESS 必须设置 (e.g. FC_ACCESS=prod)}"
SUFFIX="${FC_SUFFIX:-}"
OSS_BUCKET="${OSS_BUCKET:-vista-fc-prod}"
USER_HASH="${USER_HASH:-u_demo}"
WORKSPACE_ID="${WORKSPACE_ID:-EXP_DEMO}"
RUN_ID="${RUN_ID:-demo-$(date +%Y%m%d-%H%M%S)}"

# tenant 块 — 所有函数共用，由 EnvelopeIn.tenant 字段消费
TENANT=$(jq -n \
  --arg uh "$USER_HASH" --arg wid "$WORKSPACE_ID" \
  --arg rid "$RUN_ID" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{user_hash: $uh, workspace_id: $wid, workspace_kind: "research",
    run_id: $rid, requested_at: $ts}')

# OSS 路径基础
WS_BASE="oss://$OSS_BUCKET/user_data/$USER_HASH/research/$WORKSPACE_ID"
RESEARCH_DATA_URI="oss://$OSS_BUCKET/research_data/future_kline.duckdb"

# 演示用的 problem code（vista 3.2.x 的命名）
DEMO_PROBLEM_CODE="FTS_PROBLEM_A504A636"   # 期货-股指-30分钟-量价择时

# ──────────────────────────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────────────────────────
banner() {
  printf '\n\033[1;36m═══ %s ═══\033[0m\n' "$1"
}

# 调一个 fc 函数。第一个参数是函数名（不带 suffix），第二个是 payload JSON。
invoke_fc() {
  local fn="$1" payload="$2"
  local fname="${fn}${SUFFIX}"
  local event=$(jq -n --argjson tenant "$TENANT" --argjson payload "$payload" \
    '{tenant: $tenant, payload: $payload}')

  banner "▶ invoke $fname"
  echo "envelope-in:"
  echo "$event" | jq .
  echo
  echo "envelope-out:"
  s cli fc invoke-function \
    --function-name "$fname" \
    --event "$event" \
    --access "$ACCESS"
  echo
}

# ──────────────────────────────────────────────────────────────────────────
# 各 step 示例
# ──────────────────────────────────────────────────────────────────────────

# 1) factor-plan — LLM 规划因子挖掘路线
#    in : user_input (自然语言), factor_numbers, ...
#    out: payload.routes_toml_artifact.oss_uri  → 给 factor-builder
do_plan() {
  invoke_fc factor-plan "$(jq -n '{
    user_input: "动量反转因子挖掘",
    plan_model: null,
    skill_path: null,
    interactive: false,
    factor_numbers: 4
  }')"
}

# 2) factor-builder — LLM 按 plan 生成因子代码
#    in : routes_toml_uri (来自 plan 的产出)
#    out: payload.factors_db_artifact.oss_uri  → 给 detect / duplicate / evaluate / filter
do_builder() {
  local routes_uri="${ROUTES_URI:-$WS_BASE/factor_routes.toml}"
  invoke_fc factor-builder "$(jq -n --arg uri "$routes_uri" '{
    routes_toml_uri: $uri,
    builder_type:    "agno_agent",
    factor_numbers:  4,
    batch_size:      4,
    max_workers:     1,
    multi_turn:      false,
    model:           null,
    max_retries:     2
  }')"
}

# 3) factor-detect — 用真数据评估因子有效性
#    in : factors_db_uri, research_data_uri
#    out: payload.route_codes (有效因子的 route 编码)  → 给后续 step
do_detect() {
  local db_uri="${FACTORS_DB_URI:-$WS_BASE/factors.duckdb}"
  invoke_fc factor-detect "$(jq -n --arg db "$db_uri" --arg rd "$RESEARCH_DATA_URI" '{
    factors_db_uri:    $db,
    research_data_uri: $rd,
    max_workers:       4,
    timeout:           60
  }')"
}

# 4) factor-duplicate — 去重 / 相关性聚合
do_duplicate() {
  local db_uri="${FACTORS_DB_URI:-$WS_BASE/factors.duckdb}"
  invoke_fc factor-duplicate "$(jq -n --arg db "$db_uri" --arg rd "$RESEARCH_DATA_URI" \
                                       --arg pc "$DEMO_PROBLEM_CODE" '{
    factors_db_uri:    $db,
    research_data_uri: $rd,
    route_codes:       [],
    problem_codes:     [$pc],
    threshold:         0.8,
    max_workers:       1,
    timeout:           120
  }')"
}

# 5) factor-evaluate — 策略建模评估（最重，4 vCPU / 16 GB）
do_evaluate() {
  local db_uri="${FACTORS_DB_URI:-$WS_BASE/factors.duckdb}"
  invoke_fc factor-evaluate "$(jq -n --arg db "$db_uri" --arg rd "$RESEARCH_DATA_URI" \
                                      --arg pc "$DEMO_PROBLEM_CODE" '{
    factors_db_uri:    $db,
    research_data_uri: $rd,
    route_codes:       [],
    problem_codes:     [$pc],
    models:            ["DirectExposure"],
    max_workers:       1,
    timeout:           180,
    fee_rate:          0.0
  }')"
}

# 6) factor-filter — 按指标筛选 top-N，输出 strategy.toml
#    out: payload.toml_artifacts[]  → 给 strategy-backtest 做 fanout
do_filter() {
  local db_uri="${FACTORS_DB_URI:-$WS_BASE/factors.duckdb}"
  invoke_fc factor-filter "$(jq -n --arg db "$db_uri" --arg rd "$RESEARCH_DATA_URI" \
                                    --arg pc "$DEMO_PROBLEM_CODE" '{
    factors_db_uri:     $db,
    research_data_uri:  $rd,
    problem_codes:      [$pc],
    route_codes:        [],
    evaluate_methods:   [],
    filter_methods:     [],
    positive_threshold: 0.0,
    n:                  10,
    creator:            "vista-fc-tutorial",
    outsample_sdt:      "20250101"
  }')"
}

# 7) strategy-backtest — wbt 综合回测
#    in : strategy_toml_uri (来自 filter 的产出)
do_backtest() {
  local toml_uri="${STRATEGY_TOML_URI:-$WS_BASE/strategy.toml}"
  invoke_fc strategy-backtest "$(jq -n --arg toml "$toml_uri" --arg rd "$RESEARCH_DATA_URI" '{
    strategy_toml_uri: $toml,
    research_data_uri: $rd,
    mode:              "research",
    data_mode:         "total",
    backtest_workers:  1,
    fee_rate:          0.0,
    digits:            2,
    n_jobs:            1,
    yearly_days:       252
  }')"
}

# 8) vista-realtime — 实盘信号生成（s.yaml 里无触发器版，纯 SDK 调）
#    需要事先把 strategy.toml 推到 oss://.../user_data/<u>/realtime/<wid>/
do_realtime() {
  local toml_uri="${STRATEGY_TOML_URI:-oss://$OSS_BUCKET/user_data/$USER_HASH/realtime/$WORKSPACE_ID/strategy.toml}"
  invoke_fc vista-realtime "$(jq -n --arg toml "$toml_uri" '{
    strategy_toml_uri: $toml,
    update_mode:       "auto",
    push_targets:      ["default"]
  }')"
}

# 9) deadletter — FnF catch.goto 的兜底，直接调用是为了演示契约。
#    生产路径：FnF step 失败 → catch.goto deadletter_trap → 这个函数把现场写到 OSS。
do_deadletter() {
  invoke_fc deadletter "$(jq -n '{
    failed_function:  "factor-detect",
    original_payload: { factors_db_uri: "oss://example/factors.duckdb" },
    error: {
      code:      "VISTA_LOGIC_ERROR",
      message:   "demo failure for tutorial",
      retriable: false,
      trace_id:  "tr-tutorial-demo"
    }
  }')"
}

# 10) FnF — 推荐生产路径，一次启动，FnF 编排串完 7 步并自带 checkpoint resume
do_fnf() {
  banner "▶ start FnF flow research-pipeline${SUFFIX}"

  local fnf_input=$(jq -n \
    --argjson tenant "$TENANT" \
    --arg rd "$RESEARCH_DATA_URI" \
    --arg pc "$DEMO_PROBLEM_CODE" '{
      tenant:               $tenant,

      # factor-plan
      user_input:           "动量反转因子挖掘",
      plan_model:           null,
      skill_path:           null,
      interactive:          false,

      # factor-builder
      build_model:          null,
      builder_type:         "agno_agent",
      factor_numbers:       4,
      batch_size:           4,
      build_workers:        1,
      multi_turn:           false,
      build_max_retries:    2,

      # factor-detect
      detect_workers:       4,
      detect_timeout:       60,

      # factor-duplicate
      dup_workers:          1,
      dup_threshold:        0.8,
      dup_timeout:          120,

      # factor-evaluate
      eval_workers:         1,
      eval_timeout:         180,
      eval_models:          ["DirectExposure"],
      fee_rate:             0.0,

      # factor-filter
      problem_codes:        [$pc],
      evaluate_methods:     [],
      filter_methods:       [],
      positive_extractor:   "ratio_across_problems",
      positive_metric:      "绝对收益",
      positive_threshold:   0.0,
      top_n:                10,
      author:               "vista-fc-tutorial",
      outsample_sdt:        "20250101",

      # strategy-backtest (foreach fanout)
      mode:                 "research",
      data_mode:            "total",
      backtest_concurrency: 4,
      backtest_workers:     1,
      wbt: { fee_rate: 0.0, digits: 2, n_jobs: 1, yearly_days: 252 },

      research_data_uri:    $rd
    }')

  echo "input:"
  echo "$fnf_input" | jq .
  echo
  echo "starting execution name: $RUN_ID"
  echo

  s cli fnf StartExecution \
    --flow-name "research-pipeline${SUFFIX}" \
    --execution-name "$RUN_ID" \
    --input "$fnf_input" \
    --access "$ACCESS"

  cat <<EOF

📊 查执行状态：
  s cli fnf DescribeExecution \\
    --flow-name research-pipeline${SUFFIX} \\
    --execution-name $RUN_ID \\
    --access $ACCESS

📜 拉历史事件（看哪步在哪挂的）：
  s cli fnf GetExecutionHistory \\
    --flow-name research-pipeline${SUFFIX} \\
    --execution-name $RUN_ID \\
    --access $ACCESS

❌ 失败时看 deadletter 落盘：
  ossutil ls oss://$OSS_BUCKET/user_data/$USER_HASH/deadletter/$RUN_ID/

🔁 修了底层问题想重放：用同 execution-name 重新 StartExecution，
   FnF checkpoint 会跳过已成功的 step，从失败处接着跑。
EOF
}

# ──────────────────────────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────────────────────────
case "${1:-help}" in
  plan)        do_plan ;;
  builder)     do_builder ;;
  detect)      do_detect ;;
  duplicate)   do_duplicate ;;
  evaluate)    do_evaluate ;;
  filter)      do_filter ;;
  backtest)    do_backtest ;;
  realtime)    do_realtime ;;
  deadletter)  do_deadletter ;;
  fnf)         do_fnf ;;

  # 串调每个函数（仅作演示 — 真要端到端跑请用 fnf）
  chain)
    do_plan
    do_builder
    do_detect
    do_duplicate
    do_evaluate
    do_filter
    do_backtest
    do_realtime
    ;;

  help|*)
    cat <<USAGE
Usage: bash $0 <step>

steps（每个对应一个函数 / FnF flow）：
  plan         调 factor-plan       LLM 规划因子挖掘路线
  builder      调 factor-builder    LLM 按 plan 生成因子代码
  detect       调 factor-detect     真数据评估因子有效性
  duplicate    调 factor-duplicate  去重 / 相关性聚合
  evaluate     调 factor-evaluate   策略建模评估（最重）
  filter       调 factor-filter     按指标筛选 top-N，出 strategy.toml
  backtest     调 strategy-backtest wbt 综合回测
  realtime     调 vista-realtime    实盘信号（无 cron 版，纯 SDK 调）
  deadletter   调 deadletter        故障兜底（演示，正常由 FnF 触发）

  fnf          ★ 启 research-pipeline FnF flow，端到端跑完 7 步（推荐生产用）
  chain        按顺序串调每个函数（仅演示，FnF 才是正确编排方式）

env：
  FC_ACCESS=prod        必填
  FC_SUFFIX=""          函数名后缀，多环境隔离用
  OSS_BUCKET            生产 bucket，默认 vista-fc-prod
  USER_HASH             默认 u_demo
  WORKSPACE_ID          默认 EXP_DEMO
  RUN_ID                默认 demo-时间戳

示例：
  FC_ACCESS=prod bash $0 plan
  FC_ACCESS=prod bash $0 fnf
  FC_ACCESS=prod USER_HASH=u_alice WORKSPACE_ID=EXP_001 bash $0 fnf
USAGE
    ;;
esac
