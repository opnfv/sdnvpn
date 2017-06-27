#!/usr/bin/python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
import logging
import os
import sys
import time
import requests
import re
import subprocess

import functest.utils.openstack_utils as os_utils
from opnfv.deployment.factory import Factory as DeploymentFactory

from sdnvpn.lib import config as sdnvpn_config

logger = logging.getLogger('sndvpn_test_utils')

common_config = sdnvpn_config.CommonConfig()

ODL_USER = 'admin'
ODL_PASS = 'admin'


def create_custom_flavor():
    return os_utils.get_or_create_flavor(common_config.custom_flavor_name,
                                         common_config.custom_flavor_ram,
                                         common_config.custom_flavor_disk,
                                         common_config.custom_flavor_vcpus)


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
    """Network assoc won't work for networks/subnets created by this function.

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
            "  ping -c 10 $ip 2>&1 >/dev/null\n"
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


def get_installerHandler():
    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    installer_ip = get_installer_ip()

    if installer_type not in ["fuel", "apex"]:
        raise ValueError("%s is not supported" % installer_type)
    else:
        if installer_type in ["apex"]:
            developHandler = DeploymentFactory.get_handler(
                installer_type,
                installer_ip,
                'root',
                pkey_file="/root/.ssh/id_rsa")

        if installer_type in ["fuel"]:
            developHandler = DeploymentFactory.get_handler(
                installer_type,
                installer_ip,
                'root',
                'r00tme')
        return developHandler


def get_nodes():
    developHandler = get_installerHandler()
    return developHandler.get_nodes()


def get_installer_ip():
    return str(os.environ['INSTALLER_IP'])


def get_instance_ip(instance):
    instance_ip = instance.networks.itervalues().next()[0]
    return instance_ip


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


def open_icmp(neutron_client, security_group_id):
    if os_utils.check_security_group_rules(neutron_client,
                                           security_group_id,
                                           'ingress',
                                           'icmp'):

        if not os_utils.create_secgroup_rule(neutron_client,
                                             security_group_id,
                                             'ingress',
                                             'icmp'):
            logger.error("Failed to create icmp security group rule...")
    else:
        logger.info("This rule exists for security group: %s"
                    % security_group_id)


def open_http_port(neutron_client, security_group_id):
    if os_utils.check_security_group_rules(neutron_client,
                                           security_group_id,
                                           'ingress',
                                           'tcp',
                                           80, 80):

        if not os_utils.create_secgroup_rule(neutron_client,
                                             security_group_id,
                                             'ingress',
                                             'tcp',
                                             80, 80):

            logger.error("Failed to create http security group rule...")
    else:
        logger.info("This rule exists for security group: %s"
                    % security_group_id)


def open_bgp_port(neutron_client, security_group_id):
    if os_utils.check_security_group_rules(neutron_client,
                                           security_group_id,
                                           'ingress',
                                           'tcp',
                                           179, 179):

        if not os_utils.create_secgroup_rule(neutron_client,
                                             security_group_id,
                                             'ingress',
                                             'tcp',
                                             179, 179):
            logger.error("Failed to create bgp security group rule...")
    else:
        logger.info("This rule exists for security group: %s"
                    % security_group_id)


def exec_cmd(cmd, verbose):
    success = True
    logger.debug("Executing '%s'" % cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    output = ""
    for line in iter(p.stdout.readline, b''):
        output += line

    if verbose:
        logger.debug(output)

    p.stdout.close()
    returncode = p.wait()
    if returncode != 0:
        logger.error("Command %s failed to execute." % cmd)
        success = False

    return output, success


def check_odl_fib(ip, controller_ip):
    """Check that there is an entry in the ODL Fib for `ip`"""
    url = "http://" + controller_ip + \
          ":8181/restconf/config/odl-fib:fibEntries/"
    logger.debug("Querring '%s' for FIB entries", url)
    res = requests.get(url, auth=(ODL_USER, ODL_PASS))
    if res.status_code != 200:
        logger.error("OpenDaylight response status code: %s", res.status_code)
        return False
    logger.debug("Checking whether '%s' is in the OpenDaylight FIB"
                 % controller_ip)
    logger.debug("OpenDaylight FIB: \n%s" % res.text)
    return ip in res.text


def run_odl_cmd(odl_node, cmd):
    '''Run a command in the OpenDaylight Karaf shell

    This is a bit flimsy because of shell quote escaping, make sure that
    the cmd passed does not have any top level double quotes or this
    function will break.

    The /dev/null is used because client works, but outputs something
    that contains "ERROR" and run_cmd doesn't like that.

    '''
    karaf_cmd = ('/opt/opendaylight/bin/client -h 127.0.0.1 "%s"'
                 ' 2>/dev/null' % cmd)
    return odl_node.run_cmd(karaf_cmd)


def wait_for_cloud_init(instance):
    success = True
    # ubuntu images take a long time to start
    tries = 20
    sleep_time = 30
    logger.info("Waiting for cloud init of instance: {}"
                "".format(instance.name))
    while tries > 0:
        instance_log = instance.get_console_output()
        if "Failed to run module" in instance_log:
            success = False
            logger.error("Cloud init failed to run. Reason: %s",
                         instance_log)
            break
        if re.search(r"Cloud-init finished", instance_log):
            success = True
            break
        time.sleep(sleep_time)
        tries = tries - 1

    if tries == 0:
        logger.error("Cloud init timed out"
                     ". Reason: %s",
                     instance_log)
        success = False
    logger.info("Finished waiting for cloud init of instance {} result was {}"
                "".format(instance.name, success))
    return success


def attach_instance_to_ext_br(instance, compute_node):
    libvirt_instance_name = getattr(instance, "OS-EXT-SRV-ATTR:instance_name")
    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    if installer_type == "fuel":
        bridge = "br-ex"
    elif installer_type == "apex":
        # In Apex, br-ex is an ovs bridge and virsh attach-interface
        # won't just work. We work around it by creating a linux
        # bridge, attaching that to br-ex with a veth pair
        # and virsh-attaching the instance to the linux-bridge
        bridge = "br-quagga"
        cmd = """
        set -e
        if ! sudo brctl show |grep -q ^{bridge};then
          sudo brctl addbr {bridge}
          sudo ip link set {bridge} up
          sudo ip link add quagga-tap type veth peer name ovs-quagga-tap
          sudo ip link set dev ovs-quagga-tap up
          sudo ip link set dev quagga-tap up
          sudo ovs-vsctl add-port br-ex ovs-quagga-tap
          sudo brctl addif {bridge} quagga-tap
        fi
        """
        compute_node.run_cmd(cmd.format(bridge=bridge))

    compute_node.run_cmd("sudo virsh attach-interface %s"
                         " bridge %s" % (libvirt_instance_name, bridge))


def detach_instance_from_ext_br(instance, compute_node):
    libvirt_instance_name = getattr(instance, "OS-EXT-SRV-ATTR:instance_name")
    mac = compute_node.run_cmd("for vm in $(sudo virsh list | "
                               "grep running | awk '{print $2}'); "
                               "do echo -n ; sudo virsh dumpxml $vm| "
                               "grep -oP '52:54:[\da-f:]+' ;done")
    compute_node.run_cmd("sudo virsh detach-interface --domain %s"
                         " --type bridge --mac %s"
                         % (libvirt_instance_name, mac))

    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    if installer_type == "fuel":
        bridge = "br-ex"
    elif installer_type == "apex":
        # In Apex, br-ex is an ovs bridge and virsh attach-interface
        # won't just work. We work around it by creating a linux
        # bridge, attaching that to br-ex with a veth pair
        # and virsh-attaching the instance to the linux-bridge
        bridge = "br-quagga"
        cmd = """
            sudo brctl delif {bridge} quagga-tap &&
            sudo ovs-vsctl del-port br-ex ovs-quagga-tap &&
            sudo ip link set dev quagga-tap down &&
            sudo ip link set dev ovs-quagga-tap down &&
            sudo ip link del quagga-tap type veth peer name ovs-quagga-tap &&
            sudo ip link set {bridge} down &&
            sudo brctl delbr {bridge}
        """
        compute_node.run_cmd(cmd.format(bridge=bridge))


def cleanup_neutron(neutron_client, bgpvpn_ids, interfaces, subnet_ids,
                    router_ids, network_ids):

    if len(bgpvpn_ids) != 0:
        for bgpvpn_id in bgpvpn_ids:
            os_utils.delete_bgpvpn(neutron_client, bgpvpn_id)

    if len(interfaces) != 0:
        for router_id, subnet_id in interfaces:
            if not os_utils.remove_interface_router(neutron_client,
                                                    router_id, subnet_id):
                logging.error('Fail to delete all interface routers. '
                              'Interface router with id {} was not deleted.'.
                              format(router_id))

    if len(router_ids) != 0:
        for router_id in router_ids:
            if not os_utils.remove_gateway_router(neutron_client, router_id):
                logging.error('Fail to delete all gateway routers. '
                              'Gateway router with id {} was not deleted.'.
                              format(router_id))

    if len(subnet_ids) != 0:
        for subnet_id in subnet_ids:
            if not os_utils.delete_neutron_subnet(neutron_client, subnet_id):
                logging.error('Fail to delete all subnets. '
                              'Subnet with id {} was not deleted.'.
                              format(subnet_id))
                return False

    if len(router_ids) != 0:
        for router_id in router_ids:
            if not os_utils.delete_neutron_router(neutron_client, router_id):
                logging.error('Fail to delete all routers. '
                              'Router with id {} was not deleted.'.
                              format(router_id))
                return False

    if len(network_ids) != 0:
        for network_id in network_ids:
            if not os_utils.delete_neutron_net(neutron_client, network_id):
                logging.error('Fail to delete all networks. '
                              'Network with id {} was not deleted.'.
                              format(network_id))
                return False
    return True


def cleanup_nova(nova_client, floatingip_ids, instance_ids, image_ids):

    if len(floatingip_ids) != 0:
        for floatingip_id in floatingip_ids:
            if not os_utils.delete_floating_ip(nova_client, floatingip_id):
                logging.error('Fail to delete all floating ips. '
                              'Floating ip with id {} was not deleted.'.
                              format(floatingip_id))
                return False

    if len(instance_ids) != 0:
        for instance_id in instance_ids:
            if not os_utils.delete_instance(nova_client, instance_id):
                logging.error('Fail to delete all instances. '
                              'Instance with id {} was not deleted.'.
                              format(instance_id))
                return False

    if len(image_ids) != 0:
        for image_id in image_ids:
            if not os_utils.delete_glance_image(nova_client, image_id):
                logging.error('Fail to delete all images. '
                              'Image with id {} was not deleted.'.
                              format(image_id))
                return False
    return True


def check_exchange_bgp_routes():
    return ("#!/bin/sh\n"
            "BGP_NEIGHBORS=$(sudo vtysh -c 'show ip bgp neighbor')\n"
            "PREFIXES=$(echo \"$BGP_NEIGHBORS\" | grep 'accepted prefixes')\n"
            "ACCEPTED_ROUTES=$(echo \"$PREFIXES\" | awk '{print $1}')\n"
            "status='KO'\n"
            "for i in $ACCEPTED_ROUTES; do\n"
            "  if [ $i -gt '0' ]; then\n"
            "    status='OK'\n"
            "    break\n"
            "  fi\n"
            "done\n"
            "echo 'Routes: $status'\n")
