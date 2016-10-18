#!/usr/bin/python
#
# Copyright (c) 2015 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
import sys

import functest.utils.functest_logger as ft_logger
import functest.utils.openstack_utils as os_utils


logger = ft_logger.Logger("sndvpn_test_utils").getLogger()


def create_net(neutron_client, name):
    logger.debug("Creating network %s", name)
    net_id = os_utils.create_neutron_net(neutron_client, name)
    if not net_id:
        logger.error(
            "There has been a problem when creating the neutron network")
        sys.exit(-1)
    return net_id


def create_subnet(neutron_client, name, cidr, net_id):
    logger.debug("Creating subnet %s in network %s with cidr %s",
                 name, net_id, cidr)
    subnet_id = os_utils.create_neutron_subnet(neutron_client,
                                               name,
                                               cidr,
                                               net_id)
    if not subnet_id:
        logger.error(
            "There has been a problem when creating the neutron subnet")
        sys.exit(-1)
    return subnet_id


def create_network(neutron_client, net, subnet1, cidr1,
                   router, subnet2=None, cidr2=None):
    """Network assoc will not work for networks/subnets created by this function.

    It is an ODL limitation due to it handling routers as vpns.
    See https://bugs.opendaylight.org/show_bug.cgi?id=6962"""
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
    subnet_id = network_dic["subnet_id"]
    router_id = network_dic["router_id"]

    if subnet2 is not None:
        logger.debug("Creating and attaching a second subnet...")
        subnet_id = os_utils.create_neutron_subnet(
            neutron_client, subnet2, cidr2, net_id)
        if not subnet_id:
            logger.error(
                "There has been a problem when creating the second subnet")
            sys.exit(-1)
        logger.debug("Subnet '%s' created successfully" % subnet_id)
    return net_id, subnet_id, router_id


def create_instance(nova_client,
                    name,
                    flavor,
                    image_id,
                    network_id,
                    sg_id,
                    secgroup_name=None,
                    fixed_ip=None,
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

    if secgroup_name:
        logger.debug("Adding '%s' to security group '%s'..."
                     % (name, secgroup_name))
    else:
        logger.debug("Adding '%s' to security group '%s'..."
                     % (name, sg_id))
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
