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

export ODL_IP_ADDRESS=$1
export ODL_GRE_ENDPOINT_IP_ADDRESS=$2
export TENANT_VM_IP_PREFIX=$3
export TENANT_VM_IP_LABEL=$4

export QUAGGA_IP_ADDRESS="$(ifconfig br-mgmt | grep 'inet addr:' | cut -d: -f2 | awk '{print $1}')"
export NEXTHOP_IP_ADDRESS="$(ifconfig br-vxlan | grep 'inet addr:' | cut -d: -f2 | awk '{print $1}')"

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

br_vxlan_mac_address="$(ifconfig br-vxlan | grep -o -E '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}')"

ovs-vsctl --may-exist add-br br-phy \
    -- set Bridge br-phy datapath_type=netdev \
    -- br-set-external-id br-phy bridge-id br-phy \
    -- set bridge br-phy fail-mode=standalone \
         other_config:hwaddr="$br_vxlan_mac_address"

ovs-vsctl --timeout 10 add-port br-phy br-vxlan
ip addr add "$NEXTHOP_IP_ADDRESS"/24 dev br-phy
ip link set br-phy up
ip addr flush dev br-vxlan 2>/dev/null
ip link set br-vxlan up

src_mac_address="$(ifconfig vn1 | grep -o -E '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}')"
dst_mac_address="$(ip netns exec n1 ifconfig peer1 | grep -o -E '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}')"

echo "Info: Attach the external network with OVS"
echo "-----------------------------------------------------------------------"
ovs-vsctl add-port br-int vn1
ovs-vsctl add-port br-int gre-tun -- set Interface gre-tun type=gre options:local_ip="$NEXTHOP_IP_ADDRESS" options:remote_ip="$ODL_GRE_ENDPOINT_IP_ADDRESS" options:packet_type=legacy_l3
ovs-ofctl add-flow br-int dl_type=0x800,nw_src=30.1.1.1/32,nw_dst="$TENANT_VM_IP_PREFIX"/32,actions=push_mpls:0x8847,set_field:"$TENANT_VM_IP_LABEL"-\>mpls_label,output:"gre-tun"
ovs-ofctl add-flow br-int dl_type=0x8847,in_port="gre-tun",actions=pop_mpls:0x800,set_field:"$src_mac_address"-\>dl_src,set_field:"$dst_mac_address"-\>dl_dst,output:"vn1"
echo "Info: External network is attached to OVS for L3 communication"
