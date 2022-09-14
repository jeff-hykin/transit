#!/usr/bin/env bash

result_file="./tests/cli_tests/$(basename "$(dirname "$0")")/$(basename "$0").1.result"

python3 ./src/transit.py resampling \
    -c ./src/pytransit/data/cholesterol_glycerol_combined.dat \
    ./src/pytransit/data/samples_metadata_cg.txt \
    Glycerol \
    Cholesterol \
    ./src/pytransit/genomes/H37Rv.prot_table \
    "$result_file"