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
cat > opendaylight.service << EOF
[Unit]
Description=OpenDaylight SDN Controller
Documentation=https://wiki.opendaylight.org/view/Main_Page http://www.opendaylight.org/
After=network.service

[Service]
Type=forking
ExecStart=/opt/opendaylight/bin/start
Environment=_JAVA_OPTIONS='-Djava.net.preferIPv4Stack=true'
User=odl
Group=odl
SuccessExitStatus=143
LimitNOFILE=102400
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
curl --fail --silent -L -O http://artifacts.opnfv.org/apex/random/aaa-cli-jar.jar
python ./odl_reinstaller/odl_reinstaller.py $@
