"""Usage: python -m qa.run core [flow ...]   (each name = qa/suite_<name>.py)"""
import importlib
import os
import sys
import time

from qa import harness as H


def main(names):
    t0 = time.time()
    H.PARTIAL_NAME = "partial_" + "_".join(names)
    H.start()
    try:
        for n in names:
            importlib.import_module(f"qa.suite_{n}")
        H.run_all(os.environ.get("QA_ONLY"))
    finally:
        print("cleanup ...", flush=True)
        try:
            summary = H.cleanup()
            print("cleanup done:", summary, flush=True)
            H.S["cleanup"] = summary
        finally:
            H.stop()
    tag = "_".join(names) + ("_only" if os.environ.get("QA_ONLY") else "")
    H.save(f"results_{tag}")
    total = len(H.RESULTS)
    passed = sum(1 for r in H.RESULTS if r["result"] == "PASS")
    print(f"\n== {passed}/{total} PASS in {time.time() - t0:.0f}s ==")
    for r in H.RESULTS:
        if r["result"] != "PASS":
            print(f"  FAIL {r['id']}: {r['actual'][:400]}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["core"])
