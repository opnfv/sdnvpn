#!/bin/bash
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
set -e
cd "$( dirname "${BASH_SOURCE[0]}" )"
sudo ifdown enp0s4 2&>1 >> /dev/null /dev/null || true
sudo ifdown enp0s6 2&>1 >> /dev/null /dev/null || true
sudo cp ../templates/ifcfg-* /etc/network/interfaces.d/
sudo ifup enp0s4
sudo ifup enp0s6