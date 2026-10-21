import subprocess
import glob
import os
import argparse


def find_failed_cnf():
    args = ["python3", "../verify/verify.py", "--size", str(parse.size), "--timeout", str(parse.timeout), "--break_on_fail", "--faileddir", "./tmp_failed", "--timeoutdir", "./tmp_timeout", "--whisper"]
    if parse.options != "":
        args.append("--options")
        args.append(parse.options)
    return subprocess.run(
        args,
        timeout=180,
    )


def deltadebug(cnf: str):
    subprocess.run(
        ["../cnfdd/cnfdd", cnf, "./dd.cnf", "./reject.sh"],
        timeout=3600,
    )


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Running IPALL on fuzzed or provided CNFs.\nRunning it without any arguments will run it in fuzzing mode."
    )

    parser.add_argument(
        "--size",
        type=str,
        default="small",
        help="size",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="timeout in sec for single cnf fuzz",
    )

    parser.add_argument(
        "--options",
        type=str,
        default="../../cadical/scripts/generate-options-range-list.sh",
        help="script to generate options (disable by giving --options '')",
    )

    return parser


if __name__ == "__main__":
    parse = parser().parse_args()

    print("Starting find.py...")
    while True:
        try:
            print("Finding failed CNF...")
            find_failed_cnf()
        except subprocess.TimeoutExpired:
            print("\nTimeout expired while finding failed CNF.")
            continue

        print("\nFound failed CNF, getting path...")

        cnfs = glob.glob("./tmp_failed/*.cnf")
        if len(cnfs) == 0:
            print("No failed CNF found.")
            continue
        cnf = cnfs[0]

        print(f"Found path CNF: {cnf}")

        try:
            print(f"Delta debugging {cnf}...")
            deltadebug(cnf)
        except subprocess.TimeoutExpired:
            print("Timeout expired while delta debugging.")
            print(f"Removing {cnf}...")
            os.remove(cnf)
            continue
        print("Delta debugging complete. CNF saved as dd.cnf")
        break
