#!/usr/bin/env python3
"""统一因子代码验证工具

支持时序因子(ts)和截面因子(cs)两类因子代码的静态校验：
- 通用：函数存在性、可调用性、签名包含 df 参数
- 时序专项：未来信息泄露（rank 缺 rolling、负 shift/diff/pct_change/window）
- 截面专项：MultiIndex 使用、groupby('symbol') 误用、sort_index() 缺失

用法：
    python validate_factor.py my_factor.py --type ts
    python validate_factor.py my_factor.py --type cs --factor-name CSE_260406_ABCDEF
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def _check_future_info_leak(code: str) -> list[str]:
    """时序专项：检查未来信息泄露风险，返回问题描述列表。"""
    issues: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            func = node.func
            if isinstance(func, ast.Attribute):
                # rank() 必须紧跟 rolling()
                if func.attr == "rank" and not (
                    isinstance(func.value, ast.Call)
                    and isinstance(func.value.func, ast.Attribute)
                    and func.value.func.attr == "rolling"
                ):
                    issues.append(f"L{node.lineno}: rank() 未与 rolling() 一起使用，存在未来信息泄露风险")

                # shift/diff/pct_change 不允许负参数
                if func.attr in {"shift", "diff", "pct_change"} and node.args:
                    arg = node.args[0]
                    try:
                        value = ast.literal_eval(arg)
                        if isinstance(value, int) and value < 0:
                            issues.append(f"L{node.lineno}: {func.attr}({value}) 使用负参数，会引入未来数据")
                    except (ValueError, SyntaxError):
                        pass

                # rolling(window=负数) 无意义
                if func.attr == "rolling":
                    for kw in node.keywords:
                        if kw.arg == "window":
                            try:
                                value = ast.literal_eval(kw.value)
                                if isinstance(value, int) and value < 0:
                                    issues.append(f"L{node.lineno}: rolling(window={value}) 负窗口无意义")
                            except (ValueError, SyntaxError):
                                pass

            self.generic_visit(node)

    try:
        Visitor().visit(ast.parse(code))
    except SyntaxError as exc:
        issues.append(f"L{exc.lineno}: 语法错误 - {exc.msg}")
    return issues


def _check_cross_section_usage(code: str) -> list[str]:
    """截面专项：检查 MultiIndex/groupby/sort_index 等约定。"""
    issues: list[str] = []

    if ".groupby('symbol')" in code or '.groupby("symbol")' in code:
        issues.append("截面因子误用 groupby('symbol')；横截面应使用 groupby(level='dt') 或 groupby('dt')")

    if ".sort_index()" not in code:
        issues.append("缺少 .sort_index()；截面因子应返回排序后的结果")

    if "groupby('dt')" not in code and "groupby(level='dt')" not in code:
        issues.append("未发现 groupby('dt') 或 groupby(level='dt')，请确认是否在做横截面操作")

    return issues


def _check_function_signature(code: str, factor_name: str | None) -> tuple[str | None, list[str]]:
    """通用：解析代码并校验目标函数的存在性与签名。

    返回 (实际命中的函数名, 问题列表)。
    """
    issues: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return None, [f"L{exc.lineno}: 语法错误 - {exc.msg}"]

    func_defs = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    if not func_defs:
        return None, ["未在代码中发现任何 def 函数定义"]

    target = factor_name if factor_name in func_defs else next(iter(func_defs))
    if factor_name and factor_name not in func_defs:
        issues.append(f"未找到名为 '{factor_name}' 的函数；将退化校验首个函数 '{target}'。可用：{list(func_defs)}")

    func_node = func_defs[target]
    arg_names = [a.arg for a in func_node.args.args]
    if "df" not in arg_names:
        issues.append(f"函数 '{target}' 缺少必需参数 'df'")

    return target, issues


def validate(code: str, factor_type: str, factor_name: str | None) -> tuple[bool, list[str]]:
    """统一校验入口。返回 (是否通过, 问题列表)。"""
    issues: list[str] = []

    target, sig_issues = _check_function_signature(code, factor_name)
    issues.extend(sig_issues)
    if target is None:
        return False, issues

    if factor_type == "ts":
        issues.extend(_check_future_info_leak(code))
    elif factor_type == "cs":
        issues.extend(_check_cross_section_usage(code))
    else:
        issues.append(f"未知 factor_type='{factor_type}'，仅支持 ts/cs")

    has_error = any(
        not msg.startswith(("L", "未找到"))
        and ("缺" in msg or "误用" in msg or "泄露" in msg or "无意义" in msg or "未发现" in msg)
        for msg in issues
    )
    syntax_or_leak = any(msg.startswith("L") and "语法错误" not in msg for msg in issues)
    is_valid = not (has_error or syntax_or_leak or any("语法错误" in msg for msg in issues))
    return is_valid, issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Vista Python 因子代码统一验证工具（ts/cs）")
    parser.add_argument("code_file", help="因子代码文件路径")
    parser.add_argument("--type", dest="factor_type", choices=["ts", "cs"], required=True, help="因子类型")
    parser.add_argument("--factor-name", default=None, help="函数名（默认取文件名 stem 或代码中首个函数）")
    args = parser.parse_args()

    code_path = Path(args.code_file)
    if not code_path.exists():
        print(f"❌ 文件不存在: {args.code_file}")
        sys.exit(2)

    code = code_path.read_text(encoding="utf-8")
    factor_name = args.factor_name or code_path.stem
    is_valid, issues = validate(code, args.factor_type, factor_name)

    label = factor_name or "<unknown>"
    if is_valid:
        print(f"✅ 因子 '{label}' ({args.factor_type}) 验证通过")
        if issues:
            print("\n提示：")
            for msg in issues:
                print(f"  - {msg}")
    else:
        print(f"❌ 因子 '{label}' ({args.factor_type}) 验证失败")
        for msg in issues:
            print(f"  - {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
