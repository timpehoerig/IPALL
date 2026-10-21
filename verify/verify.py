import argparse
import os
import shutil
import subprocess
import random
import re

from enum import Enum
from dataclasses import dataclass


def run_cpp(executable: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [executable, *args],  # executable and arguments
        capture_output=True,  # capture stdout and stderr
        text=True,           # return strings instead of bytes
        timeout=parse.timeout,     # set a timeout for the process
    )


def run_and_wrap(executable: str, *args: str) -> int:
    """
    Runs a command and returns the number of satisfying assignments.
    If the command times out, returns -1.
    """
    try:
        result = run_cpp(executable, *args)
        result_lst = result.stdout.split("\n")
        idx = result_lst.index("NUMBER SATISFYING ASSIGNMENTS")
        return int(result_lst[idx + 1])

    except subprocess.TimeoutExpired:
        return -1


def generate_options() -> str:
    ignore_options = [
        "chrono",
        "chronoalways",
        "chronostrict",
        "restart",
        "inprocessing",
    ]
    out = ""
    lines = run_cpp(parse.options).stdout.split("\n")
    for line in lines:
        if line == "":
            continue

        option, default, lo, hi = line.split(" ")

        if option in ignore_options:
            continue

        assert option not in ignore_options

        value = random.randint(int(lo), int(hi))

        out += f"c --{option}={value}\n"

    return out


def dualiza(path_cnf: str) -> int:
    return run_and_wrap(parse.dualiza, path_cnf)


def ipall(path_cnf: str) -> int:
    return run_and_wrap(parse.ipall, "-c", path_cnf)


def fuzz(path_cnf: str) -> None:
    with open(path_cnf, "w") as f:
        if parse.options != "":
            f.write(generate_options())
        f.write(run_cpp(parse.cnfuzz, f"--{parse.size}").stdout)


def fuzz_with_models() -> int:
    model_count: int = 0
    cnf: str = f"{parse.tmpdir}/{parse.fuzzname}.cnf"
    while model_count == 0:
        fuzz(cnf)
        model_count = dualiza(cnf)
    return model_count


def run(cnf_path: str) -> dict[str, int]:
    dc = dualiza(cnf_path)
    ic = ipall(cnf_path)
    return {"dualiza": dc, "ipall": ic}


class Status(Enum):
    VERIFIED = 1
    FAILED = 2
    TIMEOUT = 3


def check_results(results: dict[str, int], count: Count) -> Status:
    count.count += 1
    if results["dualiza"] == -1 or results["ipall"] == -1:
        count.timeout += 1
        return Status.TIMEOUT
    if results["dualiza"] == results["ipall"]:
        count.correct += 1
        return Status.VERIFIED
    count.false += 1
    return Status.FAILED


# ############## printing ##############
class Color(Enum):
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    ORANGE = "\033[38;5;208m"
    WHITE = "\033[97m"
    RESET = "\033[0m"

    DUALIZA = "\033[94m"
    IPALL = "\033[96m"


def color(text: str, color: Color) -> str:
    return f"{color.value}{text}{Color.RESET.value}"


def pretty(results: dict[str, int], count: Count, status: Status, cnf: str) -> None:
    if parse.whisper:
        print(f"\rTried: {count.count} fuzzed cnfs", end="", flush=True)
        return
    if parse.silent:
        return

    top: str = f"count\tverified\tcorrect\tfalse\ttimeout\t{color("dualiza", Color.DUALIZA)}\t{color("ipall", Color.IPALL)}\tCNF"
    bot: str = f"{count.count}\t"

    if status is Status.VERIFIED:
        bot += f"{color('verified', Color.GREEN)}\t"
    elif status is Status.TIMEOUT:
        bot += f"{color('timeout ', Color.YELLOW)}\t"
    else:
        bot += f"{color('failed  ', Color.RED)}\t"

    bot += f"{color(str(count.correct), Color.GREEN)}\t{color(str(count.false), Color.RED)}\t{color(str(count.timeout), Color.YELLOW)}\t"
    bot += f"{results['dualiza']}\t{results['ipall']}\t{cnf}"

    options = "Options:"
    if parse.cnf == "" and parse.directory == "":
        options += f" --size {parse.size}"
    options += f" --timeout {parse.timeout}"
    if parse.options != "":
        options += " --options"
    options += "\n"

    print("\033[2J\033[H\n\n" + color(options, Color.ORANGE) + color(top, Color.MAGENTA) + "\n" + bot)


ANSI_ESCAPE = re.compile(r'\033\[[0-9;]*m')


def length(s: str) -> int:
    return len(ANSI_ESCAPE.sub("", s))


@dataclass
class Stats:
    name: str
    status: Status
    dualiza: int
    ipall: int


def pretty_stats(stats: list[Stats]):

    def display(stat: Stats) -> str:
        return f"{stat.name} {color(str(stat.dualiza), Color.DUALIZA)} {color(str(stat.ipall), Color.IPALL)}"

    fail = list(filter(lambda s: s.status == Status.FAILED, stats))
    timeout = list(filter(lambda s: s.status == Status.TIMEOUT, stats))

    max_len = max(len(fail), len(timeout))

    min_len = max(map(lambda s: length(display(s)) if s.status == Status.FAILED else 0, stats)) + 1

    if max_len == 0:
        return

    print(f"\n{color("Fails:", Color.RED)}{" " * min_len}{color("Timeouts:", Color.YELLOW)}")

    for i in range(max_len):

        f = ""
        if i < len(fail):
            f = display(fail[i])

        s = f"  {f}      {" " * (min_len - length(f))}"

        if i < len(timeout):
            s += display(timeout[i])

        print(s)


# ######################################


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Running IPALL on fuzzed or provided CNFs.\nRunning it without any arguments will run it in fuzzing mode."
    )

    parser.add_argument(
        "-c", "--cnf",
        type=str,
        default="",
        help="Path to a CNF file."
    )

    parser.add_argument(
        "-d", "--directory",
        type=str,
        default="",
        help="Path to a directory containing CNF files."
    )

    parser.add_argument(
        "--dualiza",
        type=str,
        default="../dualiza/dualiza",
        help="Path to the dualiza binary."
    )

    parser.add_argument(
        "--cnfuzz",
        type=str,
        default="../cnfuzz/cnfuzz",
        help="Path to the cnfuzz binary."
    )

    parser.add_argument(
        "--tmpdir",
        type=str,
        default="./tmp",
        help="Path to the temporary directory."
    )

    parser.add_argument(
        "--ipall",
        type=str,
        default="../src/ipall",
        help="Path to the ipall binary."
    )

    parser.add_argument(
        "--size",
        type=str,
        default="tiny",
        help="Size of the fuzzed CNF."
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=5000,
        help="Timeout in seconds for each cnf (default=5000)."
    )

    parser.add_argument(
        "--fuzzname",
        type=str,
        default="tmp_fuzzed",
        help="Name of the fuzzed CNF."
    )

    parser.add_argument(
        "--faileddir",
        type=str,
        default="./failed",
        help="Path to the directory where failed CNFs will be stored."
    )

    parser.add_argument(
        "--timeoutdir",
        type=str,
        default="./timeout",
        help="Path to the directory where timeout CNFs will be stored."
    )

    parser.add_argument(
        "--break_on_fail",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Break on first failed CNF."
    )

    parser.add_argument(
        "--silent",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Silent mode."
    )

    parser.add_argument(
        "--whisper",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Only prints the number of runs."
    )

    parser.add_argument(
        "--options",
        type=str,
        default="",
        help="Fuzz options as well (give path to options generate script)."
    )

    parser.add_argument(
        "--amount",
        type=int,
        default=-1,
        help="How many CNFs to fuzz and verify. If not given = infinite"
    )

    parser.add_argument(
        "--summarize",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="At the end print all failed and out timed CNFs"
    )

    return parser


@dataclass
class Count:
    count: int = 0
    correct: int = 0
    false: int = 0
    timeout: int = 0


if __name__ == "__main__":
    global parse

    parse = parser().parse_args()

    count = Count()

    stats = []

    # create tmp dir if it does not exist
    os.makedirs(parse.tmpdir, exist_ok=True)

    if parse.cnf != "":
        out = run(parse.cnf)
        status = check_results(out, count)
        pretty(out, count, status, parse.cnf)

    if parse.directory != "":
        failed: list[str] = []
        for filename in os.listdir(parse.directory):
            if filename.endswith(".cnf"):
                cnf_path = os.path.join(parse.directory, filename)
                out = run(cnf_path)
                status = check_results(out, count)
                pretty(out, count, status, filename)
                if parse.summarize:
                    stats.append(Stats(filename, status, out["dualiza"], out["ipall"]))

        if parse.summarize:
            pretty_stats(stats)

    if parse.cnf == "" and parse.directory == "":
        while parse.amount == -1 or parse.amount > 0:
            dc = fuzz_with_models()
            ic = ipall(f"{parse.tmpdir}/{parse.fuzzname}.cnf")
            out = {"dualiza": dc, "ipall": ic}
            status = check_results(out, count)
            pretty(out, count, status, f"{parse.fuzzname}.cnf")
            if status is Status.FAILED:
                os.makedirs(parse.faileddir, exist_ok=True)
                shutil.copy(f"{parse.tmpdir}/{parse.fuzzname}.cnf", f"{parse.faileddir}/fuzzed_{count.count}_dc{dc}_ic{ic}.cnf")
                if parse.break_on_fail:
                    break
            if status is Status.TIMEOUT:
                os.makedirs(parse.timeoutdir, exist_ok=True)
                shutil.copy(f"{parse.tmpdir}/{parse.fuzzname}.cnf", f"{parse.timeoutdir}/fuzzed_{count.count}_dc{dc}_ic{ic}_timeout.cnf")

            if parse.amount > 0:
                parse.amount -= 1

            if parse.summarize:
                stats.append(Stats(filename, status, dc, ic))

        if parse.summarize:
            pretty_stats(stats)
