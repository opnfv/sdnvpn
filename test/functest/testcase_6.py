#!/usr/bin/python
#
# Copyright (c) 2015 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
"""
Name: Multiple VPNs connecting Neutron networks and subnets using
        network and router association
Description: VPNs provide connectivity across Neutron networks and
                subnets if configured accordingly.

  ------------------------------      ---------------------
  |       VPN1 - net assoc     |      |       VPN2        |
  |                            |      |    router assoc   |
  | ----------     ----------  |      |   -------------   |
  | |  net 1 |     |  net 2 |  |      |   |   net 3   |   |
  | |        |     |        |  |      |   |           |   |
  | |   vm1  |     |   vm3  |  |      |   |    vm4    |   |
  | |   vm2  |     |        |  |      |   |    vm5    |   |
  | |        |     |        |  |      |   |           |   |
  | ----------     ----------  |      |   -------------   |
  |                            |      |                   |
  ------------------------------      ---------------------

VM1,VM3 and VM4 are started on Compute 1
VM2 and VM5 are started on Compute 2

Test execution:
    1. Create VPN1 with eRT1=RT1 and iRT1=RT1 and associate net1 and
       net2 to it.
    2. Create VPN2 with eRT2=RT2 and iRT2=RT2 and associate the router 2 to it.
    - VMs belonging to the same VPN should be able to ping each other
    - VMs in different VPNs should not be able to
    3. Change iRT1=RT2 and iRT2=RT1
    - VMs belonging to the same VPN should not ping each other
    - VMs belonging to different VPNs should be able to ping each other
    3. Change VPN1 so that iRT=eRT
    - All VMs should be able to ping each other
"""

import argparse
from random import randint
import time

import functest.utils.functest_logger as ft_logger
import functest.utils.openstack_utils as os_utils

import utils as test_utils
import config as sdnvpn_config
from results import Results

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")

args = parser.parse_args()

logger = ft_logger.Logger("sdnvpn-testcase-6").getLogger()

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig('testcase_6')


def main():
    results = Results(COMMON_CONFIG.line_length)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()
    glance_client = os_utils.get_glance_client()

    # Get hypervisors zones
    compute_nodes = test_utils.assert_and_get_compute_nodes(nova_client)

    # print the test's docstring
    logger.info(__doc__)

    logger.debug("Compute nodes: %s" % compute_nodes)
    av_zone_1 = "nova:" + compute_nodes[0]
    av_zone_2 = "nova:" + compute_nodes[1]

    image_id = os_utils.create_glance_image(glance_client,
                                            TESTCASE_CONFIG.image_name,
                                            COMMON_CONFIG.image_path,
                                            disk=COMMON_CONFIG.image_format,
                                            container="bare",
                                            public=True)

    network_1_id = test_utils.create_net(neutron_client,
                                         TESTCASE_CONFIG.net_1_name)
    test_utils.create_subnet(neutron_client,
                             TESTCASE_CONFIG.subnet_1_name,
                             TESTCASE_CONFIG.subnet_1_cidr,
                             network_1_id)

    network_2_id = test_utils.create_net(neutron_client,
                                         TESTCASE_CONFIG.net_2_name)
    test_utils.create_subnet(neutron_client,
                             TESTCASE_CONFIG.subnet_2_name,
                             TESTCASE_CONFIG.subnet_2_cidr,
                             network_2_id)

    network_3_id, _, router_3_id = test_utils.create_network(
        neutron_client,
        TESTCASE_CONFIG.net_3_name,
        TESTCASE_CONFIG.subnet_3_name,
        TESTCASE_CONFIG.subnet_3_cidr,
        TESTCASE_CONFIG.router_3_name)
    sg_id = os_utils.create_security_group_full(neutron_client,
                                                TESTCASE_CONFIG.secgroup_name,
                                                TESTCASE_CONFIG.secgroup_descr)
    # Boot instances
    u1 = test_utils.generate_ping_userdata([TESTCASE_CONFIG.instance_2_ip,
                                            TESTCASE_CONFIG.instance_3_ip,
                                            TESTCASE_CONFIG.instance_4_ip,
                                            TESTCASE_CONFIG.instance_5_ip])
    vm_1 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_1_name,
        image_id,
        network_1_id,
        sg_id,
        fixed_ip=TESTCASE_CONFIG.instance_1_ip,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1,
        userdata=u1)
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (TESTCASE_CONFIG.instance_1_name,
                  TESTCASE_CONFIG.instance_1_ip))

    u2 = test_utils.generate_ping_userdata([TESTCASE_CONFIG.instance_3_ip])
    vm_2 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_2_name,
        image_id,
        network_1_id,
        sg_id,
        fixed_ip=TESTCASE_CONFIG.instance_2_ip,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1,
        userdata=u2)
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (TESTCASE_CONFIG.instance_2_name,
                  TESTCASE_CONFIG.instance_2_ip))

    vm_3 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_3_name,
        image_id,
        network_2_id,
        sg_id,
        fixed_ip=TESTCASE_CONFIG.instance_3_ip,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1)
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (TESTCASE_CONFIG.instance_3_name,
                  TESTCASE_CONFIG.instance_3_ip))

    u4 = test_utils.generate_ping_userdata([TESTCASE_CONFIG.instance_2_ip,
                                            TESTCASE_CONFIG.instance_3_ip,
                                            TESTCASE_CONFIG.instance_5_ip])
    vm_4 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_4_name,
        image_id,
        network_3_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1,
        userdata=u4)
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (TESTCASE_CONFIG.instance_4_name,
                  TESTCASE_CONFIG.instance_4_ip))

    vm_5 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_5_name,
        image_id,
        network_3_id,
        sg_id,
        fixed_ip=TESTCASE_CONFIG.instance_5_ip,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_2)
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (TESTCASE_CONFIG.instance_5_name,
                  TESTCASE_CONFIG.instance_5_ip))

    msg = ("Create VPN1 iRT=iRT1 | eRT=eRT1")
    logger.info(msg)
    results.add_to_summary(1, msg)

    vpn_1_name = "sdnvpn-" + str(randint(100000, 999999))
    kwargs = {
        "import_targets": TESTCASE_CONFIG.targets1,
        "export_targets": TESTCASE_CONFIG.targets1,
        "route_distinguishers": TESTCASE_CONFIG.route_distinguishers1,
        "name": vpn_1_name
    }
    bgpvpn_1 = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn_1_id = bgpvpn_1['bgpvpn']['id']
    logger.debug("VPN created details: %s" % bgpvpn_1)

    msg = ("Associate network '%s' to the VPN." % TESTCASE_CONFIG.net_1_name)
    logger.info(msg)
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn_1_id, network_1_id)
    test_utils.wait_for_bgp_net_assoc(
        neutron_client, bgpvpn_1_id, network_1_id)

    msg = ("Associate network '%s' to the VPN." % TESTCASE_CONFIG.net_2_name)
    logger.info(msg)
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn_1_id, network_2_id)
    test_utils.wait_for_bgp_net_assoc(
        neutron_client, bgpvpn_1_id, network_2_id)

    msg = ("Create VPN2 iRT=iRT2 | eRT=eRT2")
    logger.info(msg)
    results.add_to_summary(1, msg)

    vpn_2_name = "sdnvpn-" + str(randint(100000, 999999))
    kwargs = {
        "import_targets": TESTCASE_CONFIG.targets2,
        "export_targets": TESTCASE_CONFIG.targets2,
        "route_distinguishers": TESTCASE_CONFIG.route_distinguishers2,
        "name": vpn_2_name
    }
    bgpvpn_2 = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn_2_id = bgpvpn_1['bgpvpn']['id']
    logger.debug("VPN created details: %s" % bgpvpn_2)

    msg = ("Associate router '%s' to the VPN." % TESTCASE_CONFIG.router_3_name)
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")

    os_utils.create_router_association(
        neutron_client, bgpvpn_2_id, router_3_id)
    test_utils.wait_for_bgp_router_assoc(
        neutron_client, bgpvpn_2_id, router_3_id)

    # Wait for VMs to get ips.
    instances_up = test_utils.wait_for_instances_up(vm_1, vm_2,
                                                    vm_3, vm_4,
                                                    vm_5)
    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    time.sleep(30)

    if not instances_up:
        logger.error("One or more instances is down")
        # TODO Handle appropriately

    # ping from vm1 to vm2 should work
    results.get_ping_status(vm_1,
                            TESTCASE_CONFIG.instance_1_ip,
                            vm_2,
                            TESTCASE_CONFIG.instance_2_ip,
                            expected="PASS", timeout=30)
    # ping from vm1 to vm3 should work
    results.get_ping_status(vm_1,
                            TESTCASE_CONFIG.instance_1_ip,
                            vm_3,
                            TESTCASE_CONFIG.instance_3_ip,
                            expected="PASS",
                            timeout=30)
    # ping from vm2 to vm3 should work
    results.get_ping_status(vm_2,
                            TESTCASE_CONFIG.instance_2_ip,
                            vm_3,
                            TESTCASE_CONFIG.instance_3_ip,
                            expected="PASS",
                            timeout=30)
    # ping from vm1 to vm5 should not work
    results.get_ping_status(vm_1,
                            TESTCASE_CONFIG.instance_1_ip,
                            vm_5,
                            TESTCASE_CONFIG.instance_5_ip,
                            expected="FAIL",
                            timeout=30)
    # ping from vm4 to vm2 should not work
    results.get_ping_status(vm_4,
                            TESTCASE_CONFIG.instance_4_ip,
                            vm_2,
                            TESTCASE_CONFIG.instance_2_ip,
                            expected="FAIL",
                            timeout=30)
    # ping from vm4 to vm3 should not work
    results.get_ping_status(vm_4,
                            TESTCASE_CONFIG.instance_4_ip,
                            vm_3,
                            TESTCASE_CONFIG.instance_3_ip,
                            expected="FAIL",
                            timeout=30)
    # ping from vm4 to vm5 should work
    results.get_ping_status(vm_4,
                            TESTCASE_CONFIG.instance_4_ip,
                            vm_5,
                            TESTCASE_CONFIG.instance_5_ip,
                            expected="PASS",
                            timeout=30)

    msg = ("Update VPN1 with iRT=eRT2 | eRT=eRT1 ...")
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")
    kwargs = {
        "import_targets": TESTCASE_CONFIG.targets2,
        "export_targets": TESTCASE_CONFIG.targets1,
        "name": vpn_1_name
    }
    bgpvpn_1 = os_utils.update_bgpvpn(neutron_client, bgpvpn_1_id, **kwargs)

    msg = ("Update VPN2 with iRT=eRT1 | eRT=eRT2 ...")
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")
    kwargs = {
        "import_targets": TESTCASE_CONFIG.targets1,
        "export_targets": TESTCASE_CONFIG.targets2,
        "name": vpn_2_name
    }
    bgpvpn_2 = os_utils.update_bgpvpn(neutron_client, bgpvpn_2_id, **kwargs)

    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    time.sleep(30)

    # Ping from VM1 to VM2 should work
    results.get_ping_status(vm_1,
                            TESTCASE_CONFIG.instance_1_ip,
                            vm_2,
                            TESTCASE_CONFIG.instance_2_ip,
                            expected="FAIL",
                            timeout=30)
    # Ping from VM1 to VM3 should not work
    results.get_ping_status(vm_1,
                            TESTCASE_CONFIG.instance_1_ip,
                            vm_3,
                            TESTCASE_CONFIG.instance_3_ip,
                            expected="PASS",
                            timeout=30)
    # Ping from VM2 to VM3 should not work
    results.get_ping_status(vm_2,
                            TESTCASE_CONFIG.instance_2_ip,
                            vm_3,
                            TESTCASE_CONFIG.instance_3_ip,
                            expected="FAIL",
                            timeout=30)
    # Ping from VM1 to VM5 should work
    results.get_ping_status(vm_1,
                            TESTCASE_CONFIG.instance_1_ip,
                            vm_5,
                            TESTCASE_CONFIG.instance_5_ip,
                            expected="PASS",
                            timeout=30)
    # Ping from VM4 to VM2 should work
    results.get_ping_status(vm_4,
                            TESTCASE_CONFIG.instance_4_ip,
                            vm_2,
                            TESTCASE_CONFIG.instance_2_ip,
                            expected="PASS",
                            timeout=30)
    # Ping from VM4 to VM3 should not work
    results.get_ping_status(vm_4,
                            TESTCASE_CONFIG.instance_4_ip,
                            vm_3,
                            TESTCASE_CONFIG.instance_3_ip,
                            expected="PASS",
                            timeout=30)
    # Ping from VM4 to VM5 should work
    results.get_ping_status(vm_4,
                            TESTCASE_CONFIG.instance_4_ip,
                            vm_5,
                            TESTCASE_CONFIG.instance_5_ip,
                            expected="PASS",
                            timeout=30)

    msg = ("Update VPN1 with iRT=[iRT1,iRT2] | eRT=eRT1 ...")
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")
    kwargs = {
        "import_targets": [TESTCASE_CONFIG.targets1,
                           TESTCASE_CONFIG.targets2],
        "export_targets": TESTCASE_CONFIG.targets1,
        "name": vpn_1_name
    }
    bgpvpn_1 = os_utils.update_bgpvpn(neutron_client, bgpvpn_1_id, **kwargs)

    msg = ("Update VPN2 with iRT=[iRT1,iRT2] | eRT=eRT2 ...")
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")
    kwargs = {
        "import_targets": [TESTCASE_CONFIG.targets1,
                           TESTCASE_CONFIG.targets2],
        "export_targets": TESTCASE_CONFIG.targets2,
        "name": vpn_2_name
    }
    bgpvpn_2 = os_utils.update_bgpvpn(neutron_client, bgpvpn_2_id, **kwargs)

    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    time.sleep(30)

    # Ping from VM1 to VM2 should work
    results.get_ping_status(vm_1,
                            TESTCASE_CONFIG.instance_1_ip,
                            vm_2,
                            TESTCASE_CONFIG.instance_2_ip,
                            expected="PASS", timeout=30)
    # Ping from VM1 to VM3 should work
    results.get_ping_status(vm_1,
                            TESTCASE_CONFIG.instance_1_ip,
                            vm_3,
                            TESTCASE_CONFIG.instance_3_ip,
                            expected="PASS", timeout=30)
    # Ping from VM2 to VM3 should work
    results.get_ping_status(vm_2,
                            TESTCASE_CONFIG.instance_2_ip,
                            vm_3,
                            TESTCASE_CONFIG.instance_3_ip,
                            expected="PASS", timeout=30)
    # Ping from VM1 to VM5 should work
    results.get_ping_status(vm_1,
                            TESTCASE_CONFIG.instance_1_ip,
                            vm_5,
                            TESTCASE_CONFIG.instance_5_ip,
                            expected="PASS", timeout=30)
    # Ping from VM4 to VM2 should work
    results.get_ping_status(vm_4,
                            TESTCASE_CONFIG.instance_4_ip,
                            vm_2,
                            TESTCASE_CONFIG.instance_2_ip,
                            expected="PASS", timeout=30)
    # Ping from VM4 to VM3 should work
    results.get_ping_status(vm_4,
                            TESTCASE_CONFIG.instance_4_ip,
                            vm_3,
                            TESTCASE_CONFIG.instance_3_ip,
                            expected="PASS", timeout=30)
    # Ping from VM4 to VM5 should work
    results.get_ping_status(vm_4,
                            TESTCASE_CONFIG.instance_4_ip,
                            vm_5,
                            TESTCASE_CONFIG.instance_5_ip,
                            expected="PASS", timeout=30)

    return results.compile_summary(TESTCASE_CONFIG.success_criteria)


if __name__ == '__main__':
    main()
