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

logger = ft_logger.Logger("sdnvpn-testcase-2").getLogger()

REPO_PATH = os.environ['repos_dir'] + '/sdnvpn/'

VM_BOOT_TIMEOUT = 180

config_file = REPO_PATH + 'test/functest/config.yaml'

INSTANCE_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.instance_1_name", config_file)
INSTANCE_1_IP = "10.10.10.11"
INSTANCE_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.instance_2_name", config_file)
INSTANCE_2_IP = "10.10.10.12"
INSTANCE_3_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.instance_3_name", config_file)
INSTANCE_3_IP = "10.10.11.13"
INSTANCE_4_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.instance_4_name", config_file)
INSTANCE_4_IP = "10.10.10.12"
INSTANCE_5_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.instance_5_name", config_file)
INSTANCE_5_IP = "10.10.11.13"
IMAGE_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.image_name", config_file)
IMAGE_FILENAME = ft_utils.get_functest_config(
    "general.openstack.image_file_name")
IMAGE_FORMAT = ft_utils.get_functest_config(
    "general.openstack.image_disk_format")
IMAGE_PATH = ft_utils.get_functest_config(
    "general.directories.dir_functest_data") + "/" + IMAGE_FILENAME

KEYFILE_PATH = REPO_PATH + 'test/functest/id_rsa'

# NEUTRON Private Network parameters

NET_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.net_1_name", config_file)
SUBNET_1a_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.subnet_1a_name", config_file)
SUBNET_1a_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.subnet_1a_cidr", config_file)
SUBNET_1b_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.subnet_1b_name", config_file)
SUBNET_1b_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.subnet_1b_cidr", config_file)
ROUTER_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.router_1_name", config_file)
NET_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.net_2_name", config_file)
SUBNET_2a_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.subnet_2a_name", config_file)
SUBNET_2a_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.subnet_2a_cidr", config_file)
SUBNET_2b_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.subnet_2b_name", config_file)
SUBNET_2b_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.subnet_2b_cidr", config_file)
ROUTER_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.router_1_name", config_file)
ROUTER_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.router_2_name", config_file)
SECGROUP_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.sdnvpn_sg_name", config_file)
SECGROUP_DESCR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.sdnvpn_sg_descr", config_file)
TARGETS_1 = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.targets1", config_file)
TARGETS_2 = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.targets2", config_file)
SUCCESS_CRITERIA = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_5.success_criteria", config_file)
TEST_DB = ft_utils.get_functest_config("results.test_db_url")

LINE_LENGTH = 90  # length for the summary table


def main():
    global LINE_LENGTH

    results = Results(LINE_LENGTH)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()
    glance_client = os_utils.get_glance_client()

    logger.debug("Using private key %s injected to the VMs." % KEYFILE_PATH)
    keyfile = open(KEYFILE_PATH, 'r')
    key = keyfile.read()
    keyfile.close()
    files = {"/home/cirros/id_rsa": key}

    image_id = os_utils.create_glance_image(glance_client,
                                            IMAGE_NAME,
                                            IMAGE_PATH,
                                            disk=IMAGE_FORMAT,
                                            container="bare",
                                            public=True)
    network_1_id, _, _ = test_utils.create_network(neutron_client,
                                                   NET_1_NAME,
                                                   SUBNET_1a_NAME,
                                                   SUBNET_1a_CIDR,
                                                   ROUTER_1_NAME,
                                                   SUBNET_1b_NAME,
                                                   SUBNET_1b_CIDR)
    network_2_id, _, router_2_id = test_utils.create_network(neutron_client,
                                                             NET_2_NAME,
                                                             SUBNET_2a_NAME,
                                                             SUBNET_2a_CIDR,
                                                             ROUTER_2_NAME,
                                                             SUBNET_2b_NAME,
                                                             SUBNET_2b_CIDR)
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

    # boot INSTANCES
    userdata_common = test_utils.generate_userdata_common()
    vm_2 = test_utils.create_instance(nova_client,
                                      INSTANCE_2_NAME,
                                      image_id,
                                      network_1_id,
                                      sg_id,
                                      fixed_ip=INSTANCE_2_IP,
                                      secgroup_name=SECGROUP_NAME,
                                      compute_node=av_zone_1,
                                      userdata=userdata_common)
    vm_2_ip = vm_2.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_2_NAME, vm_2_ip))

    vm_3 = test_utils.create_instance(nova_client,
                                      INSTANCE_3_NAME,
                                      image_id,
                                      network_1_id,
                                      sg_id,
                                      fixed_ip=INSTANCE_3_IP,
                                      secgroup_name=SECGROUP_NAME,
                                      compute_node=av_zone_2,
                                      userdata=userdata_common)
    vm_3_ip = vm_3.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_3_NAME, vm_3_ip))

    vm_5 = test_utils.create_instance(nova_client,
                                      INSTANCE_5_NAME,
                                      image_id,
                                      network_2_id,
                                      sg_id,
                                      fixed_ip=INSTANCE_5_IP,
                                      secgroup_name=SECGROUP_NAME,
                                      compute_node=av_zone_2,
                                      userdata=userdata_common)
    vm_5_ip = vm_5.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_5_NAME, vm_5_ip))

    # We boot vm5 first because we need vm5_ip for vm4 userdata
    u4 = test_utils.generate_userdata_with_ssh(
        [INSTANCE_1_IP, INSTANCE_3_IP, INSTANCE_5_IP])
    vm_4 = test_utils.create_instance(nova_client,
                                      INSTANCE_4_NAME,
                                      image_id,
                                      network_2_id,
                                      sg_id,
                                      fixed_ip=INSTANCE_4_IP,
                                      secgroup_name=SECGROUP_NAME,
                                      compute_node=av_zone_1,
                                      userdata=u4,
                                      files=files)
    vm_4_ip = vm_4.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_4_NAME, vm_4_ip))

    # We boot VM1 at the end because we need to get the IPs first to generate
    # the userdata
    u1 = test_utils.generate_userdata_with_ssh(
        [INSTANCE_2_IP, INSTANCE_3_IP, INSTANCE_4_IP, INSTANCE_5_IP])
    vm_1 = test_utils.create_instance(nova_client,
                                      INSTANCE_1_NAME,
                                      image_id,
                                      network_1_id,
                                      sg_id,
                                      fixed_ip=INSTANCE_1_IP,
                                      secgroup_name=SECGROUP_NAME,
                                      compute_node=av_zone_1,
                                      userdata=u1,
                                      files=files)
    vm_1_ip = vm_1.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_1_NAME, vm_1_ip))

    msg = ("Create VPN1 with eRT=iRT")
    logger.info(msg)
    results.add_to_summary(1, msg)
    vpn1_name = "sdnvpn-1-" + str(randint(100000, 999999))
    kwargs = {"import_targets": TARGETS_2,
              "export_targets": TARGETS_2,
              "route_targets": TARGETS_2,
              "name": vpn1_name}
    bgpvpn1 = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn1_id = bgpvpn1['bgpvpn']['id']
    logger.debug("VPN1 created details: %s" % bgpvpn1)

    msg = ("Associate network '%s' to the VPN." % NET_1_NAME)
    logger.info(msg)
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn1_id, network_1_id)
    test_utils.wait_for_bgp_net_assoc(
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
    time.sleep(30)

    # 10.10.10.12 should return sdnvpn-2 to sdnvpn-1
    results.check_ssh_output(
        vm_1, vm_1_ip, vm_2, vm_2_ip, expected=INSTANCE_2_NAME, timeout=200)
    # 10.10.11.13 should return sdnvpn-3 to sdnvpn-1
    results.check_ssh_output(
        vm_1, vm_1_ip, vm_3, vm_3_ip, expected=INSTANCE_3_NAME, timeout=30)

    results.add_to_summary(0, "-")
    msg = ("Create VPN2 with eRT=iRT")
    logger.info(msg)
    results.add_to_summary(1, msg)
    vpn2_name = "sdnvpn-2-" + str(randint(100000, 999999))
    kwargs = {"import_targets": TARGETS_1,
              "export_targets": TARGETS_1,
              "route_targets": TARGETS_1,
              "name": vpn2_name}
    bgpvpn2 = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn2_id = bgpvpn2['bgpvpn']['id']
    logger.debug("VPN created details: %s" % bgpvpn2)

    msg = ("Associate network '%s' to the VPN2." % NET_2_NAME)
    logger.info(msg)
    results.add_to_summary(1, msg)
    results.add_to_summary(0, "-")

    os_utils.create_router_association(
        neutron_client, bgpvpn2_id, router_2_id)
    test_utils.wait_for_bgp_router_assoc(
        neutron_client, bgpvpn2_id, network_2_id)

    logger.info("Waiting for the VMs to connect to each other using the"
                " updated network configuration")
    time.sleep(30)

    # 10.10.11.13 should return sdnvpn-5 to sdnvpn-4
    results.check_ssh_output(
        vm_4, vm_4_ip, vm_5, vm_5_ip, expected=INSTANCE_5_NAME, timeout=30)

    # 10.10.10.11 should return "not reachable" to sdnvpn-4
    results.check_ssh_output(
        vm_4, vm_4_ip, vm_1, vm_1_ip, expected="not reachable", timeout=30)

    results.add_to_summary(0, "=")
    logger.info("\n%s" % results.summary)

    if results.test_result == "PASS":
        logger.info("All the sub tests have passed as expected.")
    else:
        logger.info("One or more sub tests have failed.")

    status = "PASS"
    success = 100 - \
        (100 * int(results.num_tests_failed) / int(results.num_tests))
    if success < int(SUCCESS_CRITERIA):
        status = "FAILED"

    return {"status": status, "details": results.details}


if __name__ == '__main__':
    main()
