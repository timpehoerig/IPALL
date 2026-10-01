import argparse
import os
import subprocess
from enum import Enum


def run_cpp(executable: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [executable, *args],  # executable and arguments
        capture_output=True,  # capture stdout and stderr
        text=True             # return strings instead of bytes
    )


def dualiza(path_cnf: str, path_dualiza: str) -> int:
    result = run_cpp(path_dualiza, "-c", path_cnf)
    return int(result.stdout.split("\n")[1])


def fuzz(path_cnf: str, path_cnfuzz: str, size: str) -> None:
    with open(path_cnf, "w") as f:
        f.write(run_cpp(path_cnfuzz, size).stdout)


def ipall(path_cnf: str, path_ipall: str) -> int:
    result = run_cpp(path_ipall, "-c", path_cnf)
    result_lst = result.stdout.split("\n")
    idx = result_lst.index("NUMBER SATISFYING ASSIGNMENTS")
    return int(result_lst[idx + 1])


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Running IPALL on fuzzed or provided CNFs."
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

    return parser


class Color(Enum):
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"


def color(text: str, color: Color) -> str:
    return f"{color.value}{text}{Color.RESET.value}"


def pretty(results: dict[str, int], count: int, count_correct: int, count_false: int, cnf: str) -> None:
    top: str = "count\tverified\tcorrect\tfalse\tdualiza\tipall\tCNF"
    bot: str = f"{count}\t"

    if results["dualiza"] == results["ipall"]:
        bot += f"{color('verified', Color.GREEN)}\t"
    else:
        bot += f"{color('failed  ', Color.RED)}\t"

    bot += f"{color(str(count_correct), Color.GREEN)}\t{color(str(count_false), Color.RED)}\t"
    bot += f"{results['dualiza']}\t{results['ipall']}\t{cnf}"

    print("\033[2J\033[H\n\n" + color(top, Color.MAGENTA) + "\n" + bot)


def check_results(results: dict[str, int], count: int, count_correct: int, count_false: int) -> tuple[int, int, int]:
    if results["dualiza"] == results["ipall"]:
        return count + 1, count_correct + 1, count_false
    return count + 1, count_correct, count_false + 1


if __name__ == "__main__":
    args = parser().parse_args()

    count: int = 0
    count_false: int = 0
    count_correct: int = 0

    def fuzz_with_models() -> int:
        model_count: int = 0
        while model_count == 0:
            fuzz(f"{args.tmpdir}/tmp.cnf", args.cnfuzz, "--tiny")
            model_count = dualiza(f"{args.tmpdir}/tmp_fuzzed.cnf", args.dualiza)
        return model_count

    def run(cnf_path: str) -> dict[str, int]:
        dc = dualiza(cnf_path, args.dualiza)
        ic = ipall(cnf_path, "../src/ipall")
        return {"dualiza": dc, "ipall": ic}

    # create tmp dir if it does not exist
    os.makedirs(args.tmpdir, exist_ok=True)

    if args.cnf != "":
        out = run(args.cnf)
        count, count_correct, count_false = check_results(out, count, count_correct, count_false)
        pretty(out, count, count_correct, count_false, args.cnf)

    if args.directory != "":
        for filename in os.listdir(args.directory):
            if filename.endswith(".cnf"):
                cnf_path = os.path.join(args.directory, filename)
                out = run(cnf_path)
                count, count_correct, count_false = check_results(out, count, count_correct, count_false)
                pretty(out, count, count_correct, count_false, filename)

    if args.cnf == "" and args.directory == "":
        while True:
            dc = fuzz_with_models()
            ic = ipall(f"{args.tmpdir}/tmp_fuzzed.cnf", args.ipall)
            out = {"dualiza": dc, "ipall": ic}
            count, count_correct, count_false = check_results(out, count, count_correct, count_false)
            pretty(out, count, count_correct, count_false, "fuzzed.cnf")
