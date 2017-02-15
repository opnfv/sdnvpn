#!/bin/bash
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
set -e
export PYTHONPATH=$PYTHONPATH:$DIR
mkdir -p $DIR/tmp
cd $DIR
python ./odl_reinstaller/odl_reinstaller.py $@
