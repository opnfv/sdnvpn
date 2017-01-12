#!/bin/bash
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
if [ -e ~/stackrc ];then
  . ~/stackrc
fi
set -e
export PYTHONPATH=$PYTHONPATH:$DIR
mkdir -p $DIR/tmp
cd $DIR
python ./tripleo_introspector/tripleo_introspector.py $@
