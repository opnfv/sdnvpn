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
ansible-playbook -v -i inventory setup-quagga.yml
echo "-----------------------------------------------------------------------"
echo "Info: Configured localhost host for Quagga"

