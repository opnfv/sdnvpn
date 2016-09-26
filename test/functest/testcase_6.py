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
import os
from random import randint
import sys
import time

import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils
import functest.utils.openstack_utils as os_utils

import utils as test_utils
from results import Results

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")

args = parser.parse_args()

logger = ft_logger.Logger("sdnvpn-testcase-4").getLogger()

REPO_PATH = os.environ['repos_dir'] + '/sdnvpn/'

VM_BOOT_TIMEOUT = 180

config_file = REPO_PATH + 'test/functest/config.yaml'

INSTANCE_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.instance_1_name", config_file)
INSTANCE_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.instance_2_name", config_file)
INSTANCE_3_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.instance_3_name", config_file)
INSTANCE_4_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.instance_4_name", config_file)
INSTANCE_5_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.instance_5_name", config_file)
IMAGE_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.image_name", config_file)
IMAGE_FILENAME = ft_utils.get_functest_config(
    "general.openstack.image_file_name")
IMAGE_FORMAT = ft_utils.get_functest_config(
    "general.openstack.image_disk_format")
IMAGE_PATH = ft_utils.get_functest_config(
    "general.directories.dir_functest_data") + "/" + IMAGE_FILENAME

# NEUTRON Private Network parameters

NET_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.net_1_name", config_file)
SUBNET_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.subnet_1_name", config_file)
SUBNET_1_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.subnet_1_cidr", config_file)
ROUTER_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.router_1_name", config_file)
NET_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.net_2_name", config_file)
SUBNET_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.subnet_2_name", config_file)
SUBNET_2_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.subnet_2_cidr", config_file)
ROUTER_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.router_2_name", config_file)
SECGROUP_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.sdnvpn_sg_name", config_file)
SECGROUP_DESCR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.sdnvpn_sg_descr", config_file)
TARGETS_1 = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.targets1", config_file)
TARGETS_2 = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.targets2", config_file)
SUCCESS_CRITERIA = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_6.success_criteria", config_file)
TEST_DB = ft_utils.get_functest_config("results.test_db_url")

LINE_LENGTH = 60  # length for the summary table


def main():
    global LINE_LENGTH

    results = Results(LINE_LENGTH)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()
    glance_client = os_utils.get_glance_client()

    image_id = os_utils.create_glance_image(glance_client,
                                            IMAGE_NAME,
                                            IMAGE_PATH,
                                            disk=IMAGE_FORMAT,
                                            container="bare",
                                            public=True)
    network_1_id, _, router_1_id = test_utils.create_network(neutron_client,
                                                             NET_1_NAME,
                                                             SUBNET_1_NAME,
                                                             SUBNET_1_CIDR,
                                                             ROUTER_1_NAME)
    network_2_id, _, router_2_id = test_utils.create_network(neutron_client,
                                                             NET_2_NAME,
                                                             SUBNET_2_NAME,
                                                             SUBNET_2_CIDR,
                                                             ROUTER_2_NAME)
    sg_id = os_utils.create_security_group_full(neutron_client,
                                                SECGROUP_NAME, SECGROUP_DESCR)

    # Get hypervisors zones
    compute_nodes = os_utils.get_hypervisors(nova_client)
    num_compute_nodes = len(compute_nodes)
    if num_compute_nodes < 2:
        logger.error("There are %s compute nodes in the deployment. "
                     "Minimum number of nodes to complete the test is 2."
                     % num_compute_nodes)
        sys.exit(-1)

    logger.debug("Compute nodes: %s" % compute_nodes)
    av_zone_1 = "nova:" + compute_nodes[0]
    av_zone_2 = "nova:" + compute_nodes[1]

    # boot INTANCES
    vm_2 = test_utils.create_instance(nova_client,
                                      INSTANCE_2_NAME,
                                      image_id,
                                      network_1_id,
                                      sg_id,
                                      secgroup_name=SECGROUP_NAME,
                                      compute_node=av_zone_1)
    vm_2_ip = vm_2.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_2_NAME, vm_2_ip))

    vm_3 = test_utils.create_instance(nova_client,
                                      INSTANCE_3_NAME,
                                      image_id,
                                      network_1_id,
                                      sg_id,
                                      secgroup_name=SECGROUP_NAME,
                                      compute_node=av_zone_2)
    vm_3_ip = vm_3.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_3_NAME, vm_3_ip))

    vm_5 = test_utils.create_instance(nova_client,
                                      INSTANCE_5_NAME,
                                      image_id,
                                      network_2_id,
                                      sg_id,
                                      secgroup_name=SECGROUP_NAME,
                                      compute_node=av_zone_2)
    vm_5_ip = vm_5.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_5_NAME, vm_5_ip))

    # We boot vm5 first because we need vm5_ip for vm4 userdata
    u4 = test_utils.generate_ping_userdata([vm_5_ip])
    vm_4 = test_utils.create_instance(nova_client,
                                      INSTANCE_4_NAME,
                                      image_id,
                                      network_2_id,
                                      sg_id,
                                      secgroup_name=SECGROUP_NAME,
                                      compute_node=av_zone_1,
                                      userdata=u4)
    vm_4_ip = vm_4.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_4_NAME, vm_4_ip))

    # We boot VM1 at the end because we need to get the IPs first to generate
    # the userdata
    u1 = test_utils.generate_ping_userdata([vm_2_ip,
                                            vm_3_ip,
                                            vm_4_ip,
                                            vm_5_ip])
    vm_1 = test_utils.create_instance(nova_client,
                                      INSTANCE_1_NAME,
                                      image_id,
                                      network_1_id,
                                      sg_id,
                                      secgroup_name=SECGROUP_NAME,
                                      compute_node=av_zone_1,
                                      userdata=u1)
    vm_1_ip = vm_1.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_1_NAME, vm_1_ip))

    msg = ("Create VPN1 iRT=iRT1 | eRT=eRT1")
    logger.info(msg)
    results.add_to_summary(1, msg)

    vpn_1_name = "sdnvpn-" + str(randint(100000, 999999))
    kwargs = {"import_targets": TARGETS_1,
              "export_targets": TARGETS_1,
              "name": vpn_1_name}
    bgpvpn_1 = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn_1_id = bgpvpn_1['bgpvpn']['id']
    logger.debug("VPN created details: %s" % bgpvpn_1)

    msg = ("Associate router '%s' to the VPN." % ROUTER_1_NAME)
    logger.info(msg)
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")

    os_utils.create_router_association(
        neutron_client, bgpvpn_1_id, router_1_id)
    test_utils.wait_for_bgp_router_assoc(
        neutron_client, bgpvpn_1_id, router_1_id)

    msg = ("Create VPN2 iRT=iRT2 | eRT=eRT2")
    logger.info(msg)
    results.add_to_summary(1, msg)

    vpn_2_name = "sdnvpn-" + str(randint(100000, 999999))
    kwargs = {"import_targets": TARGETS_2,
              "export_targets": TARGETS_2,
              "name": vpn_2_name}
    bgpvpn_2 = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn_2_id = bgpvpn_1['bgpvpn']['id']
    logger.debug("VPN created details: %s" % bgpvpn_2)

    msg = ("Associate network '%s' to the VPN." % NET_2_NAME)
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn_2_id, network_2_id)
    test_utils.wait_for_bgp_net_assoc(
        neutron_client, bgpvpn_2_id, network_2_id)

    # Wait for VMs to get ips.
    instances_up = test_utils.wait_for_instances_up(vm_1, vm_2,
                                                    vm_3, vm_4,
                                                    vm_5)

    if not instances_up:
        logger.error("One or more instances is down")
        # TODO Handle appropriately

    # Ping from VM1 to VM2 should work
    results.get_ping_status(vm_1, vm_1_ip, vm_2, vm_2_ip,
                            expected="PASS", timeout=200)
    # Ping from VM1 to VM3 should work
    results.get_ping_status(vm_1, vm_1_ip, vm_2, vm_2_ip,
                            expected="PASS", timeout=200)
    # Ping from VM1 to VM5 should not work
    results.get_ping_status(vm_1, vm_1_ip, vm_5, vm_5_ip,
                            expected="FAIL", timeout=30)
    # Ping from VM4 to VM2 should not work
    results.get_ping_status(vm_4, vm_4_ip, vm_2, vm_2_ip,
                            expected="FAIL", timeout=30)
    # Ping from VM4 to VM3 should not work
    results.get_ping_status(vm_4, vm_4_ip, vm_3, vm_3_ip,
                            expected="FAIL", timeout=30)
    # Ping from VM4 to VM5 should work
    results.get_ping_status(vm_4, vm_4_ip, vm_5, vm_5_ip,
                            expected="PASS", timeout=30)

    msg = ("Update VPN1 with iRT=eRT2 | eRT=eRT1 ...")
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")
    kwargs = {"import_targets": TARGETS_2,
              "export_targets": TARGETS_1,
              "name": vpn_1_name}
    bgpvpn_1 = os_utils.update_bgpvpn(neutron_client, bgpvpn_1_id, **kwargs)

    msg = ("Update VPN2 with iRT=eRT1 | eRT=eRT2 ...")
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")
    kwargs = {"import_targets": TARGETS_1,
              "export_targets": TARGETS_2,
              "name": vpn_2_name}
    bgpvpn_2 = os_utils.update_bgpvpn(neutron_client, bgpvpn_2_id, **kwargs)

    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    time.sleep(30)

    # Ping from VM1 to VM2 should not work
    results.get_ping_status(vm_1, vm_1_ip, vm_2, vm_2_ip,
                            expected="FAIL", timeout=200)
    # Ping from VM1 to VM3 should not work
    results.get_ping_status(vm_1, vm_1_ip, vm_2, vm_2_ip,
                            expected="FAIL", timeout=200)
    # Ping from VM1 to VM5 should work
    results.get_ping_status(vm_1, vm_1_ip, vm_5, vm_5_ip,
                            expected="PASS", timeout=30)
    # Ping from VM4 to VM2 should work
    results.get_ping_status(vm_4, vm_4_ip, vm_2, vm_2_ip,
                            expected="PASS", timeout=30)
    # Ping from VM4 to VM3 should not work
    results.get_ping_status(vm_4, vm_4_ip, vm_3, vm_3_ip,
                            expected="PASS", timeout=30)
    # Ping from VM4 to VM5 should not work
    results.get_ping_status(vm_4, vm_4_ip, vm_5, vm_5_ip,
                            expected="FAIL", timeout=30)

    msg = ("Update VPN1 with iRT=[iRT1,iRT2] | eRT=eRT1 ...")
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")
    kwargs = {"import_targets": [TARGETS_1, TARGETS_2],
              "export_targets": TARGETS_1,
              "name": vpn_1_name}
    bgpvpn_1 = os_utils.update_bgpvpn(neutron_client, bgpvpn_1_id, **kwargs)

    msg = ("Update VPN2 with iRT=[iRT1,iRT2] | eRT=eRT2 ...")
    logger.info(msg)
    results.add_to_summary(0, "-")
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")
    kwargs = {"import_targets": [TARGETS_1, TARGETS_2],
              "export_targets": TARGETS_2,
              "name": vpn_2_name}
    bgpvpn_2 = os_utils.update_bgpvpn(neutron_client, bgpvpn_2_id, **kwargs)

    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    time.sleep(30)

    # Ping from VM1 to VM2 should work
    results.get_ping_status(vm_1, vm_1_ip, vm_2, vm_2_ip,
                            expected="PASS", timeout=200)
    # Ping from VM1 to VM3 should work
    results.get_ping_status(vm_1, vm_1_ip, vm_2, vm_2_ip,
                            expected="PASS", timeout=200)
    # Ping from VM1 to VM5 should work
    results.get_ping_status(vm_1, vm_1_ip, vm_5, vm_5_ip,
                            expected="PASS", timeout=30)
    # Ping from VM4 to VM2 should work
    results.get_ping_status(vm_4, vm_4_ip, vm_2, vm_2_ip,
                            expected="PASS", timeout=30)
    # Ping from VM4 to VM3 should work
    results.get_ping_status(vm_4, vm_4_ip, vm_3, vm_3_ip,
                            expected="PASS", timeout=30)
    # Ping from VM4 to VM5 should work
    results.get_ping_status(vm_4, vm_4_ip, vm_5, vm_5_ip,
                            expected="PASS", timeout=30)

    results.add_to_summary(0, "=")
    logger.info("\n%s" % results.summary)

    if results.test_result == "PASS":
        logger.info("All the ping tests have passed as expected.")
    else:
        logger.info("One or more ping tests have failed.")

    status = "PASS"
    success = 100 - \
        (100 * int(results.num_tests_failed) / int(results.num_tests_failed))
    if success < int(SUCCESS_CRITERIA):
        status = "FAILED"

    return {"status": status, "details": results.details}


if __name__ == '__main__':
    main()
