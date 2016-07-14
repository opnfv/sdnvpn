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


parser = argparse.ArgumentParser()

parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")

args = parser.parse_args()

""" logging configuration """
logger = ft_logger.Logger("sdnvpn-testcase-1").getLogger()

REPO_PATH = os.environ['repos_dir'] + '/sdnvpn/'
HOME = os.environ['HOME'] + "/"

VM_BOOT_TIMEOUT = 180

config_file = REPO_PATH + 'test/functest/config.yaml'

INSTANCE_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.instance_1_name", config_file)
INSTANCE_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.instance_2_name", config_file)
INSTANCE_3_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.instance_3_name", config_file)
INSTANCE_4_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.instance_4_name", config_file)
INSTANCE_5_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.instance_5_name", config_file)
FLAVOR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.flavor", config_file)
IMAGE_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.image_name", config_file)
IMAGE_FILENAME = ft_utils.get_parameter_from_yaml(
    "general.openstack.image_file_name")
IMAGE_FORMAT = ft_utils.get_parameter_from_yaml(
    "general.openstack.image_disk_format")
IMAGE_PATH = ft_utils.get_parameter_from_yaml(
    "general.directories.dir_functest_data") + "/" + IMAGE_FILENAME

# NEUTRON Private Network parameters

NET_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.net_1_name", config_file)
SUBNET_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.subnet_1_name", config_file)
SUBNET_1_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.subnet_1_cidr", config_file)
ROUTER_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.router_1_name", config_file)
NET_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.net_2_name", config_file)
SUBNET_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.subnet_2_name", config_file)
SUBNET_2_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.subnet_2_cidr", config_file)
ROUTER_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.router_2_name", config_file)
SECGROUP_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.sdnvpn_sg_name", config_file)
SECGROUP_DESCR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.sdnvpn_sg_descr", config_file)

TEST_DB = ft_utils.get_parameter_from_yaml("results.test_db_url")

TEST_RESULT = "PASS"
SUMMARY = ""
LINE_LENGTH = 60  # length for the summary table
DETAILS = []


def create_network(neutron_client, net, subnet, router, cidr):
    network_dic = os_utils.create_network_full(logger,
                                               neutron_client,
                                               net,
                                               subnet,
                                               router,
                                               cidr)
    if not network_dic:
        logger.error(
            "There has been a problem when creating the neutron network")
        sys.exit(-1)
    return network_dic["net_id"]


def create_instance(nova_client,
                    name,
                    flavor,
                    image_id,
                    network_id,
                    sg_id,
                    compute_node='',
                    userdata=None):
    logger.info("Creating instance '%s'..." % name)
    logger.debug(
        "Configuration:\n name=%s \n flavor=%s \n image=%s \n "
        "network=%s \n secgroup=%s \n hypervisor=%s \n userdata=%s\n"
        % (name, flavor, image_id, network_id, sg_id, compute_node, userdata))
    instance = os_utils.create_instance_and_wait_for_active(
        flavor,
        image_id,
        network_id,
        name,
        config_drive=True,
        userdata=userdata,
        av_zone=compute_node)

    if instance is None:
        logger.error("Error while booting instance.")
        sys.exit(-1)
    # Retrieve IP of INSTANCE
    # instance_ip = instance.networks.get(network_id)[0]

    logger.debug("Adding '%s' to security group '%s'..."
                 % (name, SECGROUP_NAME))
    os_utils.add_secgroup_to_instance(nova_client, instance.id, sg_id)

    return instance


def generate_ping_userdata(ips_array):
    ips = ""
    for ip in ips_array:
        ips = ("%s %s" % (ips, ip))

    ips = ips.replace('  ', ' ')
    return ("#!/bin/sh\n"
            "set%s\n"
            "while true; do\n"
            " for i do\n"
            "  ip=$i\n"
            "  ping -c 1 $ip 2>&1 >/dev/null\n"
            "  RES=$?\n"
            "  if [ \"Z$RES\" = \"Z0\" ] ; then\n"
            "   echo ping $ip OK\n"
            "  else echo ping $ip KO\n"
            "  fi\n"
            " done\n"
            " sleep 1\n"
            "done\n"
            % ips)


def get_ping_status(vm_source, ip_source,
                    vm_target, ip_target,
                    expected="PASS", timeout=30):
    console_log = vm_source.get_console_output()

    global TEST_RESULT

    if "request failed" in console_log:
        # Normally, cirros displays this message when userdata fails
        logger.debug("It seems userdata is not supported in "
                     "nova boot...")
        return False
    else:
        tab = ("%s" % (" " * 53))
        expected_result = 'can ping' if expected == 'PASS' else 'cannot ping'
        test_case_name = ("'%s' %s '%s'" %
                          (vm_source.name, expected_result, vm_target.name))
        logger.debug("\n%sPing\n%sfrom '%s' (%s)\n%sto '%s' (%s).\n"
                     "%s-->Expected result: %s.\n"
                     % (tab, tab, vm_source.name, ip_source,
                        tab, vm_target.name, ip_target,
                        tab, expected_result))
        while True:
            console_log = vm_source.get_console_output()
            # the console_log is a long string, we want to take
            # the last 4 lines (for example)
            lines = console_log.split('\n')
            last_n_lines = lines[-5:]
            if ("ping %s OK" % ip_target) in last_n_lines:
                msg = ("'%s' can ping '%s'" % (vm_source.name, vm_target.name))
                if expected == "PASS":
                    logger.debug("[PASS] %s" % msg)
                    add_to_summary(2, "PASS", test_case_name)
                else:
                    logger.debug("[FAIL] %s" % msg)
                    TEST_RESULT = "FAIL"
                    add_to_summary(2, "FAIL", test_case_name)
                    logger.debug("\n%s" % last_n_lines)
                break
            elif ("ping %s KO" % ip_target) in last_n_lines:
                msg = ("'%s' cannot ping '%s'" %
                       (vm_source.name, vm_target.name))
                if expected == "FAIL":
                    logger.debug("[PASS] %s" % msg)
                    add_to_summary(2, "PASS", test_case_name)
                else:
                    logger.debug("[FAIL] %s" % msg)
                    TEST_RESULT = "FAIL"
                    add_to_summary(2, "FAIL", test_case_name)
                break
            time.sleep(1)
            timeout -= 1
            if timeout == 0:
                TEST_RESULT = "FAIL"
                logger.debug("[FAIL] Timeout reached for '%s'. No ping output "
                             "captured in the console log" % vm_source.name)
                add_to_summary(2, "FAIL", test_case_name)
                break


def add_to_summary(num_cols, col1, col2=""):
    global SUMMARY, LINE_LENGTH, DETAILS
    if num_cols == 0:
        SUMMARY += ("+%s+\n" % (col1 * (LINE_LENGTH - 2)))
    elif num_cols == 1:
        SUMMARY += ("| " + col1.ljust(LINE_LENGTH - 3) + "|\n")
    elif num_cols == 2:
        SUMMARY += ("| %s" % col1.ljust(7) + "| ")
        SUMMARY += (col2.ljust(LINE_LENGTH - 12) + "|\n")
        DETAILS.append({col2: col1})


def main():
    global TEST_RESULT, SUMMARY

    add_to_summary(0, "=")
    add_to_summary(2, "STATUS", "SUBTEST")
    add_to_summary(0, "=")

    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()
    glance_client = os_utils.get_glance_client()

    image_id = os_utils.create_glance_image(glance_client,
                                            IMAGE_NAME,
                                            IMAGE_PATH,
                                            disk=IMAGE_FORMAT,
                                            container="bare",
                                            public=True,
                                            logger=logger)
    network_1_id = create_network(neutron_client,
                                  NET_1_NAME,
                                  SUBNET_1_NAME,
                                  ROUTER_1_NAME,
                                  SUBNET_1_CIDR)
    network_2_id = create_network(neutron_client,
                                  NET_2_NAME,
                                  SUBNET_2_NAME,
                                  ROUTER_2_NAME,
                                  SUBNET_2_CIDR)
    sg_id = os_utils.create_security_group_full(logger, neutron_client,
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
    vm_2 = create_instance(nova_client,
                           INSTANCE_2_NAME,
                           FLAVOR,
                           image_id,
                           network_1_id,
                           sg_id,
                           av_zone_1)
    vm_2_ip = vm_2.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_2_NAME, vm_2_ip))

    vm_3 = create_instance(nova_client,
                           INSTANCE_3_NAME,
                           FLAVOR, image_id,
                           network_1_id,
                           sg_id,
                           av_zone_2)
    vm_3_ip = vm_3.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_3_NAME, vm_3_ip))

    vm_5 = create_instance(nova_client,
                           INSTANCE_5_NAME,
                           FLAVOR,
                           image_id,
                           network_2_id,
                           sg_id,
                           av_zone_2)
    vm_5_ip = vm_5.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_5_NAME, vm_5_ip))

    # We boot vm5 first because we need vm5_ip for vm4 userdata
    u4 = generate_ping_userdata([vm_5_ip])
    vm_4 = create_instance(nova_client,
                           INSTANCE_4_NAME,
                           FLAVOR,
                           image_id,
                           network_2_id,
                           sg_id,
                           av_zone_1,
                           userdata=u4)
    vm_4_ip = vm_4.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_4_NAME, vm_4_ip))

    # We boot VM1 at the end because we need to get the IPs first to generate
    # the userdata
    u1 = generate_ping_userdata([vm_2_ip, vm_3_ip, vm_4_ip, vm_5_ip])
    vm_1 = create_instance(nova_client,
                           INSTANCE_1_NAME,
                           FLAVOR,
                           image_id,
                           network_1_id,
                           sg_id,
                           av_zone_1,
                           userdata=u1)
    vm_1_ip = vm_1.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_1_NAME, vm_1_ip))
    msg = ("Create VPN with eRT<>iRT")
    logger.info("\n\n--> %s ..." % msg)
    add_to_summary(1, msg)
    vpn_name = "sdnvpn-" + str(randint(100000, 999999))
    kwargs = {"import_targets": "88:88",
              "export_targets": "55:55",
              "name": vpn_name}
    bgpvpn = os_utils.create_bgpvpn(neutron_client, **kwargs)
    bgpvpn_id = bgpvpn['bgpvpn']['id']
    logger.debug("VPN created details: %s" % bgpvpn)

    msg = ("Associate network '%s' to the VPN." % NET_1_NAME)
    logger.info("\n\n--> %s..." % msg)
    add_to_summary(1, msg)
    add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn_id, network_1_id)

    # Wait for VMs to get ips.
    time.sleep(80)

    # Ping from VM1 to VM2 should work
    get_ping_status(vm_1, vm_1_ip, vm_2, vm_2_ip, expected="PASS", timeout=200)
    # Ping from VM1 to VM3 should work
    get_ping_status(vm_1, vm_1_ip, vm_3, vm_3_ip, expected="PASS", timeout=30)
    # Ping from VM1 to VM4 should not work
    get_ping_status(vm_1, vm_1_ip, vm_4, vm_4_ip, expected="FAIL", timeout=30)

    msg = ("Associate network '%s' to the VPN." % NET_2_NAME)
    logger.info("\n\n--> %s..." % msg)
    add_to_summary(0, "-")
    add_to_summary(1, msg)
    add_to_summary(0, "-")
    os_utils.create_network_association(
        neutron_client, bgpvpn_id, network_2_id)

    # Wait a bit for this to take effect
    time.sleep(10)

    # Ping from VM4 to VM5 should work
    get_ping_status(vm_4, vm_4_ip, vm_5, vm_5_ip, expected="PASS", timeout=30)
    # Ping from VM1 to VM4 should not work
    get_ping_status(vm_1, vm_1_ip, vm_4, vm_4_ip, expected="FAIL", timeout=30)
    # Ping from VM1 to VM5 should not work
    get_ping_status(vm_1, vm_1_ip, vm_5, vm_5_ip, expected="FAIL", timeout=30)

    msg = ("Update VPN with eRT=iRT ...")
    logger.info("\n\n--> %s..." % msg)
    add_to_summary(0, "-")
    add_to_summary(1, msg)
    add_to_summary(0, "-")
    kwargs = {"import_targets": "88:88",
              "export_targets": "88:88",
              "name": vpn_name}
    bgpvpn = os_utils.update_bgpvpn(neutron_client, bgpvpn_id, **kwargs)
    # Wait a bit for this to take effect
    time.sleep(10)

    # Ping from VM1 to VM4 should work
    get_ping_status(vm_1, vm_1_ip, vm_4, vm_4_ip, expected="PASS", timeout=30)
    # Ping from VM1 to VM5 should work
    get_ping_status(vm_1, vm_1_ip, vm_5, vm_5_ip, expected="PASS", timeout=30)

    add_to_summary(0, "=")
    logger.info("\n%s" % SUMMARY)

    if TEST_RESULT == "PASS":
        logger.info("All the ping tests have passed as expected.")
    else:
        logger.info("One or more ping tests have failed.")

    return {"status": TEST_RESULT, "details": DETAILS}


if __name__ == '__main__':
    main()
