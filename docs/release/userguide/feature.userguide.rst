.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) Tim Irnich, Nikolas Hermanns, Christopher Price and others

Introduction
============
.. Describe the specific features and how it is realised in the scenario in a brief manner
.. to ensure the user understand the context for the user guide instructions to follow.

This document provides an overview of how to work with the SDN VPN features in
OPNFV.

Feature and API usage guidelines and example
============================================
.. Describe with examples how to use specific features, provide API examples and details required to
.. operate the feature on the platform.

For the details of using OpenStack BGPVPN API, please refer to the documentation
at http://docs.openstack.org/developer/networking-bgpvpn/.

Example
-------
In the example we will show a BGPVPN associated to 2 neutron networks.
The BGPVPN will have the import and export routes in the way that it
imports its own Route. The outcome will be that vms sitting on these two
networks will be able to have a full L3 connectivity.


Some defines:
::

 net_1="Network1"
 net_2="Network2"
 subnet_net1="10.10.10.0/24"
 subnet_net2="10.10.11.0/24"

Create neutron networks and save network IDs:
::

 neutron net-create --provider:network_type=local $net_1
 export net_1_id=`echo "$rv" | grep " id " |awk '{print $4}'`
 neutron net-create --provider:network_type=local $net_2
 export net_2_id=`echo "$rv" | grep " id " |awk '{print $4}'`

Create neutron subnets:
::

 neutron subnet-create $net_1 --disable-dhcp $subnet_net1
 neutron subnet-create $net_2 --disable-dhcp $subnet_net2

Create BGPVPN:
::

 neutron bgpvpn-create --route-distinguishers 100:100 --route-targets 100:2530 --name L3_VPN

Start VMs on both networks:
::

 nova boot --flavor 1 --image <some-image> --nic net-id=$net_1_id vm1
 nova boot --flavor 1 --image <some-image> --nic net-id=$net_2_id vm2

The VMs should not be able to see each other.

Associate to Neutron networks:
::

 neutron bgpvpn-net-assoc-create L3_VPN --network $net_1_id
 neutron bgpvpn-net-assoc-create L3_VPN --network $net_2_id

Now the VMs should be able to ping each other

Troubleshooting
===============
Check neutron logs on the controller:
::

 tail -f /var/log/neutron/server.log |grep -E "ERROR|TRACE"

Check Opendaylight logs:
::

 tail -f /opt/opendaylight/data/logs/karaf.log

Restart Opendaylight:
::

 service opendaylight restart
