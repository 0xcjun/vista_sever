"""One-shot script to build tests/fixtures/duckdb/mini_factors.duckdb.

Run:
  uv run python tests/fixtures/_build_mini_factors.py

Creates 3 symbols x 20 klines x 3 factors ~ small duckdb file suitable for
integration tests (kept under the 500KB pre-commit large-file limit).
"""

from __future__ import annotations

import itertools
import random
from pathlib import Path

import duckdb

OUT = Path(__file__).parent / "duckdb" / "mini_factors.duckdb"
OUT.parent.mkdir(parents=True, exist_ok=True)
if OUT.exists():
    OUT.unlink()

con = duckdb.connect(str(OUT))

con.execute(
    """
    CREATE TABLE factors (
        factor_name VARCHAR PRIMARY KEY,
        route_code VARCHAR,
        creator VARCHAR,
        is_deleted INTEGER DEFAULT 0
    )
    """
)
con.execute(
    """
    CREATE TABLE factor_values (
        factor_name VARCHAR,
        symbol VARCHAR,
        dt TIMESTAMP,
        value DOUBLE
    )
    """
)

con.executemany(
    "INSERT INTO factors VALUES (?, ?, ?, 0)",
    [
        ("f_momentum_5", "R001", "test"),
        ("f_reverse_5", "R001", "test"),
        ("f_rsi_14", "R002", "test"),
    ],
)

random.seed(42)
rows = []
for factor, sym, i in itertools.product(
    ["f_momentum_5", "f_reverse_5", "f_rsi_14"],
    ["SFIF9001.CFE", "SFIC9001.CFE", "SFIH9001.CFE"],
    range(20),
):
    # 20 klines x 15 minutes = 5 hours within a single day
    hour = (i * 15 // 60) % 24
    minute = (i * 15) % 60
    rows.append(
        (
            factor,
            sym,
            f"2026-04-01 {hour:02d}:{minute:02d}:00",
            random.uniform(-1.0, 1.0),
        )
    )

con.executemany("INSERT INTO factor_values VALUES (?, ?, ?, ?)", rows)
con.close()

print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
