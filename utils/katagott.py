import json, subprocess, threading, queue, os, sys

MODEL = "/Volumes/exdata/katago/models/kata1-b28c512nbt-s10063600896-d5087116207.bin.gz"
CFG   = "/Volumes/exdata/katago/analysis.cfg"
KATAGO_BIN = "katago"  # 如果不在 PATH，请改成全路径，比如 "/opt/homebrew/bin/katago"

# 启动 analysis 引擎
proc = subprocess.Popen(
    [KATAGO_BIN, "analysis", "-model", MODEL, "-config", CFG],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=1
)

# 异步读取 stdout
out_q = queue.Queue()
def reader():
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            out_q.put(json.loads(line))
        except json.JSONDecodeError:
            print("Non-JSON:", line, file=sys.stderr)

threading.Thread(target=reader, daemon=True).start()

# 发请求：空棋盘，黑先，200 visits
req = {
    "id": "q1",
    "rules": "Chinese",
    "komi": 7.5,
    "boardXSize": 19,
    "boardYSize": 19,
    "moves": [],
    "maxVisits": 200,
    "includeOwnership": True,
    "reportPolicy": True
}
proc.stdin.write(json.dumps(req) + "\n")
proc.stdin.flush()

# 读取直到完成
result = None
while True:
    msg = out_q.get()
    result = msg
    if msg.get("isTerminal") or msg.get("isDone"):
        break

# 打印前 5 个推荐着法
infos = result.get("moveInfos", [])[:5]
for i, mv in enumerate(infos, 1):
    print(i, mv["move"],
          "winrate=", round(mv["winrate"]*100, 2),
          "scoreLead=", round(mv.get("scoreLead", 0.0), 2))

# 结束进程
try:
    proc.stdin.close()
except:
    pass
proc.terminate()