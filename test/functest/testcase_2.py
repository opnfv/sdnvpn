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

logger = ft_logger.Logger("sdnvpn-testcase-2").getLogger()

REPO_PATH = os.environ['repos_dir'] + '/sdnvpn/'

VM_BOOT_TIMEOUT = 180

config_file = REPO_PATH + 'test/functest/config.yaml'

INSTANCE_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.instance_1_name", config_file)
INSTANCE_1_IP = "10.10.10.11"
INSTANCE_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.instance_2_name", config_file)
INSTANCE_2_IP = "10.10.10.12"
INSTANCE_3_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.instance_3_name", config_file)
INSTANCE_3_IP = "10.10.11.13"
INSTANCE_4_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.instance_4_name", config_file)
INSTANCE_4_IP = "10.10.10.12"
INSTANCE_5_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.instance_5_name", config_file)
INSTANCE_5_IP = "10.10.11.13"
FLAVOR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.flavor", config_file)
IMAGE_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.image_name", config_file)
IMAGE_FILENAME = ft_utils.get_parameter_from_yaml(
    "general.openstack.image_file_name")
IMAGE_FORMAT = ft_utils.get_parameter_from_yaml(
    "general.openstack.image_disk_format")
IMAGE_PATH = ft_utils.get_parameter_from_yaml(
    "general.directories.dir_functest_data") + "/" + IMAGE_FILENAME

KEYFILE_PATH = REPO_PATH + 'test/functest/id_rsa'

# NEUTRON Private Network parameters

NET_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.net_1_name", config_file)
SUBNET_1a_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.subnet_1a_name", config_file)
SUBNET_1a_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.subnet_1a_cidr", config_file)
SUBNET_1b_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.subnet_1b_name", config_file)
SUBNET_1b_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.subnet_1b_cidr", config_file)
ROUTER_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.router_1_name", config_file)
NET_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.net_2_name", config_file)
SUBNET_2a_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.subnet_2a_name", config_file)
SUBNET_2a_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.subnet_2a_cidr", config_file)
SUBNET_2b_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.subnet_2b_name", config_file)
SUBNET_2b_CIDR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.subnet_2b_cidr", config_file)
ROUTER_1_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.router_1_name", config_file)
ROUTER_2_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.router_2_name", config_file)
SECGROUP_NAME = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.sdnvpn_sg_name", config_file)
SECGROUP_DESCR = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.sdnvpn_sg_descr", config_file)
TARGETS_1 = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.targets1", config_file)
TARGETS_2 = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_2.targets2", config_file)
SUCCESS_CRITERIA = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.succes_criteria", config_file)
TEST_DB = ft_utils.get_parameter_from_yaml("results.test_db_url")

TEST_RESULT = "PASS"
SUMMARY = ""
LINE_LENGTH = 90  # length for the summary table
DETAILS = []
NUM_TESTS = 0
NUM_TESTS_FAILED = 0


def create_network(neutron_client, net, subnet1, cidr1,
                   router, subnet2=None, cidr2=None):
    network_dic = os_utils.create_network_full(neutron_client,
                                               net,
                                               subnet1,
                                               router,
                                               cidr1)
    if not network_dic:
        logger.error(
            "There has been a problem when creating the neutron network")
        sys.exit(-1)
    net_id = network_dic["net_id"]
    if subnet2 is not None:
        logger.debug("Creating and attaching a second subnet...")
        subnet_id = os_utils.create_neutron_subnet(
            neutron_client, subnet2, cidr2, net_id)
        if not subnet_id:
            logger.error(
                "There has been a problem when creating the second subnet")
            sys.exit(-1)
        logger.debug("Subnet '%s' created successfully" % subnet_id)
    return net_id


def create_instance(nova_client,
                    name,
                    flavor,
                    image_id,
                    network_id,
                    sg_id,
                    fixed_ip,
                    compute_node='',
                    userdata=None,
                    files=None):
    logger.info("Creating instance '%s'..." % name)
    logger.debug(
        "Configuration:\n name=%s \n flavor=%s \n image=%s \n"
        " network=%s\n secgroup=%s \n hypervisor=%s \n"
        " fixed_ip=%s\n files=%s\n userdata=\n%s\n"
        % (name, flavor, image_id, network_id, sg_id,
           compute_node, fixed_ip, files, userdata))
    instance = os_utils.create_instance_and_wait_for_active(
        flavor,
        image_id,
        network_id,
        name,
        config_drive=True,
        userdata=userdata,
        av_zone=compute_node,
        fixed_ip=fixed_ip,
        files=files)

    if instance is None:
        logger.error("Error while booting instance.")
        sys.exit(-1)
    # Retrieve IP of INSTANCE
    # instance_ip = instance.networks.get(network_id)[0]

    logger.debug("Adding '%s' to security group '%s'..."
                 % (name, SECGROUP_NAME))
    os_utils.add_secgroup_to_instance(nova_client, instance.id, sg_id)

    return instance


def generate_userdata_common():
    return ("#!/bin/sh\n"
            "sudo mkdir -p /home/cirros/.ssh/\n"
            "sudo chown cirros:cirros /home/cirros/.ssh/\n"
            "sudo chown cirros:cirros /home/cirros/id_rsa\n"
            "mv /home/cirros/id_rsa /home/cirros/.ssh/\n"
            "sudo echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgnWtSS98Am516e"
            "stBsq0jbyOB4eLMUYDdgzsUHsnxFQCtACwwAg9/2uq3FoGUBUWeHZNsT6jcK9"
            "sCMEYiS479CUCzbrxcd8XaIlK38HECcDVglgBNwNzX/WDfMejXpKzZG61s98rU"
            "ElNvZ0YDqhaqZGqxIV4ejalqLjYrQkoly3R+2k= "
            "cirros@test1>/home/cirros/.ssh/authorized_keys\n"
            "sudo chown cirros:cirros /home/cirros/.ssh/authorized_keys\n"
            "chmod 700 /home/cirros/.ssh\n"
            "chmod 644 /home/cirros/.ssh/authorized_keys\n"
            "chmod 600 /home/cirros/.ssh/id_rsa\n"
            )


def generate_userdata_with_ssh(ips_array):
    u1 = generate_userdata_common()

    ips = ""
    for ip in ips_array:
        ips = ("%s %s" % (ips, ip))

    ips = ips.replace('  ', ' ')
    u2 = ("#!/bin/sh\n"
          "set%s\n"
          "while true; do\n"
          " for i do\n"
          "  ip=$i\n"
          "  hostname=$(ssh -y -i /home/cirros/.ssh/id_rsa "
          "cirros@$ip 'hostname' </dev/zero 2>/dev/null)\n"
          "  RES=$?\n"
          "  if [ \"Z$RES\" = \"Z0\" ]; then echo $ip $hostname;\n"
          "  else echo $ip 'not reachable';fi;\n"
          " done\n"
          " sleep 1\n"
          "done\n"
          % ips)
    return (u1 + u2)


def check_ssh_output(vm_source, ip_source,
                     vm_target, ip_target,
                     expected, timeout=30):
    console_log = vm_source.get_console_output()

    global TEST_RESULT

    if "request failed" in console_log:
        # Normally, cirros displays this message when userdata fails
        logger.debug("It seems userdata is not supported in "
                     "nova boot...")
        return False
    else:
        tab = ("%s" % (" " * 53))
        test_case_name = ("[%s] returns 'I am %s' to '%s'[%s]" %
                          (ip_target, expected,
                           vm_source.name, ip_source))
        logger.debug("%sSSH\n%sfrom '%s' (%s)\n%sto '%s' (%s).\n"
                     "%s-->Expected result: %s.\n"
                     % (tab, tab, vm_source.name, ip_source,
                        tab, vm_target.name, ip_target,
                        tab, expected))
        while True:
            console_log = vm_source.get_console_output()
            # the console_log is a long string, we want to take
            # the last 4 lines (for example)
            lines = console_log.split('\n')
            last_n_lines = lines[-5:]
            if ("%s %s" % (ip_target, expected)) in last_n_lines:
                logger.debug("[PASS] %s" % test_case_name)
                add_to_summary(2, "PASS", test_case_name)
                break
            elif ("%s not reachable" % ip_target) in last_n_lines:
                logger.debug("[FAIL] %s" % test_case_name)
                add_to_summary(2, "FAIL", test_case_name)
                TEST_RESULT = "FAIL"
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
    global SUMMARY, LINE_LENGTH, NUM_TESTS, NUM_TESTS_FAILED
    if num_cols == 0:
        SUMMARY += ("+%s+\n" % (col1 * (LINE_LENGTH - 2)))
    elif num_cols == 1:
        SUMMARY += ("| " + col1.ljust(LINE_LENGTH - 3) + "|\n")
    elif num_cols == 2:
        SUMMARY += ("| %s" % col1.ljust(7) + "| ")
        SUMMARY += (col2.ljust(LINE_LENGTH - 12) + "|\n")
        if col1 in ("FAIL", "PASS"):
            DETAILS.append({col2: col1})
            NUM_TESTS += 1
            if col1 == "FAIL":
                NUM_TESTS_FAILED += 1


def main():
    global TEST_RESULT, SUMMARY

    add_to_summary(0, "=")
    add_to_summary(2, "STATUS", "SUBTEST")
    add_to_summary(0, "=")

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
    network_1_id = create_network(neutron_client,
                                  NET_1_NAME,
                                  SUBNET_1a_NAME,
                                  SUBNET_1a_CIDR,
                                  ROUTER_1_NAME,
                                  SUBNET_1b_NAME,
                                  SUBNET_1b_CIDR)
    network_2_id = create_network(neutron_client,
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

    # boot INTANCES
    userdata_common = generate_userdata_common()
    vm_2 = create_instance(nova_client,
                           INSTANCE_2_NAME,
                           FLAVOR,
                           image_id,
                           network_1_id,
                           sg_id,
                           INSTANCE_2_IP,
                           compute_node=av_zone_1,
                           userdata=userdata_common)
    vm_2_ip = vm_2.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_2_NAME, vm_2_ip))

    vm_3 = create_instance(nova_client,
                           INSTANCE_3_NAME,
                           FLAVOR, image_id,
                           network_1_id,
                           sg_id,
                           INSTANCE_3_IP,
                           compute_node=av_zone_2,
                           userdata=userdata_common)
    vm_3_ip = vm_3.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_3_NAME, vm_3_ip))

    vm_5 = create_instance(nova_client,
                           INSTANCE_5_NAME,
                           FLAVOR,
                           image_id,
                           network_2_id,
                           sg_id,
                           fixed_ip=INSTANCE_5_IP,
                           compute_node=av_zone_2,
                           userdata=userdata_common)
    vm_5_ip = vm_5.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_5_NAME, vm_5_ip))

    # We boot vm5 first because we need vm5_ip for vm4 userdata
    u4 = generate_userdata_with_ssh(
        [INSTANCE_1_IP, INSTANCE_3_IP, INSTANCE_5_IP])
    vm_4 = create_instance(nova_client,
                           INSTANCE_4_NAME,
                           FLAVOR,
                           image_id,
                           network_2_id,
                           sg_id,
                           fixed_ip=INSTANCE_4_IP,
                           compute_node=av_zone_1,
                           userdata=u4,
                           files=files)
    vm_4_ip = vm_4.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_4_NAME, vm_4_ip))

    # We boot VM1 at the end because we need to get the IPs first to generate
    # the userdata
    u1 = generate_userdata_with_ssh(
        [INSTANCE_2_IP, INSTANCE_3_IP, INSTANCE_4_IP, INSTANCE_5_IP])
    vm_1 = create_instance(nova_client,
                           INSTANCE_1_NAME,
                           FLAVOR,
                           image_id,
                           network_1_id,
                           sg_id,
                           fixed_ip=INSTANCE_1_IP,
                           compute_node=av_zone_1,
                           userdata=u1,
                           files=files)
    vm_1_ip = vm_1.networks.itervalues().next()[0]
    logger.debug("Instance '%s' booted successfully. IP='%s'." %
                 (INSTANCE_1_NAME, vm_1_ip))

    msg = ("Create VPN1 with eRT=iRT")
    logger.info(msg)
    add_to_summary(1, msg)
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
    add_to_summary(1, msg)
    add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn1_id, network_1_id)

    # Wait for VMs to get ips.
    time.sleep(80)

    # 10.10.10.12 should return sdnvpn-2 to sdnvpn-1
    check_ssh_output(
        vm_1, vm_1_ip, vm_2, vm_2_ip, expected=INSTANCE_2_NAME, timeout=200)
    # 10.10.11.13 should return sdnvpn-3 to sdnvpn-1
    check_ssh_output(
        vm_1, vm_1_ip, vm_3, vm_3_ip, expected=INSTANCE_3_NAME, timeout=30)

    add_to_summary(0, "-")
    msg = ("Create VPN2 with eRT=iRT")
    logger.info(msg)
    add_to_summary(1, msg)
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
    add_to_summary(1, msg)
    add_to_summary(0, "-")

    os_utils.create_network_association(
        neutron_client, bgpvpn2_id, network_2_id)

    # Wait a bit for this to take effect
    time.sleep(80)

    # 10.10.11.13 should return sdnvpn-5 to sdnvpn-4
    check_ssh_output(
        vm_4, vm_4_ip, vm_5, vm_5_ip, expected=INSTANCE_5_NAME, timeout=30)

    # 10.10.10.11 should return "not reachable" to sdnvpn-4
    check_ssh_output(
        vm_4, vm_4_ip, vm_1, vm_1_ip, expected="not reachable", timeout=30)

    add_to_summary(0, "=")
    logger.info("\n%s" % SUMMARY)

    if TEST_RESULT == "PASS":
        logger.info("All the sub tests have passed as expected.")
    else:
        logger.info("One or more sub tests have failed.")

    status = "PASS"
    success = 100 - (100 * int(NUM_TESTS_FAILED) / int(NUM_TESTS))
    if success < int(SUCCESS_CRITERIA):
        status = "FAILED"

    return {"status": status, "details": DETAILS}


if __name__ == '__main__':
    main()
