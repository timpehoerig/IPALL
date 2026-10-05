import subprocess
import glob
import os


def find_failed_cnf():
    subprocess.run(
        ["python3", "../verify/verify.py", "--size", "small", "--timeout", "60", "--break_on_fail", "True", "--faileddir", "./tmp_failed", "--timeoutdir", "./tmp_timeout", "--silent", "True"],
        timeout=180,
    )


def deltadebug(cnf: str):
    subprocess.run(
        ["../cnfdd/cnfdd", cnf, "./dd.cnf", "./reject.sh"],
        timeout=3600,
    )


if __name__ == "__main__":
    print("Starting find.py...")
    while True:
        try:
            print("Finding failed CNF...")
            find_failed_cnf()
        except subprocess.TimeoutExpired:
            print("Timeout expired while finding failed CNF.")
            continue

        print("Found failed CNF, getting path...")

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
