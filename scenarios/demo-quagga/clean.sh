#!/bin/bash
# SPDX-license-identifier: Apache-2.0
##############################################################################
# Copyright (c) 2018 Ericsson and Others.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

echo "Info: Stop the BGPD process and remove the Quagga packages"
echo "-----------------------------------------------------------------------"
kill -9 `ps -aef | grep 'bgpd' | grep -v grep | awk '{print $2}'`

dpkg -r thrift
dpkg -r zrpc
dpkg -r quagga
dpkg -r zmq
dpkg -r c-capnproto
dpkg --purge zrpc
dpkg --purge c-capnproto
dpkg --purge zmq
dpkg --purge thrift
dpkg --purge quagga

rm -rf /opt/quagga
echo "Info: Quagga is cleaned up successfully"

echo "Info: Clean up the OVS configuration"
echo "-----------------------------------------------------------------------"
ovs-vsctl del-port br-int vn1
ovs-vsctl del-port br-int gre-tun
ovs-vsctl del-br br-int

/etc/init.d/openvswitch-switch stop

dpkg -r openvswitch-switch
dpkg --purge openvswitch-switch
echo "Info: OVS configuration is cleaned up successfully"

echo "Info: Delete the network namespace configuation"
echo "-----------------------------------------------------------------------"
ip netns delete n1
echo "Info: Deleted the network namespace configuation"

