#!/bin/bash
# SPDX-license-identifier: Apache-2.0
##############################################################################
# Copyright (c) 2018 Ericsson and Others.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
SDNVPN_PLAYBOOKS="$(dirname $(realpath ${BASH_SOURCE[0]}))/playbooks"

echo "Info: Install and Start Quagga process on the localhost"
echo "-----------------------------------------------------------------------"
cd $SDNVPN_PLAYBOOKS
ansible-playbook -v -i "localhost," -c local setup-quagga.yml
echo "-----------------------------------------------------------------------"
echo "Info: Configured localhost host for Quagga"

echo "Info: Configure Quagga with BGP neighbor and VRFs"
echo "-----------------------------------------------------------------------"
(sleep 1;echo "sdncbgpc";sleep 1;cat /tmp/quagga-config;sleep 1; echo "exit") |nc -q1 localhost 2605
echo "Info: Configured Quagga with BGP neighbor and VRFs"