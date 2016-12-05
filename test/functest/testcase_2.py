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
import sys

import functest.utils.functest_logger as ft_logger
import functest.utils.openstack_utils as os_utils

import utils as test_utils
from results import Results
import config as sdnvpn_config

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")

args = parser.parse_args()

logger = ft_logger.Logger("sdnvpn-testcase-2").getLogger()

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig('testcase_2')


def main():
    results = Results(COMMON_CONFIG.line_length)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()
    glance_client = os_utils.get_glance_client()

    logger.debug("Using private key %s injected to the VMs."
                 % COMMON_CONFIG.keyfile_path)
    keyfile = open(COMMON_CONFIG.keyfile_path, 'r')
    key = keyfile.read()
    keyfile.close()
    files = {"/home/cirros/id_rsa": key}

    image_id = os_utils.create_glance_image(glance_client,
                                            TESTCASE_CONFIG.image_name,
                                            COMMON_CONFIG.image_path,
                                            disk=COMMON_CONFIG.image_format,
                                            container="bare",
                                            public=True)
    network_1_id = test_utils.create_net(
        neutron_client,
        TESTCASE_CONFIG.net_1_name)
    test_utils.create_subnet(
        neutron_client,
        TESTCASE_CONFIG.subnet_1a_name,
        TESTCASE_CONFIG.subnet_1a_cidr,
        network_1_id)
    test_utils.create_subnet(
        neutron_client,
        TESTCASE_CONFIG.subnet_1b_name,
        TESTCASE_CONFIG.subnet_1b_cidr,
        network_1_id)

    network_2_id = test_utils.create_net(
        neutron_client,
        TESTCASE_CONFIG.net_2_name)
    test_utils.create_subnet(
        neutron_client,
        TESTCASE_CONFIG.subnet_2a_name,
        TESTCASE_CONFIG.subnet_2a_cidr,
        network_2_id)
    test_utils.create_subnet(
        neutron_client,
        TESTCASE_CONFIG.subnet_2b_name,
        TESTCASE_CONFIG.subnet_2b_cidr,
        network_2_id)

    sg_id = os_utils.create_security_group_full(neutron_client,
                                                TESTCASE_CONFIG.secgroup_name,
                                                TESTCASE_CONFIG.secgroup_descr)

    compute_nodes = test_utils.assert_and_get_compute_nodes(nova_client)

    av_zone_1 = "nova:" + compute_nodes[0]
    av_zone_2 = "nova:" + compute_nodes[1]

    # boot INTANCES
    userdata_common = test_utils.generate_userdata_common()
    vm_2 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_2_name,
        image_id,
        network_1_id,
        sg_id,
        fixed_ip=TESTCASE_CONFIG.instance_2_ip,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1,
        userdata=userdata_common)

    vm_3 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_3_name,
        image_id,
        network_1_id,
        sg_id,
        fixed_ip=TESTCASE_CONFIG.instance_3_ip,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_2,
        userdata=userdata_common)

    vm_5 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_5_name,
        image_id,
        network_2_id,
        sg_id,
        fixed_ip=TESTCASE_CONFIG.instance_5_ip,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_2,
        userdata=userdata_common)

    # We boot vm5 first because we need vm5_ip for vm4 userdata
    u4 = test_utils.generate_userdata_with_ssh(
        [TESTCASE_CONFIG.instance_1_ip,
         TESTCASE_CONFIG.instance_3_ip,
         TESTCASE_CONFIG.instance_5_ip])
    vm_4 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_4_name,
        image_id,
        network_2_id,
        sg_id,
        fixed_ip=TESTCASE_CONFIG.instance_4_ip,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1,
        userdata=u4,
        files=files)

    # We boot VM1 at the end because we need to get the IPs first to generate
    # the userdata
    u1 = test_utils.generate_userdata_with_ssh(
        [TESTCASE_CONFIG.instance_2_ip,
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
        userdata=u1,
        files=files)

    msg = ("Create VPN1 with eRT=iRT")
    logger.info(msg)
    results.add_to_summary(1, msg)
    vpn1_name = "sdnvpn-1-" + str(randint(100000, 999999))
    kwargs = {"import_targets": TESTCASE_CONFIG.targets2,
              "export_targets": TESTCASE_CONFIG.targets2,
              "route_targets": TESTCASE_CONFIG.targets2,
              "route_distinguishers": TESTCASE_CONFIG.route_distinguishers1,
              "name": vpn1_name}
    bgpvpn1 = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn1_id = bgpvpn1['bgpvpn']['id']
    logger.debug("VPN1 created details: %s" % bgpvpn1)

    msg = ("Associate network '%s' to the VPN." % TESTCASE_CONFIG.net_1_name)
    logger.info(msg)
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn1_id, network_1_id)

    # Wait for VMs to get ips.
    instances_up = test_utils.wait_for_instances_up(vm_1, vm_2,
                                                    vm_3, vm_4,
                                                    vm_5)

    if not instances_up:
        logger.error("One or more instances is down")
        sys.exit(-1)

    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    test_utils.wait_before_subtest()

    # 10.10.10.12 should return sdnvpn-2 to sdnvpn-1
    results.check_ssh_output(vm_1, vm_2,
                             expected=TESTCASE_CONFIG.instance_2_name,
                             timeout=200)
    # 10.10.11.13 should return sdnvpn-3 to sdnvpn-1
    results.check_ssh_output(vm_1, vm_3,
                             expected=TESTCASE_CONFIG.instance_3_name,
                             timeout=30)

    results.add_to_summary(0, "-")
    msg = ("Create VPN2 with eRT=iRT")
    logger.info(msg)
    results.add_to_summary(1, msg)
    vpn2_name = "sdnvpn-2-" + str(randint(100000, 999999))
    kwargs = {"import_targets": TESTCASE_CONFIG.targets1,
              "export_targets": TESTCASE_CONFIG.targets1,
              "route_targets": TESTCASE_CONFIG.targets1,
              "route_distinguishers": TESTCASE_CONFIG.route_distinguishers2,
              "name": vpn2_name}
    bgpvpn2 = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn2_id = bgpvpn2['bgpvpn']['id']
    logger.debug("VPN created details: %s" % bgpvpn2)

    msg = ("Associate network '%s' to the VPN2." % TESTCASE_CONFIG.net_2_name)
    logger.info(msg)
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn2_id, network_2_id)

    test_utils.wait_for_bgp_net_assoc(neutron_client, bgpvpn1_id, network_1_id)
    test_utils.wait_for_bgp_net_assoc(neutron_client, bgpvpn2_id, network_2_id)

    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    test_utils.wait_before_subtest()

    # 10.10.11.13 should return sdnvpn-5 to sdnvpn-4
    results.check_ssh_output(vm_4, vm_5,
                             expected=TESTCASE_CONFIG.instance_5_name,
                             timeout=30)

    # 10.10.10.11 should return "not reachable" to sdnvpn-4
    results.check_ssh_output(vm_4, vm_1,
                             expected="not reachable",
                             timeout=30)

    return results.compile_summary(TESTCASE_CONFIG.success_criteria)


if __name__ == '__main__':
    main()
