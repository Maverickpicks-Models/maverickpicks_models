"""Run an mpm module from Task Scheduler and keep a log of what happened.

  python -m mpm.run oddsapi --league NBA --purpose pregame

Output and any error go to C:\\MaverickPicks\\logs\\YYYY-MM-DD.log (or MPM_LOG_DIR), one block per run,
so a job that fails at 6 PM leaves a trace instead of disappearing.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import os
import runpy
import sys
import traceback


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m mpm.run <module> [args...]")
        return 2
    mod, args = sys.argv[1], sys.argv[2:]
    folder = os.environ.get("MPM_LOG_DIR", r"C:\MaverickPicks\logs")
    os.makedirs(folder, exist_ok=True)
    start = dt.datetime.now()
    buf = io.StringIO()
    code = 0
    sys.argv = [f"mpm.{mod}", *args]
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            runpy.run_module(f"mpm.{mod}", run_name="__main__")
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        except Exception:
            traceback.print_exc()
            code = 1
    status = "OK" if code == 0 else f"FAILED ({code})"
    with open(os.path.join(folder, f"{start:%Y-%m-%d}.log"), "a", encoding="utf-8") as fh:
        fh.write(f"=== {start:%H:%M:%S} mpm.{mod} {' '.join(args)} -> {status} "
                 f"({(dt.datetime.now() - start).total_seconds():.1f}s)\n{buf.getvalue().rstrip()}\n\n")
    print(buf.getvalue(), end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
