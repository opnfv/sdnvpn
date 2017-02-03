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
Testcase for router/FloatingIP & net assoc mutual exclusivity

A testcase for ODL Bug 6962, testing whether a subnet with a router can be
network associated:
- Create two VMs, each in a subnet with a router
- Network assoc the two networks in a VPN iRT=eRT
- Try to ping from one VM to the other
- Assign a floating IP to a VM
- Ping it
"""
import argparse

import functest.utils.functest_logger as ft_logger
import functest.utils.openstack_utils as os_utils

from sdnvpn.lib import utils as test_utils
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib.results import Results

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")

args = parser.parse_args()

logger = ft_logger.Logger("sdnvpn-testcase-7").getLogger()

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig('testcase_7')


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
                                            public='public')
    network_1_id, _, _ = test_utils.create_network(
        neutron_client,
        TESTCASE_CONFIG.net_1_name,
        TESTCASE_CONFIG.subnet_1_name,
        TESTCASE_CONFIG.subnet_1_cidr,
        TESTCASE_CONFIG.router_1_name)
    network_2_id, _, _ = test_utils.create_network(
        neutron_client,
        TESTCASE_CONFIG.net_2_name,
        TESTCASE_CONFIG.subnet_2_name,
        TESTCASE_CONFIG.subnet_2_cidr,
        TESTCASE_CONFIG.router_2_name)

    sg_id = os_utils.create_security_group_full(neutron_client,
                                                TESTCASE_CONFIG.secgroup_name,
                                                TESTCASE_CONFIG.secgroup_descr)
    test_utils.open_icmp_ssh(neutron_client, sg_id)
    vm_2 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_2_name,
        image_id,
        network_2_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name)
    vm_2_ip = test_utils.get_instance_ip(vm_2)

    u1 = test_utils.generate_ping_userdata([vm_2_ip])
    vm_1 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_1_name,
        image_id,
        network_1_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        userdata=u1)

    msg = ("Create VPN with eRT==iRT")
    results.record_action(msg)
    vpn_name = "sdnvpn-7"
    kwargs = {"import_targets": TESTCASE_CONFIG.targets,
              "export_targets": TESTCASE_CONFIG.targets,
              "route_distinguishers": TESTCASE_CONFIG.route_distinguishers,
              "name": vpn_name}
    bgpvpn = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn_id = bgpvpn['bgpvpn']['id']
    logger.debug("VPN created details: %s" % bgpvpn)

    msg = ("Associate networks '%s', '%s' to the VPN."
           % (TESTCASE_CONFIG.net_1_name,
              TESTCASE_CONFIG.net_2_name))
    results.record_action(msg)
    results.add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn_id, network_1_id)
    os_utils.create_network_association(
        neutron_client, bgpvpn_id, network_2_id)

    test_utils.wait_for_bgp_net_assoc(
        neutron_client, bgpvpn_id, network_1_id)
    test_utils.wait_for_bgp_net_assoc(
        neutron_client, bgpvpn_id, network_2_id)

    instances_up = test_utils.wait_for_instances_up(vm_1, vm_2)
    if not instances_up:
        logger.error("One or more instances is down")

    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    test_utils.wait_before_subtest()

    results.get_ping_status(vm_1, vm_2, expected="PASS", timeout=200)
    results.add_to_summary(0, "=")

    msg = "Assign a Floating IP to %s and ping it" % vm_2.name
    results.record_action(msg)
    results.add_to_summary(0, '-')

    fip = os_utils.create_floating_ip(neutron_client)
    fip_added = os_utils.add_floating_ip(nova_client, vm_2.id, fip['fip_addr'])
    if fip_added:
        results.add_success(msg)
    else:
        results.add_failure(msg)

    results.ping_ip_test(fip['fip_addr'])

    return results.compile_summary()


if __name__ == '__main__':
    main()
