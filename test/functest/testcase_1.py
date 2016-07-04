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
import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils
import functest.utils.openstack_utils as os_utils

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")

args = parser.parse_args()

""" logging configuration """
logger = ft_logger.Logger("creat_instance_and_ip").getLogger()

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
                    compute_node):
    logger.info("Creating instance '%s'..." % name)
    logger.debug(
        "Configuration:\n name=%s \n flavor=%s \n image=%s \n "
        "network=%s \n" % (name, flavor, image_id, network_id))
    instance = os_utils.create_instance_and_wait_for_active(
        flavor, image_id, network_id, name, av_zone=compute_node)

    if instance is None:
        logger.error("Error while booting instance.")
        sys.exit(-1)
    # Retrieve IP of INSTANCE
    instance_ip = instance.networks.get(network_id)[0]
    logger.debug("Instance '%s' got private ip '%s'." %
                 (name, instance_ip))

    logger.info("Adding '%s' to security group '%s'..."
                % (name, SECGROUP_NAME))
    os_utils.add_secgroup_to_instance(nova_client, instance.id, sg_id)


def main():

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

    logger.info("Compute nodes: %s" % compute_nodes)
    compute_node_1 = compute_nodes[0]
    compute_node_2 = compute_nodes[1]

    # boot INTANCES
    create_instance(
        nova_client,
        INSTANCE_1_NAME,
        FLAVOR,
        image_id,
        network_1_id,
        sg_id,
        compute_node_1)

    create_instance(
        nova_client,
        INSTANCE_2_NAME,
        FLAVOR,
        image_id,
        network_1_id,
        sg_id,
        compute_node_1)

    create_instance(
        nova_client,
        INSTANCE_3_NAME,
        FLAVOR, image_id,
        network_1_id,
        sg_id,
        compute_node_2)

    create_instance(
        nova_client,
        INSTANCE_4_NAME,
        FLAVOR,
        image_id,
        network_2_id,
        sg_id,
        compute_node_1)

    create_instance(
        nova_client,
        INSTANCE_5_NAME,
        FLAVOR,
        image_id,
        network_2_id,
        sg_id,
        compute_node_2)
    # TODO: create instance on specific compute

    sys.exit(0)

if __name__ == '__main__':
    main()
