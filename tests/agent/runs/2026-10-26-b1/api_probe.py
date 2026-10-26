"""S7 · S6(API) · S8 API 탐침 (회차 2026-10-26-b1). 표준 라이브러리만 씀.

사용: python3 -I api_probe.py <단계> — 단계마다 응답 전문을 표준 출력에 찍음.
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8002/api/course"


def call(method: str, path: str, body: bytes | None = None, ctype: str | None = None) -> tuple[int, str]:
    request = urllib.request.Request(BASE + path, data=body, method=method)
    if ctype:
        request.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def show(label: str, method: str, path: str, body: bytes | None = None, ctype: str | None = None) -> int:
    status, text = call(method, path, body, ctype)
    size = "none" if body is None else f"{len(body)}B"
    print(f"== {label} :: {method} {path} body={size} ctype={ctype}")
    print(f"HTTP {status}")
    print(text if len(text) < 2000 else text[:2000] + "...(truncated)")
    return status


def s7() -> None:
    pcm = b"\x00" * 3200
    show("valid key + 3200B PCM", "POST", "/sentences/u001-s1/attempts", pcm, "application/octet-stream")
    show("unknown key u999-s1", "POST", "/sentences/u999-s1/attempts", pcm, "application/octet-stream")
    show("empty body", "POST", "/sentences/u001-s1/attempts", b"", "application/octet-stream")
    show("odd length 3201B", "POST", "/sentences/u001-s1/attempts", b"\x00" * 3201, "application/octet-stream")
    show("over max 30s+ (960002B)", "POST", "/sentences/u001-s1/attempts", b"\x00" * 960002, "application/octet-stream")
    show("unknown key + empty body", "POST", "/sentences/u999-s1/attempts", b"", "application/octet-stream")
    body = json.dumps({"position_sec": 0, "unit": 5, "sentence_index": 0}).encode()
    show("day2 progress unit 5", "POST", "/days/2/progress", body, "application/json")
    body = json.dumps({"position_sec": 0, "unit": 22, "sentence_index": 5}).encode()
    show("day2 progress sentence_index 5", "POST", "/days/2/progress", body, "application/json")
    body = json.dumps({"position_sec": -1, "unit": 22, "sentence_index": 0}).encode()
    show("day2 progress position -1", "POST", "/days/2/progress", body, "application/json")
    body = json.dumps({"position_sec": 0, "unit": 22, "sentence_index": 0}).encode()
    show("day 7 progress", "POST", "/days/7/progress", body, "application/json")
    show("GET day 7", "GET", "/days/7")
    show("GET day 0", "GET", "/days/0")


def s8() -> None:
    body = json.dumps({"position_sec": 0, "unit": 101, "sentence_index": 0, "completed": True}).encode()
    show("day6 completed", "POST", "/days/6/progress", body, "application/json")
    show("GET course after", "GET", "")


def day2() -> None:
    status, text = call("GET", "/days/2")
    data = json.loads(text)
    print("HTTP", status, "progress", data["progress"])


def post_progress() -> None:
    day, unit, index, pos = (int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]))
    body = json.dumps({"position_sec": pos, "unit": unit, "sentence_index": index}).encode()
    show(f"day{day} progress", "POST", f"/days/{day}/progress", body, "application/json")


if __name__ == "__main__":
    {"s7": s7, "s8": s8, "day2": day2, "post": post_progress}[sys.argv[1]]()
