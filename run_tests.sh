#!/bin/bash

export PYTHONPATH=$PYTHONPATH:$PWD/nozzle/

python -m unittest discover ./tests/integration/db/

find -name "*.pyc" | xargs rm -f
