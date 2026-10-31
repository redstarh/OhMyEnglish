"""음성 조각을 무음 사이에 놓아 가짜 마이크 입력 wav 를 만든다 (16kHz mono 16bit).
사용: compose.py <out.wav> <item>...   item = 'sil:<초>' | '<raw.wav>'  (raw 는 앞뒤 무음을 잘라 넣음)"""
import array, sys, wave

def load_trim(path):
    with wave.open(path) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2
        a = array.array("h", w.readframes(w.getnframes()))
    idx = [i for i, v in enumerate(a) if abs(v) > 300]
    return a[max(0, idx[0] - 800): idx[-1] + 800] if idx else a

out = array.array("h")
marks = []
for item in sys.argv[2:]:
    if item.startswith("sil:"):
        out.extend([0] * int(float(item[4:]) * 16000))
    else:
        seg = load_trim(item)
        marks.append({"seg": item.rsplit("/", 1)[-1], "start": round(len(out) / 16000, 3), "len": round(len(seg) / 16000, 3)})
        out.extend(seg)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(out.tobytes())
print({"out": sys.argv[1].rsplit("/", 1)[-1], "total": round(len(out) / 16000, 3), "marks": marks})
