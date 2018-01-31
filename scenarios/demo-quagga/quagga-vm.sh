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

echo "Info: Configure External network for Quagga VM"
echo "-----------------------------------------------------------------------"
ovs-vsctl --may-exist add-br br-int \
  -- set Bridge br-int datapath_type=netdev \
  -- br-set-external-id br-int bridge-id br-int \
  -- set bridge br-int fail-mode=standalone

ip netns add n1
ip netns exec n1 ip link set dev lo up

ip link add vn1 type veth peer name peer1
ip link set peer1 netns n1

ip addr add 30.1.1.2/24 dev vn1 
ip link set vn1 up
ip netns exec n1 ip addr add 30.1.1.1/24 dev peer1
ip netns exec n1 ip link set peer1 up
ip netns exec n1 ip link set lo up

ip netns exec n1 ip route add default via 30.1.1.2
# Enable IP-forwarding.
echo 1 > /proc/sys/net/ipv4/ip_forward
echo "Info: External network is configured with IP Network namespace"

ovs-vsctl --may-exist add-br br-phy \
    -- set Bridge br-phy datapath_type=netdev \
    -- br-set-external-id br-phy bridge-id br-phy \
    -- set bridge br-phy fail-mode=standalone \
         other_config:hwaddr=52:54:00:8c:81:a5

ovs-vsctl --timeout 10 add-port br-phy br-vxlan
ip addr add 172.29.240.10/24 dev br-phy
ip link set br-phy up
ip addr flush dev br-vxlan 2>/dev/null
ip link set br-vxlan up

echo "Info: Attach the external network with OVS"
echo "-----------------------------------------------------------------------"
ovs-vsctl add-port br-int vn1
ovs-vsctl add-port br-int gre-tun -- set Interface gre-tun type=gre options:local_ip=172.29.240.10 options:remote_ip=172.29.240.12 options:packet_type=legacy_l3
ovs-ofctl add-flow br-int dl_type=0x800,nw_src=30.1.1.1/32,nw_dst=11.0.1.1/32,actions=push_mpls:0x8847,set_field:0x100-\>mpls_label,output:"gre-tun"
ovs-ofctl add-flow br-int dl_type=0x8847,in_port="gre-tun",actions=pop_mpls:0x800,output:"vn1"
echo "Info: External network is attached to OVS for L3 communication"
