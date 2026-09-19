#!/usr/bin/env python3
"""B3 회차용 DB 질의 헬퍼. psql_cli.psql 하나만 쓴다."""
import sys

sys.path.insert(0, "/Users/redstar/MyProject/OhMyEnglish/tests/harness")
from psql_cli import psql  # noqa: E402

if __name__ == "__main__":
    sql = sys.stdin.read() if sys.argv[1:] == ["-"] else sys.argv[1]
    print(psql(sql))
