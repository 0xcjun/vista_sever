#!/usr/bin/env python3
"""统一算子获取工具

支持 ts (时序) / cs (截面) 两类算子的随机抽取与列举：

- ts: 从 fix_params_operates 模块抽取预优化参数算子（带标签/前缀过滤）
- cs: 从 cs_operators.py 源码 AST 提取截面算子签名（按函数名/模式识别）

用法：
    python get_operators.py --type ts --num 10
    python get_operators.py --type ts --tag 趋势 --num 5
    python get_operators.py --type ts --prefix RSI --num 3
    python get_operators.py --type ts --list-tags
    python get_operators.py --type cs --num 10
    python get_operators.py --type cs --list
"""

from __future__ import annotations

import argparse
import ast
import random
import sys
from pathlib import Path

# 同目录加入 sys.path 以便 import 同级 fix_params_operates 模块
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))


# =============================================================================
# 时序算子 (ts) - 基于 fix_params_operates
# =============================================================================


def _ts_random_operators(
    num: int = 10,
    with_code: bool = True,
    tag_filter: str | None = None,
    prefix_filter: str | None = None,
    include_mar: bool = True,
) -> str:
    """从 fix_params_operates 随机抽取时序算子。"""
    try:
        from fix_params_operates import (  # type: ignore[import-not-found]
            FIXED_OPERATORS,
            get_operator,
            get_operators_by_prefix,
            get_operators_by_tag,
        )
    except ImportError:
        return "错误: 无法导入同目录 fix_params_operates 模块"

    if tag_filter:
        candidates = get_operators_by_tag(tag_filter)
    elif prefix_filter:
        candidates = get_operators_by_prefix(prefix_filter)
    else:
        candidates = list(FIXED_OPERATORS)

    if not candidates:
        return f"错误: 未找到匹配算子 (tag={tag_filter}, prefix={prefix_filter})"

    samples = random.sample(candidates, min(num, len(candidates)))
    if include_mar:
        mar = get_operator("MAR")
        if mar and mar not in samples:
            samples.append(mar)

    lines = []
    for op in samples:
        tags_str = f" [{','.join(op.tags)}]" if op.tags else ""
        if with_code:
            lines.append(f"- {op.name}:{op.desc}{tags_str};{op.code}")
        else:
            lines.append(f"- {op.name}:{op.desc}{tags_str}")
    return "\n".join(lines)


def _ts_list_tags() -> str:
    try:
        from fix_params_operates import FIXED_OPERATORS  # type: ignore[import-not-found]
    except ImportError:
        return "错误: 无法导入同目录 fix_params_operates 模块"

    tags: set[str] = set()
    for op in FIXED_OPERATORS:
        tags.update(op.tags)
    return "可用标签:\n" + "\n".join(f"  - {t}" for t in sorted(tags))


# =============================================================================
# 截面算子 (cs) - 基于 cs_operators.py 源码 AST 解析
# =============================================================================


_CS_NAME_HINTS = (
    "rank",
    "zscore",
    "scale",
    "quantile",
    "bucket",
    "vec_",
    "group_",
    "regression_neut",
    "vector_neut",
    "winsorize",
)
_TS_NAME_HINTS = ("ts_", "adv", "past")
_CS_GROUPBY_PATTERNS = (
    "groupby('dt')",
    'groupby("dt")',
    "groupby(level='dt')",
    'groupby(level="dt")',
    "groupby(level=0)",
)
_TS_GROUPBY_PATTERNS = (
    "groupby('symbol')",
    'groupby("symbol")',
    "groupby(level='symbol')",
    'groupby(level="symbol")',
    "groupby(level=1)",
)


def _is_cs_operator(source: str | None, name: str) -> bool:
    """识别截面算子：按函数名前缀 + 源码中的 groupby 模式。"""
    if not source:
        return False
    name_lower = name.lower()

    if any(name_lower.startswith(p) for p in _TS_NAME_HINTS):
        return False
    if any(p in name_lower for p in _CS_NAME_HINTS):
        return True

    if any(p in source for p in _TS_GROUPBY_PATTERNS):
        return False
    if any(p in source for p in _CS_GROUPBY_PATTERNS):
        return True
    return False


def _cs_extract_operators() -> dict[str, dict]:
    """从同目录 cs_operators.py 源码提取截面算子元数据。"""
    cs_path = SCRIPTS_DIR / "cs_operators.py"
    if not cs_path.exists():
        raise FileNotFoundError(f"未找到 {cs_path}")

    source_code = cs_path.read_text(encoding="utf-8")
    tree = ast.parse(source_code)

    operators: dict[str, dict] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_source = ast.get_source_segment(source_code, node)
            if not _is_cs_operator(func_source, node.name):
                continue
            operators[node.name] = {
                "docstring": ast.get_docstring(node),
                "source": func_source,
                "args": [a.arg for a in node.args.args],
            }
    return operators


_CS_DESC_MAP = {
    "rank": "截面排名（百分比）",
    "zscore": "标准化（Z-score）",
    "scale": "资金分配缩放",
    "quantile": "分位数转换",
    "group_rank": "分组排名",
    "group_zscore": "分组标准化",
    "group_normalize": "分组归一化",
    "winsorize": "极端值处理（缩尾）",
    "regression_neut": "回归中性化",
    "vector_neut": "向量正交化",
    "bucket": "分桶操作",
}


def _cs_describe(name: str, meta: dict) -> str:
    if meta.get("docstring"):
        first = meta["docstring"].strip().split("\n")[0]
        if first and not first.startswith('"""'):
            return first
    name_lower = name.lower()
    for key, desc in _CS_DESC_MAP.items():
        if key in name_lower:
            return desc
    if name.startswith("group_"):
        return f"分组操作：{name}"
    if name.startswith("vec_"):
        return f"截面操作：{name}"
    return f"算子：{name}"


def _cs_example(name: str, meta: dict) -> str:
    args = meta.get("args", [])
    if "group" in name.lower() and len(args) >= 2:
        return f"{name}(df['field'], df['industry'])"
    if name == "scale":
        return f"{name}(df['factor'], scale=1, longscale=1, shortscale=1)"
    if name in {"regression_neut", "vector_neut"}:
        return f"{name}(df['y'], df['x'])"
    return f"{name}(df['field'])"


def _cs_random_operators(num: int = 10, with_code: bool = True) -> str:
    operators = _cs_extract_operators()
    if not operators:
        return "未找到截面算子"

    names = list(operators.keys())
    samples = random.sample(names, min(num, len(names)))
    lines = []
    for name in sorted(samples):
        desc = _cs_describe(name, operators[name])
        if with_code:
            lines.append(f"- {name}:{desc};{_cs_example(name, operators[name])}")
        else:
            lines.append(f"- {name}:{desc}")
    return "\n".join(lines)


def _cs_list_all() -> str:
    operators = _cs_extract_operators()
    lines = [f"找到 {len(operators)} 个截面算子："]
    for name in sorted(operators):
        lines.append(f"- {name}: {_cs_describe(name, operators[name])}")
    return "\n".join(lines)


# =============================================================================
# CLI 入口
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vista Python 因子算子统一获取工具（ts/cs）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 时序：随机 10 个固定参数算子
  python get_operators.py --type ts --num 10

  # 时序：按标签 / 前缀过滤
  python get_operators.py --type ts --tag 趋势 --num 5
  python get_operators.py --type ts --prefix RSI --num 3
  python get_operators.py --type ts --list-tags

  # 截面：随机 10 个 cs_operators 算子
  python get_operators.py --type cs --num 10
  python get_operators.py --type cs --list
""",
    )
    parser.add_argument("--type", dest="op_type", choices=["ts", "cs"], required=True)
    parser.add_argument("--num", type=int, default=10)
    parser.add_argument("--no-code", action="store_true", help="不输出示例代码")

    # ts 专用
    parser.add_argument("--tag", help="ts: 按标签过滤")
    parser.add_argument("--prefix", help="ts: 按前缀过滤")
    parser.add_argument("--no-mar", action="store_true", help="ts: 不强制包含 MAR 算子")
    parser.add_argument("--list-tags", action="store_true", help="ts: 列出所有可用标签")

    # cs 专用
    parser.add_argument("--list", action="store_true", help="cs: 列出全部截面算子")

    args = parser.parse_args()
    with_code = not args.no_code

    if args.op_type == "ts":
        if args.list_tags:
            print(_ts_list_tags())
            return
        print(
            _ts_random_operators(
                num=args.num,
                with_code=with_code,
                tag_filter=args.tag,
                prefix_filter=args.prefix,
                include_mar=not args.no_mar,
            )
        )
    else:  # cs
        if args.list:
            print(_cs_list_all())
            return
        print(_cs_random_operators(num=args.num, with_code=with_code))


if __name__ == "__main__":
    main()
