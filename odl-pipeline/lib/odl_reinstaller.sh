#!/bin/bash
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
set -e
export PYTHONPATH=$PYTHONPATH:$DIR
mkdir -p tmp
python odl_reinstaller/odl_reinstaller.py $@
