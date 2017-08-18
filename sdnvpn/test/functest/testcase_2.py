#!/usr/bin/python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

import argparse
import logging
import sys

from functest.utils import openstack_utils as os_utils
from random import randint
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib.results import Results

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")

args = parser.parse_args()

logger = logging.getLogger('sdnvpn-testcase-2')

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

    (floatingip_ids, instance_ids, router_ids, network_ids, image_ids,
     subnet_ids, interfaces, bgpvpn_ids) = ([] for i in range(8))

    logger.debug("Using private key %s injected to the VMs."
                 % COMMON_CONFIG.keyfile_path)

    image_id = os_utils.create_glance_image(glance_client,
                                            TESTCASE_CONFIG.image_name,
                                            COMMON_CONFIG.image_path,
                                            disk=COMMON_CONFIG.image_format,
                                            container="bare",
                                            public='public')
    image_ids.append(image_id)

    network_1_id = test_utils.create_net(
        neutron_client,
        TESTCASE_CONFIG.net_1_name)
    subnet_1a_id = test_utils.create_subnet(
        neutron_client,
        TESTCASE_CONFIG.subnet_1a_name,
        TESTCASE_CONFIG.subnet_1a_cidr,
        network_1_id)
    subnet_1b_id = test_utils.create_subnet(
        neutron_client,
        TESTCASE_CONFIG.subnet_1b_name,
        TESTCASE_CONFIG.subnet_1b_cidr,
        network_1_id)

    network_2_id = test_utils.create_net(
        neutron_client,
        TESTCASE_CONFIG.net_2_name)
    subnet_2a_id = test_utils.create_subnet(
        neutron_client,
        TESTCASE_CONFIG.subnet_2a_name,
        TESTCASE_CONFIG.subnet_2a_cidr,
        network_2_id)
    subnet_2b_id = test_utils.create_subnet(
        neutron_client,
        TESTCASE_CONFIG.subnet_2b_name,
        TESTCASE_CONFIG.subnet_2b_cidr,
        network_2_id)
    network_ids.extend([network_1_id, network_2_id])
    subnet_ids.extend([subnet_1a_id, subnet_1b_id, subnet_2a_id, subnet_2b_id])
    # The following 2 routers are temporary and used in order to create
    # the appropriate datapath to transfere the private keys (id_rsa files)
    # to the coresponded VMs. They are deleted before the actual test is
    # started
    router1_id, router1_interfaces = test_utils.create_router(
        neutron_client,
        TESTCASE_CONFIG.router_1_name,
        [subnet_1a_id, subnet_1b_id])
    router2_id, router2_interfaces = test_utils.create_router(
        neutron_client,
        TESTCASE_CONFIG.router_2_name,
        [subnet_2a_id, subnet_2b_id])
    interfaces.extend(router1_interfaces)
    interfaces.extend(router2_interfaces)
    router_ids.extend([router1_id, router2_id])

    sg_id = os_utils.create_security_group_full(neutron_client,
                                                TESTCASE_CONFIG.secgroup_name,
                                                TESTCASE_CONFIG.secgroup_descr)

    compute_nodes = test_utils.assert_and_get_compute_nodes(nova_client)

    av_zone_1 = "nova:" + compute_nodes[0]
    av_zone_2 = "nova:" + compute_nodes[1]

    # boot INSTANCES
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
        userdata=u4)

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
        userdata=u1)
    instance_ids.extend([vm_1.id, vm_2.id, vm_3.id, vm_4.id, vm_5.id])

    # Wait for VMs to get ips.
    instances_get_ip = test_utils.wait_instances_get_dhcp_lease(vm_1, vm_2,
                                                                vm_3, vm_4,
                                                                vm_5)

    if not instances_get_ip:
        logger.error("One or more instances is down")
        sys.exit(-1)

    # We use the following floating ips, in order to create the appropriate
    # datapath to pass the id_rsa key to vm_1 and vm_4
    fip_1 = os_utils.create_floating_ip(neutron_client)
    vm_1_fip_added = os_utils.add_floating_ip(nova_client,
                                              vm_1.id,
                                              fip_1['fip_addr'])
    if not vm_1_fip_added:
        logger.error("Fail to assign floating ip to vm_1")
        sys.exit(-1)
    fip_2 = os_utils.create_floating_ip(neutron_client)
    vm_4_fip_added = os_utils.add_floating_ip(nova_client,
                                              vm_4.id,
                                              fip_2['fip_addr'])
    if not vm_4_fip_added:
        logger.error("Fail to assign floating ip to vm_4")
        sys.exit(-1)

    floatingip_ids.extend([fip_1['fip_id'], fip_2['fip_id']])
    cmd_copy_key_1 = ("cp %s /tmp/id_rsa; "
                      "chmod 600 /tmp/id_rsa; "
                      "sshpass -p '%s' scp -oStrictHostKeyChecking=no "
                      "-oUserKnownHostsFile=/dev/null /tmp/id_rsa "
                      "%s@%s:/home/%s/.ssh" %
                      (COMMON_CONFIG.keyfile_path,
                       TESTCASE_CONFIG.instance_pwd,
                       TESTCASE_CONFIG.instance_uname, fip_1['fip_addr'],
                       TESTCASE_CONFIG.instance_uname))
    cmd_copy_key_2 = ("cp %s /tmp/id_rsa; "
                      "chmod 600 /tmp/id_rsa; "
                      "sshpass -p '%s' scp -oStrictHostKeyChecking=no "
                      "-oUserKnownHostsFile=/dev/null /tmp/id_rsa "
                      "%s@%s:/home/%s/.ssh" %
                      (COMMON_CONFIG.keyfile_path,
                       TESTCASE_CONFIG.instance_pwd,
                       TESTCASE_CONFIG.instance_uname, fip_2['fip_addr'],
                       TESTCASE_CONFIG.instance_uname))
    test_utils.wait_before_subtest()
    test_utils.exec_cmd(cmd_copy_key_1, True)
    test_utils.exec_cmd(cmd_copy_key_2, True)
    test_utils.cleanup_neutron(neutron_client,
                               floatingip_ids, [],
                               interfaces, [], router_ids, [])
    test_utils.wait_before_subtest()

    # At this point the setup is clean from any extra components.
    # It is ready for the actual test process

    msg = ("Create VPN1 with eRT=iRT")
    results.record_action(msg)
    vpn1_name = "sdnvpn-1-" + str(randint(100000, 999999))
    kwargs = {"import_targets": TESTCASE_CONFIG.targets2,
              "export_targets": TESTCASE_CONFIG.targets2,
              "route_targets": TESTCASE_CONFIG.targets2,
              "route_distinguishers": TESTCASE_CONFIG.route_distinguishers1,
              "name": vpn1_name}
    bgpvpn1 = test_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn1_id = bgpvpn1['bgpvpn']['id']
    logger.debug("VPN1 created details: %s" % bgpvpn1)
    bgpvpn_ids.append(bgpvpn1_id)

    msg = ("Associate network '%s' to the VPN." % TESTCASE_CONFIG.net_1_name)
    results.record_action(msg)
    results.add_to_summary(0, "-")

    test_utils.create_network_association(
        neutron_client, bgpvpn1_id, network_1_id)
    test_utils.wait_for_bgp_net_assoc(neutron_client, bgpvpn1_id, network_1_id)

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
                             timeout=200)

    results.add_to_summary(0, "-")
    msg = ("Create VPN2 with eRT=iRT")
    results.record_action(msg)
    vpn2_name = "sdnvpn-2-" + str(randint(100000, 999999))
    kwargs = {"import_targets": TESTCASE_CONFIG.targets1,
              "export_targets": TESTCASE_CONFIG.targets1,
              "route_targets": TESTCASE_CONFIG.targets1,
              "route_distinguishers": TESTCASE_CONFIG.route_distinguishers2,
              "name": vpn2_name}
    bgpvpn2 = test_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn2_id = bgpvpn2['bgpvpn']['id']
    logger.debug("VPN created details: %s" % bgpvpn2)
    bgpvpn_ids.append(bgpvpn2_id)

    msg = ("Associate network '%s' to the VPN2." % TESTCASE_CONFIG.net_2_name)
    results.record_action(msg)
    results.add_to_summary(0, "-")

    test_utils.create_network_association(
        neutron_client, bgpvpn2_id, network_2_id)
    test_utils.wait_for_bgp_net_assoc(neutron_client, bgpvpn2_id, network_2_id)

    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    test_utils.wait_before_subtest()

    # 10.10.11.13 should return sdnvpn-5 to sdnvpn-4
    results.check_ssh_output(vm_4, vm_5,
                             expected=TESTCASE_CONFIG.instance_5_name,
                             timeout=200)

    # 10.10.10.11 should return "not reachable" to sdnvpn-4
    results.check_ssh_output(vm_4, vm_1,
                             expected="not reachable",
                             timeout=30)

    test_utils.cleanup_nova(nova_client, instance_ids, image_ids)
    test_utils.cleanup_neutron(neutron_client, [], bgpvpn_ids,
                               [], subnet_ids, [],
                               network_ids)
    return results.compile_summary()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
