# queue_run.py
import re, subprocess, sys, pathlib

md = pathlib.Path("repos.md").read_text(encoding="utf-8")
urls = re.findall(r"https://github\.com/[^\s)]+", md)

pathlib.Path("logs").mkdir(exist_ok=True)
for u in urls:
    owner_repo = "-".join(u.rstrip(")").split("/")[-2:])
    log = pathlib.Path("logs") / f"{owner_repo}.log"
    # swap "lmstxt" with "lmstudio-llmstxt" if that's your installed CLI
    cmd = ["lmstxt", u]
    print(">>", " ".join(cmd))
    with log.open("w", encoding="utf-8") as fh:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        fh.write(p.stdout)
        sys.stdout.write(p.stdout)
        sys.stdout.flush()
    if p.returncode != 0:
        print(f"[error] failed for {u} (see {log})")
