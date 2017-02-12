#!/bin/bash
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
export bridges="admin|private|public|storage"
for br in $(ifconfig |grep -v br-external |grep "^br" |grep -E $bridges |awk '{print $1}');do
  sudo ip addr flush dev $br;
done
