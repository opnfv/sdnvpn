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
import sys
import time
import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as functest_utils
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
#TODO(etimirn-07Jul2016): networks need to be changed for TC2

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

    logger.info("Adding '%s' to security group '%s'..."
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


def generate_hostcheck_userdata(ips_array):
   #TODO(etimirn-07Jul2016): add new array code from Jose

   return ("#!/bin/sh\n"
           "ips=%s\n"
           "while true; do\n"
           "for ip in ${ips[@]}; do\n"
           "ping -c 1 $ip 2>&1 >/dev/null\n "
           "RES=$?\n"
           "if [ \"Z$RES\" = \"Z0\" ] ; then\n"
           "echo ping $ip OK\n"
           "else echo ping $ip KO\n"
           "fi\n"
           "done\n"
           "sleep 1\n"
           "done\n"
           % ips)


def get_ping_status(vm, ip):
    console_log = vm.get_console_output()
    output = ("ping %s OK" % ip)
    # logger.debug(console_log)
    if "request failed" in console_log:
        logger.debug("It seems userdata is not supported in "
                     "nova boot...")
        return False
    else:
        if output in console_log:
            return True
        else:
            return False


def
 main():
    pass


if __name__ == '__main__':
    main()
