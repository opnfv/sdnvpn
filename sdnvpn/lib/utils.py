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
import time
import os
from urlparse import urlparse

import functest.utils.functest_logger as ft_logger
import functest.utils.openstack_utils as os_utils
import re

from sdnvpn.lib import config as sdnvpn_config

logger = ft_logger.Logger("sndvpn_test_utils").getLogger()

common_config = sdnvpn_config.CommonConfig()

ODL_USER = 'admin'
ODL_PASS = 'admin'


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
                    image_id,
                    network_id,
                    sg_id,
                    secgroup_name=None,
                    fixed_ip=None,
                    compute_node='',
                    userdata=None,
                    files=None,
                    **kwargs
                    ):
    if 'flavor' not in kwargs:
        kwargs['flavor'] = common_config.default_flavor

    logger.info("Creating instance '%s'..." % name)
    logger.debug(
        "Configuration:\n name=%s \n flavor=%s \n image=%s \n"
        " network=%s\n secgroup=%s \n hypervisor=%s \n"
        " fixed_ip=%s\n files=%s\n userdata=\n%s\n"
        % (name, kwargs['flavor'], image_id, network_id, sg_id,
           compute_node, fixed_ip, files, userdata))
    instance = os_utils.create_instance_and_wait_for_active(
        kwargs['flavor'],
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
    else:
        logger.debug("Instance '%s' booted successfully. IP='%s'." %
                     (name, instance.networks.itervalues().next()[0]))
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


def wait_for_instance(instance):
    logger.info("Waiting for instance %s to get a DHCP lease..." % instance.id)
    # The sleep this function replaced waited for 80s
    tries = 40
    sleep_time = 2
    pattern = "Lease of .* obtained, lease time"
    expected_regex = re.compile(pattern)
    console_log = ""
    while tries > 0 and not expected_regex.search(console_log):
        console_log = instance.get_console_output()
        time.sleep(sleep_time)
        tries -= 1

    if not expected_regex.search(console_log):
        logger.error("Instance %s seems to have failed leasing an IP."
                     % instance.id)
        return False
    return True


def wait_for_instances_up(*args):
    check = [wait_for_instance(instance) for instance in args]
    return all(check)


def wait_for_bgp_net_assoc(neutron_client, bgpvpn_id, net_id):
    tries = 30
    sleep_time = 1
    nets = []
    logger.debug("Waiting for network %s to associate with BGPVPN %s "
                 % (bgpvpn_id, net_id))

    while tries > 0 and net_id not in nets:
        nets = os_utils.get_bgpvpn_networks(neutron_client, bgpvpn_id)
        time.sleep(sleep_time)
        tries -= 1
    if net_id not in nets:
        logger.error("Association of network %s with BGPVPN %s failed" %
                     (net_id, bgpvpn_id))
        return False
    return True


def wait_for_bgp_net_assocs(neutron_client, bgpvpn_id, *args):
    check = [wait_for_bgp_net_assoc(neutron_client, bgpvpn_id, id)
             for id in args]
    # Return True if all associations succeeded
    return all(check)


def wait_for_bgp_router_assoc(neutron_client, bgpvpn_id, router_id):
    tries = 30
    sleep_time = 1
    routers = []
    logger.debug("Waiting for router %s to associate with BGPVPN %s "
                 % (bgpvpn_id, router_id))
    while tries > 0 and router_id not in routers:
        routers = os_utils.get_bgpvpn_routers(neutron_client, bgpvpn_id)
        time.sleep(sleep_time)
        tries -= 1
    if router_id not in routers:
        logger.error("Association of router %s with BGPVPN %s failed" %
                     (router_id, bgpvpn_id))
        return False
    return True


def wait_for_bgp_router_assocs(neutron_client, bgpvpn_id, *args):
    check = [wait_for_bgp_router_assoc(neutron_client, bgpvpn_id, id)
             for id in args]
    # Return True if all associations succeeded
    return all(check)


def wait_before_subtest(*args, **kwargs):
    ''' This is a placeholder.
        TODO: Replace delay with polling logic. '''
    time.sleep(30)


def assert_and_get_compute_nodes(nova_client, required_node_number=2):
    """Get the compute nodes in the deployment

    Exit if the deployment doesn't have enough compute nodes"""
    compute_nodes = os_utils.get_hypervisors(nova_client)

    num_compute_nodes = len(compute_nodes)
    if num_compute_nodes < 2:
        logger.error("There are %s compute nodes in the deployment. "
                     "Minimum number of nodes to complete the test is 2."
                     % num_compute_nodes)
        sys.exit(-1)

    logger.debug("Compute nodes: %s" % compute_nodes)
    return compute_nodes


def open_icmp_ssh(neutron_client, security_group_id):
    os_utils.create_secgroup_rule(neutron_client,
                                  security_group_id,
                                  'ingress',
                                  'icmp')
    os_utils.create_secgroup_rule(neutron_client,
                                  security_group_id,
                                  'tcp',
                                  80, 80)


def get_controller_ip():
    # OS_AUTH_URL=http://172.16.0.16:5000/v2.0
    auth_url = os.environ.get('OS_AUTH_URL')
    return urlparse(auth_url).hostname
