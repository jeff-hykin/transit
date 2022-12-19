#!/usr/bin/env bash

result_file="./tests/cli_tests/$(basename "$(dirname "$0")")/$(basename "$0").1.result"
annotation="./src/pytransit/data/genomes/H37Rv.prot_table"
metadata="./src/pytransit/data/cholesterol_glycerol.transit/metadata.tsv"
comwig="./src/pytransit/data/cholesterol_glycerol.transit/comwig.tsv"

python3 ./src/transit.py ttnfitness \
    "./src/pytransit/data/cholesterol_glycerol.transit/glycerol_rep1.wig,./src/pytransit/data/cholesterol_glycerol.transit/glycerol_rep2.wig" \
    ./src/pytransit/data/genomes/H37Rv.prot_table \
    ./src/pytransit/data/genomes/H37Rv.fna \
    ./tests/cli_tests/gumbel/0001_basic.sh.1.result \
    "$result_file.genes" \
    "$result_file.sites"