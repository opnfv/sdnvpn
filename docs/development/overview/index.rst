.. _sdnvpn-overview:

.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) Tim Irnich, (tim.irnich@ericsson.com) and others

=======
SDN VPN
=======

A high-level description of the scenarios is provided in this section.
For details of the scenarios and their provided capabilities refer to
the scenario description document:
http://artifacts.opnfv.org/danube/sdnpvn/scenarios/os-odl_l2-bgpvpn/index.html

The BGPVPN feature enables creation of BGP VPNs on the Neutron API according to the OpenStack
BGPVPN blueprint at https://blueprints.launchpad.net/neutron/+spec/neutron-bgp-vpn.
In a nutshell, the blueprint defines a BGPVPN object and a number of ways
how to associate it with the existing Neutron object model, as well as a unique
definition of the related semantics. The BGPVPN framework supports a backend
driver model with currently available drivers for Bagpipe, OpenContrail, Nuage
and OpenDaylight. The OPNFV scenario makes use of the OpenDaylight driver and backend
implementation through the ODL NetVirt project.

====================
SDNVPN Testing Suite
====================

An overview of the SDNVPN Test is depicted here. More details for each test case are provided:
https://wiki.opnfv.org/display/sdnvpn/SDNVPN+Testing

    BGPVPN Tempest test cases
        Create BGPVPN passes
        Create BGPVPN as non-admin fails
        Delete BGPVPN as non-admin fails
        Show BGPVPN as non-owner fails
        List BGPVPNs as non-owner fails
        Show network associated BGPVPNs as non-owner fails
        List network associated BGPVPNs as non-owner fails
        Associate/Deassociate a network to a BGPVPN resource passes
        Update route targets on a BGPVPN passes
        Update route targets on a BGPVPN as non-admin fails
        Reject the creation of BGPVPN with invalid route targets passes
        Reject the update of BGPVPN with invalid route targets passes
        Reject the association on an invalid network to a BGPVPN passes
        Reject the diassociation on an invalid network to a BGPVPN passes
        Associate/Deassociate a router to a BGPVPN resource passes
        Attach the subnet of an associated network to an associated router of the same BGVPN passes



    Functest scenario specific tests:

    Test Case 1 - VPN provides connectivity between subnets, using network association
    Name: VPN connecting Neutron networks and subnets
    Description: VPNs provide connectivity across Neutron networks and subnets if configured accordingly.

    Test setup procedure:
    Set up VM1 and VM2 on Node1 and VM3 on Node2, all having ports in the same Neutron Network N1
    Moreover all ports have 10.10.10/24 addresses (this subnet is denoted SN1 in the following)
    Set up VM4 on Node1 and VM5 on Node2, both having ports in Neutron Network N2
    Moreover all ports have 10.10.11/24 addresses (this subnet is denoted SN2 in the following)

    Test execution:
        Create VPN1 with eRT<>iRT (so that connected subnets should not reach each other)
        Associate SN1 to VPN1
        Ping from VM1 to VM2 should work
        Ping from VM1 to VM3 should work
        Ping from VM1 to VM4 should not work
        Associate SN2 to VPN1
        Ping from VM4 to VM5 should work
        Ping from VM1 to VM4 should not work (disabled until isolation fixed upstream)
        Ping from VM1 to VM5 should not work (disabled until isolation fixed upstream)
        Change VPN 1 so that iRT=eRT
        Ping from VM1 to VM4 should work
        Ping from VM1 to VM5 should work

    Test Case 2 - tenant separation
    Name: Using VPNs for tenant separation
    Description: Using VPNs to isolate tenants so that overlapping IP address ranges can be used

    Test setup procedure:
    Set up VM1 and VM2 on Node1 and VM3 on Node2, all having ports in the same Neutron Network N1.
    VM1 and VM2 have IP addresses in a subnet SN1 with range 10.10.10/24
        VM1: 10.10.10.11, running an HTTP server which returns "I am VM1" for any HTTP request
        (or something else than an HTTP server)
        VM2: 10.10.10.12, running an HTTP server which returns "I am VM2" for any HTTP request
    VM3 has an IP address in a subnet SN2 with range 10.10.11/24
        VM3: 10.10.11.13, running an HTTP server which returns "I am VM3" for any HTTP request
    Set up VM4 on Node1 and VM5 on Node2, both having ports in Neutron Network N2
    VM4 has an address in a subnet SN1b with range 10.10.10/24
        VM4: 10.10.10.12 (the same as VM2), running an HTTP server which returns "I am VM4" for any HTTP request
    VM5 has an address in a subnet SN2b with range 10.10.11/24
        VM5: 10.10.11.13 (the same as VM3), running an HTTP server which returns "I am VM5" for any HTTP request

    Test execution:
        Create VPN 1 with iRT=eRT=RT1 and associate N1 to it
        HTTP from VM1 to VM2 and VM3 should work
            It returns "I am VM2" and "I am VM3" respectively
        HTTP from VM1 to VM4 and VM5 should not work
            It never returns "I am VM4" or "I am VM5"
        Create VPN2 with iRT=eRT=RT2 and associate N2 to it
        HTTP from VM4 to VM5 should work
            It returns "I am VM5"
        HTTP from VM4 to VM1 and VM3 should not work
            It never returns "I am VM1" or "I am VM3"


    Test Case 3 - Data Center Gateway integration
    Name: Data Center Gateway integration
    Description: Investigate the peering functionality of BGP protocol,
    using a Zrpcd/Quagga router and OpenDaylight Controller

    Test setup procedure:
    Search in the pool of nodes and find one Compute node and one Controller nodes, that have OpenDaylight controller running
    Start an instance using ubuntu-16.04-server-cloudimg-amd64-disk1.img image and in it run the Quagga setup script
    Start bgp router in the Controller node, using odl:configure-bgp

    Test execution:
    Set up a Quagga instance in a nova compute node
    Start a BGP router with OpenDaylight in a controller node
    Add the Quagga running in the instance as a neighbor
    Check that bgpd is running
    Verify that the OpenDaylight and gateway Quagga peer each other
    Start an instance in a second  nova compute node and connect it with a new network, (Network 3-3).
    Create a bgpvpn (include parameters route-distinguisher and route-targets) and associate it with the network created
    Define the same route-distinguisher and route-targets on the simulated quagga side
    Check that the routes from the Network 3-3 are advertised towards simulated Quagga VM

    Test Case 4 - VPN provides connectivity between subnets using router association
    Functest: variant of Test Case 1.
    Set up a Router R1 with one connected network/subnet N1/S1.
    Set up a second network N2.
    Create VPN1 and associate Router R1 and Network N2 to it.
        Hosts from N2 should be able to reach hosts in N1.

    Name: VPN connecting Neutron networks and subnets using router association
    Description: VPNs provide connectivity across Neutron networks and subnets if configured accordingly.

    Test setup procedure:
    Set up VM1 and VM2 on Node1 and VM3 on Node2,
    All VMs have ports in the same Neutron Network N1 and 10.10.10/24 addresses
    (this subnet is denoted SN1 in the following).
    N1/SN1 are connected to router R1.
    Set up VM4 on Node1 and VM5 on Node2,
    Both VMs have ports in Neutron Network N2 and having 10.10.11/24 addresses
    (this subnet is denoted SN2 in the following)

    Test execution:
    Create VPN1 with eRT<>iRT (so that connected subnets should not reach each other)
    Associate R1 to VPN1
        Ping from VM1 to VM2 should work
        Ping from VM1 to VM3 should work
        Ping from VM1 to VM4 should not work
     Associate SN2 to VPN1
        Ping from VM4 to VM5 should work
        Ping from VM1 to VM4 should not work
        Ping from VM1 to VM5 should not work
    Change VPN1 so that iRT=eRT
        Ping from VM1 to VM4 should work
        Ping from VM1 to VM5 should work

    Test Case 7 - Network associate a subnet with a router attached to a VPN and
    verify floating IP functionality (disabled, because of ODL Bug 6962)

    A test for https://bugs.opendaylight.org/show_bug.cgi?id=6962

    Setup procedure:
    Create VM1 in a subnet with a router attached.
    Create VM2 in a different subnet with another router attached.
    Network associate them to a VPN with iRT=eRT
    Ping from VM1 to VM2 should work
    Assign a floating IP to VM1
    Pinging the floating IP should work

    Test Case 8 - Router associate a subnet with a router attached to a VPN and
    verify floating IP functionality

    Setup procedure:
    Create VM1 in a subnet with a router which is connected with the gateway
    Create VM2 in a different subnet without a router attached.
    Assoc the two networks in a VPN iRT=eRT
    One with router assoc, other with net assoc
    Try to ping from one VM to the other
    Assign a floating IP to the VM in the router assoc network
    Ping it

    Test Case 9 - Check fail mode in OVS br-int interfaces
    This testcase checks if the fail mode is always “secure”.
    To accomplish it, a check is performed on all OVS br-int interfaces, for all OpenStack nodes.
    The testcase is considered as successful if all OVS br-int interfaces have fail_mode=secure


    Test Case 10 - Check the communication between a group of VMs
    This testcase investigates if communication between a group of VMs is interrupted upon deletion
    and creation of VMs inside this group.

    Test case flow:
        Create 3  VMs:  VM_1  on compute 1, VM_2 on compute 1, VM_3 on compute 2.
        All VMs ping each other.
        VM_2  is deleted.
        Traffic is still flying between VM_ 1 and VM_3.
        A new VM, VM_ 4  is added to compute 1.
        Traffic is not interrupted and VM_4 can be reached as well.


    Testcase 11: test Opendaylight resync and group_add_mod feature mechanisms
    This is testcase to test Opendaylight resync and group_add_mod feature functionalities

    Sub-testcase 11-1:
    Create and start 2 VMs, connected to a common Network.
        New groups should appear in OVS dump
    OVS disconnects and the VMs and the networks are cleaned.
        The new groups are still in the OVS dump,
        cause OVS  is not connected anymore, so it is not notified that the groups are deleted
    OVS re-connects.
        The new groups should be deleted, as Opendaylight has to resync the groups totally and
        should remove the groups since VMS are deleted.

    Sub-testcase 11-2:
    Create and start 2 VMs, connected to a common Network.
        New groups should appear in OVS dump
    OVS disconnects.
        The new groups are still in the OVS dump, cause OVS is not connected anymore,
        so it is not notified that the groups are deleted
    OVS re-connects.
        The new groups should be still there, as the topology remains. Opendaylight Carbon's
        group_add_mod mechanism should handle the already existing group.
    OVS re-connects.
        The new groups should be still there, as the topology remains.
        Opendaylight Carbon’ group_add_mod mechanism should handle the already existing group.

    Testcase 12: Test Resync mechanism between Opendaylight and OVS
    This is the testcase to validate flows and groups are programmed correctly
    after resync which is triggered by OVS del-controller/set-controller commands
    and adding/remove iptables drop rule on OF port 6653.

    Sub-testcase 12-1:
    Create and start 2 VMs, connected to a common Network
        New flows and groups were added to OVS
    Reconnect the OVS by running del-ontroller and set-controller commands
        The flows and groups are still intact and none of the flows/groups
        are removed
    Reconnect the OVS by adding ip tables drop rule and then remove it
        The flows and groups are still intact and none of the flows/groups
        are removed
