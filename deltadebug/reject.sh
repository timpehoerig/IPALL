#!/bin/bash

CNF="$1"

CLAUSES=$(grep -vE '^[[:space:]]*(c|p|%|$)' "$CNF" | grep -c '[0-9]')

if [ "$CLAUSES" -eq 0 ]; then
    exit 1
fi

IPALL="/home/hoerig/repos/IPALL/src/ipall"
DUALIZA="/home/hoerig/repos/IPALL/dualiza/dualiza"

COUNT_IPALL=$("$IPALL" -c "$CNF" 2>/dev/null | tail -1)
COUNT_DUALIZA=$("$DUALIZA" -c "$CNF" 2>/dev/null | tail -1)

if [ "$COUNT_IPALL" != "$COUNT_DUALIZA" ]; then
    # interesting case
    exit 0
else
    exit 1
fi