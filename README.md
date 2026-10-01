# IPALL - A model enumerator without Blocking Clauses using IPASIR-UP

A very simple model enumerator.
Only calls the solver through the IPASIR-UP interface.
This does not implement implicant shrinking as it requires more functionality than IPASIR-UP provides.

For more theory and information check: [CaDiCAll](https://github.com/timpehoerig/CaDiCAll)
A default IPALL call corresponds to CaDiCAlls "-r" option.

## USAGE:

1. Compile your solver. For CaDiCaL:

Move to 'cadical' and run `./configure && make`

2. Compile IPALL:

Run `make` on this level to compile all, run `make clean` to clean up all files produced by `make` and the execution of either.

## USAGE: IPALL:

Move to `src`.

Run `./ipall --help`.
