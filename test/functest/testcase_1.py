#!/usr/bin/python
#
# Copyright (c) 2015 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

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

logger = ft_logger.Logger("sdnvpn-testcase-1").getLogger()

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig('testcase_1')


def main():
    results = Results(COMMON_CONFIG.line_length)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()
    glance_client = os_utils.get_glance_client()

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

    sg_id = os_utils.create_security_group_full(neutron_client,
                                                TESTCASE_CONFIG.secgroup_name,
                                                TESTCASE_CONFIG.secgroup_descr)

    compute_nodes = test_utils.assert_and_get_compute_nodes(nova_client)

    av_zone_1 = "nova:" + compute_nodes[0]
    av_zone_2 = "nova:" + compute_nodes[1]

    # boot INTANCES
    vm_2 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_2_name,
        image_id,
        network_1_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1)
    vm_2_ip = vm_2.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (TESTCASE_CONFIG.instance_2_name, vm_2_ip))

    vm_3 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_3_name,
        image_id,
        network_1_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_2)
    vm_3_ip = vm_3.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (TESTCASE_CONFIG.instance_3_name, vm_3_ip))

    vm_5 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_5_name,
        image_id,
        network_2_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_2)
    vm_5_ip = vm_5.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (TESTCASE_CONFIG.instance_5_name, vm_5_ip))

    # We boot vm5 first because we need vm5_ip for vm4 userdata
    u4 = test_utils.generate_ping_userdata([vm_5_ip])
    vm_4 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_4_name,
        image_id,
        network_2_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1,
        userdata=u4)
    vm_4_ip = vm_4.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (TESTCASE_CONFIG.instance_4_name, vm_4_ip))

    # We boot VM1 at the end because we need to get the IPs first to generate
    # the userdata
    u1 = test_utils.generate_ping_userdata([vm_2_ip,
                                            vm_3_ip,
                                            vm_4_ip,
                                            vm_5_ip])
    vm_1 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_1_name,
        image_id,
        network_1_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1,
        userdata=u1)
    vm_1_ip = vm_1.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (TESTCASE_CONFIG.instance_1_name, vm_1_ip))

    msg = ("Create VPN with eRT<>iRT")
    logger.info(msg)
    results.add_to_summary(1, msg)
    vpn_name = "sdnvpn-" + str(randint(100000, 999999))
    kwargs = {
        "import_targets": TESTCASE_CONFIG.targets1,
        "export_targets": TESTCASE_CONFIG.targets2,
        "route_distinguishers": TESTCASE_CONFIG.route_distinguishers,
        "name": vpn_name
    }
    bgpvpn = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn_id = bgpvpn['bgpvpn']['id']
    logger.debug("VPN created details: %s" % bgpvpn)

    msg = ("Associate network '%s' to the VPN." % TESTCASE_CONFIG.net_1_name)
    logger.info(msg)
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn_id, network_1_id)

    # Wait for VMs to get ips.
    instances_up = test_utils.wait_for_instances_up(vm_1, vm_2,
                                                    vm_3, vm_4,
                                                    vm_5)

    if not instances_up:
        logger.error("One or more instances is down")
        # TODO: Handle this appropriately

    # Ping from VM1 to VM2 should work
    results.get_ping_status(vm_1, vm_1_ip, vm_2, vm_2_ip,
                            expected="PASS", timeout=200)
    # Ping from VM1 to VM3 should work
    results.get_ping_status(vm_1, vm_1_ip, vm_3, vm_3_ip,
                            expected="PASS", timeout=30)
    # Ping from VM1 to VM4 should not work
    results.get_ping_status(vm_1, vm_1_ip, vm_4, vm_4_ip,
                            expected="FAIL", timeout=30)

    msg = ("Associate network '%s' to the VPN." % TESTCASE_CONFIG.net_2_name)
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")
    os_utils.create_network_association(
        neutron_client, bgpvpn_id, network_2_id)

    test_utils.wait_for_bgp_net_assocs(neutron_client,
                                       bgpvpn_id,
                                       network_1_id,
                                       network_2_id)

    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    time.sleep(30)

    # Ping from VM4 to VM5 should work
    results.get_ping_status(vm_4, vm_4_ip, vm_5, vm_5_ip,
                            expected="PASS", timeout=30)
    # Ping from VM1 to VM4 should not work
    results.get_ping_status(vm_1, vm_1_ip, vm_4, vm_4_ip,
                            expected="FAIL", timeout=30)
    # Ping from VM1 to VM5 should not work
    results.get_ping_status(vm_1, vm_1_ip, vm_5, vm_5_ip,
                            expected="FAIL", timeout=30)

    msg = ("Update VPN with eRT=iRT ...")
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")
    kwargs = {"import_targets": TESTCASE_CONFIG.targets1,
              "export_targets": TESTCASE_CONFIG.targets1,
              "name": vpn_name}
    bgpvpn = os_utils.update_bgpvpn(neutron_client, bgpvpn_id, **kwargs)
    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    time.sleep(30)

    # Ping from VM1 to VM4 should work
    results.get_ping_status(vm_1, vm_1_ip, vm_4, vm_4_ip,
                            expected="PASS", timeout=30)
    # Ping from VM1 to VM5 should work
    results.get_ping_status(vm_1, vm_1_ip, vm_5, vm_5_ip,
                            expected="PASS", timeout=30)

    return results.compile_summary(TESTCASE_CONFIG.success_criteria)


if __name__ == '__main__':
    main()
