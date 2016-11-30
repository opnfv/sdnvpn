#!/bin/bash
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
if [ -e ~/stackrc ];then
  . ~/stackrc
fi
set -e
export PYTHONPATH=$PYTHONPATH:$DIR
mkdir -p tmp
python tripleo_manager/tripleo_manager.py $@
