#!/usr/bin/env python3
"""Run every replay script against a slot and write the lab-run report.

  python3 tools/replay/run_all.py --slot 1 [--update-fiches]

Each tools/replay/*.py that takes --slot is run with it (and --control where it exists);
its exit code is the verdict: 0 PASS, 1 FAIL, 2 INCONCLUSIVE. The report goes to
docs/lab-runs/<date>.md with the commit, build and per-script output. With
--update-fiches every fiche whose `replay.script` ran gets its `last_run` line rewritten;
a FAIL is printed as a demotion the committer must make (docs/EVIDENCE.md, rule 5) --
the script does not change a status by itself.
"""

import argparse
import datetime
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VERDICT = {0: "PASS", 1: "FAIL", 2: "INCONCLUSIVE"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slot", type=int, required=True)
    parser.add_argument("--update-fiches", action="store_true")
    parser.add_argument("--build", default="coa-extensions-rev4-2026-09-14")
    parser.add_argument("--dataset", default="ascension-live-2026-09-17")
    args = parser.parse_args()

    commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    today = datetime.date.today().isoformat()
    results = []
    for script in sorted(glob.glob(os.path.join(ROOT, "tools", "replay", "*.py"))):
        if os.path.basename(script) == "run_all.py":
            continue
        with open(script, encoding="utf-8") as handle:
            source = handle.read()
        if "--slot" not in source:
            continue
        command = [sys.executable, script, "--slot", str(args.slot)]
        if "--control" in source:
            command.append("--control")
        print(f"running {os.path.relpath(script, ROOT)} ...", flush=True)
        run = subprocess.run(command, capture_output=True, text=True)
        verdict = VERDICT.get(run.returncode, f"exit {run.returncode}")
        print(f"  {verdict}")
        results.append((os.path.relpath(script, ROOT), verdict, run.stdout.strip() + ("\n" + run.stderr.strip() if run.stderr.strip() else "")))

    os.makedirs(os.path.join(ROOT, "docs", "lab-runs"), exist_ok=True)
    report = os.path.join(ROOT, "docs", "lab-runs", f"{today}.md")
    with open(report, "w", encoding="utf-8") as out:
        print(f"# Lab run {today}", file=out)
        print("", file=out)
        print(f"Commit `{commit}`, slot {args.slot}, client build `{args.build}`, dataset `{args.dataset}`.", file=out)
        print("", file=out)
        print("| Script | Verdict |", file=out)
        print("| --- | --- |", file=out)
        for script, verdict, _ in results:
            print(f"| `{script}` | {verdict} |", file=out)
        for script, verdict, output in results:
            print("", file=out)
            print(f"## `{script}` — {verdict}", file=out)
            print("", file=out)
            print("```", file=out)
            print(output, file=out)
            print("```", file=out)
    print(f"report: {os.path.relpath(report, ROOT)}")

    if args.update_fiches:
        by_script = {script: verdict for script, verdict, _ in results}
        for path in glob.glob(os.path.join(ROOT, "protocol", "opcodes", "*.yaml")):
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            m = re.search(r"^replay:\n  script: (\S+)", text, re.M)
            if not m or m.group(1) not in by_script:
                continue
            verdict = by_script[m.group(1)].lower()
            new = re.sub(r"^  last_run: \{[^}]*\}", f"  last_run: {{ date: {today}, result: {verdict}, build: {args.build},\n              dataset: {args.dataset}, slot: {args.slot} }}", text, count=1, flags=re.M | re.S)
            if new != text:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(new)
                if verdict == "fail" and "status: proven" in text:
                    print(f"DEMOTE: {os.path.relpath(path, ROOT)} is proven but its replay failed -- set status/evidence down in this commit")
    return 0 if all(v == "PASS" for _, v, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
