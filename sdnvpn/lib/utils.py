#!/usr/bin/env python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
import json
import logging
import os
import time
import requests
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from openstack.exceptions import ResourceNotFound
from requests.auth import HTTPBasicAuth

from opnfv.deployment.factory import Factory as DeploymentFactory

from sdnvpn.lib import config as sdnvpn_config
import sdnvpn.lib.openstack_utils as os_utils

logger = logging.getLogger('sdnvpn_test_utils')

common_config = sdnvpn_config.CommonConfig()

ODL_USER = 'admin'
ODL_PASS = 'admin'

executor = ThreadPoolExecutor(5)


class ExtraRoute(object):
    """
    Class to represent extra route for a router
    """

    def __init__(self, destination, nexthop):
        self.destination = destination
        self.nexthop = nexthop


class AllowedAddressPair(object):
    """
    Class to represent allowed address pair for a neutron port
    """

    def __init__(self, ipaddress, macaddress):
        self.ipaddress = ipaddress
        self.macaddress = macaddress


def create_default_flavor():
    return os_utils.get_or_create_flavor(common_config.default_flavor,
                                         common_config.default_flavor_ram,
                                         common_config.default_flavor_disk,
                                         common_config.default_flavor_vcpus)


def create_custom_flavor():
    return os_utils.get_or_create_flavor(common_config.custom_flavor_name,
                                         common_config.custom_flavor_ram,
                                         common_config.custom_flavor_disk,
                                         common_config.custom_flavor_vcpus)


def create_net(conn, name):
    logger.debug("Creating network %s", name)
    net_id = os_utils.create_neutron_net(conn, name)
    if not net_id:
        logger.error(
            "There has been a problem when creating the neutron network")
        raise Exception("There has been a problem when creating"
                        " the neutron network {}".format(name))
    return net_id


def create_subnet(conn, name, cidr, net_id):
    logger.debug("Creating subnet %s in network %s with cidr %s",
                 name, net_id, cidr)
    subnet_id = os_utils.create_neutron_subnet(conn,
                                               name,
                                               cidr,
                                               net_id)
    if not subnet_id:
        logger.error(
            "There has been a problem when creating the neutron subnet")
        raise Exception("There has been a problem when creating"
                        " the neutron subnet {}".format(name))
    return subnet_id


def create_network(conn, net, subnet1, cidr1,
                   router, subnet2=None, cidr2=None):
    """Network assoc won't work for networks/subnets created by this function.
    It is an ODL limitation due to it handling routers as vpns.
    See https://bugs.opendaylight.org/show_bug.cgi?id=6962"""
    network_dic = os_utils.create_network_full(conn,
                                               net,
                                               subnet1,
                                               router,
                                               cidr1)
    if not network_dic:
        logger.error(
            "There has been a problem when creating the neutron network")
        raise Exception("There has been a problem when creating"
                        " the neutron network {}".format(net))
    net_id = network_dic["net_id"]
    subnet_id = network_dic["subnet_id"]
    router_id = network_dic["router_id"]

    if subnet2 is not None:
        logger.debug("Creating and attaching a second subnet...")
        subnet_id = os_utils.create_neutron_subnet(
            conn, subnet2, cidr2, net_id)
        if not subnet_id:
            logger.error(
                "There has been a problem when creating the second subnet")
            raise Exception("There has been a problem when creating"
                            " the second subnet {}".format(subnet2))
        logger.debug("Subnet '%s' created successfully" % subnet_id)
    return net_id, subnet_id, router_id


def get_port(conn, instance_id):
    ports = os_utils.get_port_list(conn)
    for port in ports:
        if port.device_id == instance_id:
            return port
    return None


def update_port_allowed_address_pairs(conn, port_id, address_pairs):
    if len(address_pairs) <= 0:
        return
    allowed_address_pairs = []
    for address_pair in address_pairs:
        address_pair_dict = {'ip_address': address_pair.ipaddress,
                             'mac_address': address_pair.macaddress}
        allowed_address_pairs.append(address_pair_dict)

    try:
        port = conn.network.\
            update_port(port_id, allowed_address_pairs=allowed_address_pairs)
        return port.id
    except Exception as e:
        logger.error("Error [update_neutron_port(network, '%s', '%s')]:"
                     " %s" % (port_id, address_pairs, e))
        return None


def create_instance(conn,
                    name,
                    image_id,
                    network_id,
                    sg_id,
                    secgroup_name=None,
                    fixed_ip=None,
                    compute_node=None,
                    userdata=None,
                    files=[],
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
        raise Exception("Error while booting instance {}".format(name))
    else:
        # Retrieve IP of INSTANCE
        network_name = conn.network.get_network(network_id).name
        instance_ip = conn.compute.get_server(instance).\
            addresses.get(network_name)[0]['addr']
        logger.debug("Instance '%s' booted successfully. IP='%s'." %
                     (name, instance_ip))

    if secgroup_name:
        logger.debug("Adding '%s' to security group '%s'..."
                     % (name, secgroup_name))
    else:
        logger.debug("Adding '%s' to security group '%s'..."
                     % (name, sg_id))
    os_utils.add_secgroup_to_instance(conn, instance.id, sg_id)

    return instance


def generate_ping_userdata(ips_array, ping_count=10):
    ips = ""
    for ip in ips_array:
        ips = ("%s %s" % (ips, ip))

    ips = ips.replace('  ', ' ')
    return ("#!/bin/sh\n"
            "set%s\n"
            "while true; do\n"
            " for i do\n"
            "  ip=$i\n"
            "  ping -c %s $ip 2>&1 >/dev/null\n"
            "  RES=$?\n"
            "  if [ \"Z$RES\" = \"Z0\" ] ; then\n"
            "   echo ping $ip OK\n"
            "  else echo ping $ip KO\n"
            "  fi\n"
            " done\n"
            " sleep 1\n"
            "done\n"
            % (ips, ping_count))


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


def generate_userdata_interface_create(interface_name, interface_number,
                                       ip_Address, net_mask):
    return ("#!/bin/sh\n"
            "set -xe\n"
            "sudo useradd -m sdnvpn\n"
            "sudo adduser sdnvpn sudo\n"
            "sudo echo sdnvpn:opnfv | chpasswd\n"
            "sleep 20\n"
            "sudo ifconfig %s:%s %s netmask %s up\n"
            % (interface_name, interface_number,
               ip_Address, net_mask))


def get_installerHandler():
    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    installer_ip = get_installer_ip()

    if installer_type not in ["fuel", "apex"]:
        logger.warn("installer type %s is neither fuel nor apex."
                    "returning None for installer handler" % installer_type)
        return None
    else:
        if installer_type in ["apex"]:
            installer_user = "root"
        elif installer_type in ["fuel"]:
            installer_user = "ubuntu"

        developHandler = DeploymentFactory.get_handler(
            installer_type,
            installer_ip,
            installer_user,
            pkey_file="/root/.ssh/id_rsa")

        return developHandler


def get_nodes():
    developHandler = get_installerHandler()
    return developHandler.get_nodes()


def get_installer_ip():
    return str(os.environ['INSTALLER_IP'])


def get_instance_ip(conn, instance):
    instance_ip = conn.compute.get_server(instance).\
        addresses.values()[0][0]['addr']
    return instance_ip


def wait_for_instance(instance, pattern=".* login:", tries=40):
    logger.info("Waiting for instance %s to boot up" % instance.id)
    conn = os_utils.get_os_connection()
    sleep_time = 2
    expected_regex = re.compile(pattern)
    console_log = ""
    while tries > 0 and not expected_regex.search(console_log):
        console_log = conn.compute.\
            get_server_console_output(instance)['output']
        time.sleep(sleep_time)
        tries -= 1

    if not expected_regex.search(console_log):
        logger.error("Instance %s does not boot up properly."
                     % instance.id)
        return False
    return True


def wait_for_instances_up(*instances):
    check = [wait_for_instance(instance) for instance in instances]
    return all(check)


def wait_for_instances_get_dhcp(*instances):
    check = [wait_for_instance(instance, "Lease of .* obtained")
             for instance in instances]
    return all(check)


def async_Wait_for_instances(instances, tries=40):
    if len(instances) <= 0:
        return
    futures = []
    for instance in instances:
        future = executor.submit(wait_for_instance,
                                 instance,
                                 ".* login:",
                                 tries)
        futures.append(future)
    results = []
    for future in futures:
        results.append(future.result())
    if False in results:
        logger.error("one or more instances is not yet booted up")


def wait_for_instance_delete(conn, instance_id, tries=30):
    sleep_time = 2
    instances = [instance_id]
    logger.debug("Waiting for instance %s to be deleted"
                 % (instance_id))
    while tries > 0 and instance_id in instances:
        instances = [instance.id for instance in
                     os_utils.get_instances(conn)]
        time.sleep(sleep_time)
        tries -= 1
    if instance_id in instances:
        logger.error("Deletion of instance %s failed" %
                     (instance_id))


def wait_for_bgp_net_assoc(neutron_client, bgpvpn_id, net_id):
    tries = 30
    sleep_time = 1
    nets = []
    logger.debug("Waiting for network %s to associate with BGPVPN %s "
                 % (bgpvpn_id, net_id))

    while tries > 0 and net_id not in nets:
        nets = get_bgpvpn_networks(neutron_client, bgpvpn_id)
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
        routers = get_bgpvpn_routers(neutron_client, bgpvpn_id)
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


def assert_and_get_compute_nodes(conn, required_node_number=2):
    """Get the compute nodes in the deployment
    Exit if the deployment doesn't have enough compute nodes"""
    compute_nodes = os_utils.get_hypervisors(conn)

    num_compute_nodes = len(compute_nodes)
    if num_compute_nodes < 2:
        logger.error("There are %s compute nodes in the deployment. "
                     "Minimum number of nodes to complete the test is 2."
                     % num_compute_nodes)
        raise Exception("There are {} compute nodes in the deployment. "
                        "Minimum number of nodes to complete the test"
                        " is 2.".format(num_compute_nodes))

    logger.debug("Compute nodes: %s" % compute_nodes)
    return compute_nodes


def open_icmp(conn, security_group_id):
    if os_utils.check_security_group_rules(conn,
                                           security_group_id,
                                           'ingress',
                                           'icmp'):

        if not os_utils.create_secgroup_rule(conn,
                                             security_group_id,
                                             'ingress',
                                             'icmp'):
            logger.error("Failed to create icmp security group rule...")
    else:
        logger.info("This rule exists for security group: %s"
                    % security_group_id)


def open_http_port(conn, security_group_id):
    if os_utils.check_security_group_rules(conn,
                                           security_group_id,
                                           'ingress',
                                           'tcp',
                                           80, 80):

        if not os_utils.create_secgroup_rule(conn,
                                             security_group_id,
                                             'ingress',
                                             'tcp',
                                             80, 80):

            logger.error("Failed to create http security group rule...")
    else:
        logger.info("This rule exists for security group: %s"
                    % security_group_id)


def open_bgp_port(conn, security_group_id):
    if os_utils.check_security_group_rules(conn,
                                           security_group_id,
                                           'ingress',
                                           'tcp',
                                           179, 179):

        if not os_utils.create_secgroup_rule(conn,
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


def check_odl_fib(ip, odl_ip):
    """Check that there is an entry in the ODL Fib for `ip`"""
    url = "http://" + odl_ip + \
          ":8181/restconf/config/odl-fib:fibEntries/"
    logger.debug("Querring '%s' for FIB entries", url)
    res = requests.get(url, auth=(ODL_USER, ODL_PASS))
    if res.status_code != 200:
        logger.error("OpenDaylight response status code: %s", res.status_code)
        return False
    logger.debug("Checking whether '%s' is in the OpenDaylight FIB"
                 % odl_ip)
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


def wait_for_cloud_init(conn, instance):
    success = True
    # ubuntu images take a long time to start
    tries = 20
    sleep_time = 30
    logger.info("Waiting for cloud init of instance: {}"
                "".format(instance.name))
    while tries > 0:
        instance_log = conn.compute.\
            get_server_console_output(instance)['output']
        if "Failed to run module" in instance_log:
            success = False
            logger.error("Cloud init failed to run. Reason: %s",
                         instance_log)
            break
        if re.search(r"Cloud-init v. .+ finished at", instance_log):
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
    libvirt_instance_name = instance.instance_name
    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    # In Apex, br-ex (or br-floating for Fuel) is an ovs bridge and virsh
    # attach-interface won't just work. We work around it by creating a linux
    # bridge, attaching that to br-ex (or br-floating for Fuel) with a
    # veth pair and virsh-attaching the instance to the linux-bridge
    if installer_type in ["fuel"]:
        bridge = "br-floating"
    elif installer_type in ["apex"]:
        bridge = "br-ex"
    else:
        logger.warn("installer type %s is neither fuel nor apex."
                    % installer_type)
        return

    cmd = """
    set -e
    if ! sudo brctl show |grep -q ^br-quagga;then
      sudo brctl addbr br-quagga
      sudo ip link set br-quagga up
      sudo ip link add quagga-tap type veth peer name ovs-quagga-tap
      sudo ip link set dev ovs-quagga-tap up
      sudo ip link set dev quagga-tap up
      sudo ovs-vsctl add-port {bridge} ovs-quagga-tap
      sudo brctl addif br-quagga quagga-tap
    fi
    """
    compute_node.run_cmd(cmd.format(bridge=bridge))

    compute_node.run_cmd("sudo virsh attach-interface %s"
                         " bridge br-quagga" % (libvirt_instance_name))


def detach_instance_from_ext_br(instance, compute_node):
    libvirt_instance_name = instance.instance_name
    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    # This function undoes all the actions performed by
    # attach_instance_to_ext_br on Fuel and Apex installers.
    if installer_type in ["fuel"]:
        bridge = "br-floating"
    elif installer_type in ["apex"]:
        bridge = "br-ex"
    else:
        logger.warn("installer type %s is neither fuel nor apex."
                    % installer_type)
        return
    mac = compute_node.run_cmd("for vm in $(sudo virsh list | "
                               "grep running | awk '{print $2}'); "
                               "do echo -n ; sudo virsh dumpxml $vm| "
                               "grep -oP '52:54:[\da-f:]+' ;done")
    compute_node.run_cmd("sudo virsh detach-interface --domain %s"
                         " --type bridge --mac %s"
                         % (libvirt_instance_name, mac))

    cmd = """
        sudo brctl delif br-quagga quagga-tap &&
        sudo ovs-vsctl del-port {bridge} ovs-quagga-tap &&
        sudo ip link set dev quagga-tap down &&
        sudo ip link set dev ovs-quagga-tap down &&
        sudo ip link del quagga-tap type veth peer name ovs-quagga-tap &&
        sudo ip link set br-quagga down &&
        sudo brctl delbr br-quagga
    """
    compute_node.run_cmd(cmd.format(bridge=bridge))


def cleanup_neutron(conn, neutron_client, floatingip_ids, bgpvpn_ids,
                    interfaces, subnet_ids, router_ids, network_ids):
    if len(floatingip_ids) != 0:
        for floatingip_id in floatingip_ids:
            if not os_utils.delete_floating_ip(conn, floatingip_id):
                logger.error('Fail to delete all floating ips. '
                             'Floating ip with id {} was not deleted.'.
                             format(floatingip_id))
                return False

    if len(bgpvpn_ids) != 0:
        for bgpvpn_id in bgpvpn_ids:
            delete_bgpvpn(neutron_client, bgpvpn_id)

    if len(interfaces) != 0:
        for router_id, subnet_id in interfaces:
            if not os_utils.remove_interface_router(conn,
                                                    router_id, subnet_id):
                logger.error('Fail to delete all interface routers. '
                             'Interface router with id {} was not deleted.'.
                             format(router_id))

    if len(router_ids) != 0:
        for router_id in router_ids:
            if not os_utils.remove_gateway_router(conn, router_id):
                logger.error('Fail to delete all gateway routers. '
                             'Gateway router with id {} was not deleted.'.
                             format(router_id))

    if len(subnet_ids) != 0:
        for subnet_id in subnet_ids:
            if not os_utils.delete_neutron_subnet(conn, subnet_id):
                logger.error('Fail to delete all subnets. '
                             'Subnet with id {} was not deleted.'.
                             format(subnet_id))
                return False

    if len(router_ids) != 0:
        for router_id in router_ids:
            if not os_utils.delete_neutron_router(conn, router_id):
                logger.error('Fail to delete all routers. '
                             'Router with id {} was not deleted.'.
                             format(router_id))
                return False

    if len(network_ids) != 0:
        for network_id in network_ids:
            if not os_utils.delete_neutron_net(conn, network_id):
                logger.error('Fail to delete all networks. '
                             'Network with id {} was not deleted.'.
                             format(network_id))
                return False
    return True


def cleanup_nova(conn, instance_ids, flavor_ids=None):
    if flavor_ids is not None and len(flavor_ids) != 0:
        for flavor_id in flavor_ids:
            conn.compute.delete_flavor(flavor_id)
    if len(instance_ids) != 0:
        for instance_id in instance_ids:
            if not os_utils.delete_instance(conn, instance_id):
                logger.error('Fail to delete all instances. '
                             'Instance with id {} was not deleted.'.
                             format(instance_id))
            else:
                wait_for_instance_delete(conn, instance_id)
    return True


def cleanup_glance(conn, image_ids):
    if len(image_ids) != 0:
        for image_id in image_ids:
            if not os_utils.delete_glance_image(conn, image_id):
                logger.error('Fail to delete all images. '
                             'Image with id {} was not deleted.'.
                             format(image_id))
                return False
    return True


def create_bgpvpn(neutron_client, **kwargs):
    # route_distinguishers
    # route_targets
    json_body = {"bgpvpn": kwargs}
    return neutron_client.create_bgpvpn(json_body)


def update_bgpvpn(neutron_client, bgpvpn_id, **kwargs):
    json_body = {"bgpvpn": kwargs}
    return neutron_client.update_bgpvpn(bgpvpn_id, json_body)


def delete_bgpvpn(neutron_client, bgpvpn_id):
    return neutron_client.delete_bgpvpn(bgpvpn_id)


def get_bgpvpn(neutron_client, bgpvpn_id):
    return neutron_client.show_bgpvpn(bgpvpn_id)


def get_bgpvpn_routers(neutron_client, bgpvpn_id):
    return get_bgpvpn(neutron_client, bgpvpn_id)['bgpvpn']['routers']


def get_bgpvpn_networks(neutron_client, bgpvpn_id):
    return get_bgpvpn(neutron_client, bgpvpn_id)['bgpvpn']['networks']


def create_router_association(neutron_client, bgpvpn_id, router_id):
    json_body = {"router_association": {"router_id": router_id}}
    return neutron_client.create_router_association(bgpvpn_id, json_body)


def create_network_association(neutron_client, bgpvpn_id, neutron_network_id):
    json_body = {"network_association": {"network_id": neutron_network_id}}
    return neutron_client.create_network_association(bgpvpn_id, json_body)


def is_fail_mode_secure():
    """
    Checks the value of the attribute fail_mode,
    if it is set to secure. This check is performed
    on all OVS br-int interfaces, for all OpenStack nodes.
    """
    is_secure = {}
    openstack_nodes = get_nodes()
    get_ovs_int_cmd = ("sudo ovs-vsctl show | "
                       "grep -i bridge | "
                       "awk '{print $2}'")
    # Define OVS get fail_mode command
    get_ovs_fail_mode_cmd = ("sudo ovs-vsctl get-fail-mode br-int")
    for openstack_node in openstack_nodes:
        if not openstack_node.is_active():
            continue

        installer_type = str(os.environ['INSTALLER_TYPE'].lower())
        if installer_type in ['fuel']:
            if (
                'controller' in openstack_node.roles or
                'opendaylight' in openstack_node.roles
            ):
                continue

        ovs_int_list = (openstack_node.run_cmd(get_ovs_int_cmd).
                        strip().split('\n'))
        if 'br-int' in ovs_int_list:
            # Execute get fail_mode command
            br_int_fail_mode = (openstack_node.
                                run_cmd(get_ovs_fail_mode_cmd).strip())
            if br_int_fail_mode == 'secure':
                # success
                is_secure[openstack_node.name] = True
            else:
                # failure
                logger.error('The fail_mode for br-int was not secure '
                             'in {} node'.format(openstack_node.name))
                is_secure[openstack_node.name] = False
    return is_secure


def update_nw_subnet_port_quota(conn, tenant_id, nw_quota,
                                subnet_quota, port_quota, router_quota):
    try:
        conn.network.update_quota(tenant_id, networks=nw_quota,
                                  subnets=subnet_quota, ports=port_quota,
                                  routers=router_quota)
        return True
    except Exception as e:
        logger.error("Error [update_nw_subnet_port_quota(network,"
                     " '%s', '%s', '%s', '%s, %s')]: %s" %
                     (tenant_id, nw_quota, subnet_quota,
                      port_quota, router_quota, e))
        return False


def update_instance_quota_class(cloud, instances_quota):
    try:
        cloud.set_compute_quotas('admin', instances=instances_quota)
        return True
    except Exception as e:
        logger.error("Error [update_instance_quota_class(compute,"
                     " '%s' )]: %s" % (instances_quota, e))
        return False


def get_neutron_quota(conn, tenant_id):
    try:
        return conn.network.get_quota(tenant_id)
    except ResourceNotFound as e:
        logger.error("Error in getting network quota for tenant "
                     " '%s' )]: %s" % (tenant_id, e))
        raise


def get_nova_instances_quota(cloud):
    try:
        return cloud.get_compute_quotas('admin').instances
    except Exception as e:
        logger.error("Error in getting nova instances quota: %s" % e)
        raise


def update_router_extra_route(conn, router_id, extra_routes):
    if len(extra_routes) <= 0:
        return
    routes_list = []
    for extra_route in extra_routes:
        route_dict = {'destination': extra_route.destination,
                      'nexthop': extra_route.nexthop}
        routes_list.append(route_dict)

    try:
        conn.network.update_router(router_id, routes=routes_list)
        return True
    except Exception as e:
        logger.error("Error in updating router with extra route: %s" % e)
        raise


def update_router_no_extra_route(conn, router_ids):
    for router_id in router_ids:
        try:
            conn.network.update_router(router_id, routes=[])
            return True
        except Exception as e:
            logger.error("Error in clearing extra route: %s" % e)


def get_ovs_groups(compute_node_list, ovs_br_list, of_protocol="OpenFlow13"):
    """
    Gets, as input, a list of compute nodes and a list of OVS bridges
    and returns the command console output, as a list of lines, that
    contains all the OVS groups from all bridges and nodes in lists.
    """
    cmd_out_lines = []
    for compute_node in compute_node_list:
        for ovs_br in ovs_br_list:
            if ovs_br in compute_node.run_cmd("sudo ovs-vsctl show"):
                ovs_groups_cmd = ("sudo ovs-ofctl dump-groups {} -O {} | "
                                  "grep group".format(ovs_br, of_protocol))
                cmd_out_lines += (compute_node.run_cmd(ovs_groups_cmd).strip().
                                  split("\n"))
    return cmd_out_lines


def get_ovs_flows(compute_node_list, ovs_br_list, of_protocol="OpenFlow13"):
    """
    Gets, as input, a list of compute nodes and a list of OVS bridges
    and returns the command console output, as a list of lines, that
    contains all the OVS flows from all bridges and nodes in lists.
    """
    cmd_out_lines = []
    for compute_node in compute_node_list:
        for ovs_br in ovs_br_list:
            if ovs_br in compute_node.run_cmd("sudo ovs-vsctl show"):
                ovs_flows_cmd = ("sudo ovs-ofctl dump-flows {} -O {} | "
                                 "grep table=".format(ovs_br, of_protocol))
                cmd_out_lines += (compute_node.run_cmd(ovs_flows_cmd).strip().
                                  split("\n"))
    return cmd_out_lines


def get_node_ip_and_netmask(node, iface):
    cmd = "ip a | grep {iface} | grep inet | awk '{print $2}'"\
          .format(iface=iface)
    mgmt_net_cidr = node.run_cmd(cmd).strip().split('\n')
    mgmt_ip = mgmt_net_cidr[0].split('/')[0]
    mgmt_netmask = mgmt_net_cidr[0].split('/')[1]

    return mgmt_ip, mgmt_netmask


def get_odl_bgp_entity_owner(odl_nodes):
    """ Finds the ODL owner of the BGP entity in the cluster.

    When ODL runs in clustering mode we need to execute the BGP speaker
    related commands to that ODL which is the owner of the BGP entity.

    :param odl_nodes: list of Opendaylight nodes
    :return odl_node: Opendaylight node in which ODL BGP entity owner runs
    """
    if len(odl_nodes) == 1:
        return odl_nodes[0]
    else:
        installer_type = str(os.environ['INSTALLER_TYPE'].lower())
        if installer_type in ['fuel']:
            ip, _ = get_node_ip_and_netmask(odl_nodes[0], 'ens6')
            port = 8282
        else:
            ip = odl_nodes[0].ip
            port = 8081
        url = ('http://admin:admin@{ip}:{port}/restconf/'
               'operational/entity-owners:entity-owners/entity-type/bgp'
               .format(ip=ip, port=str(port)))

        remote_odl_akka_conf = ('/opt/opendaylight/configuration/'
                                'initial/akka.conf')
        remote_odl_home_akka_conf = '/home/heat-admin/akka.conf'
        local_tmp_akka_conf = '/tmp/akka.conf'
        try:
            json_output = requests.get(url).json()
        except Exception:
            logger.error('Failed to find the ODL BGP '
                         'entity owner through REST')
            return None
        odl_bgp_owner = json_output['entity-type'][0]['entity'][0]['owner']

        for odl_node in odl_nodes:

            odl_node.run_cmd('sudo cp {0} /home/heat-admin/'
                             .format(remote_odl_akka_conf))
            odl_node.run_cmd('sudo chmod 777 {0}'
                             .format(remote_odl_home_akka_conf))
            odl_node.get_file(remote_odl_home_akka_conf, local_tmp_akka_conf)

            for line in open(local_tmp_akka_conf):
                if re.search(odl_bgp_owner, line):
                    return odl_node
        return None


def add_quagga_external_gre_end_point(odl_nodes, remote_tep_ip):
    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    if installer_type in ['fuel']:
        ip, _ = get_node_ip_and_netmask(odl_nodes[0], 'ens6')
        port = 8282
    else:
        ip = odl_nodes[0].ip
        port = 8081
    json_body = {'input':
                 {'destination-ip': remote_tep_ip,
                  'tunnel-type': "odl-interface:tunnel-type-mpls-over-gre"}
                 }
    url = ('http://{ip}:{port}/restconf/operations/'
           'itm-rpc:add-external-tunnel-endpoint'.format(ip=ip,
                                                         port=str(port)))
    headers = {'Content-type': 'application/yang.data+json',
               'Accept': 'application/yang.data+json'}
    try:
        requests.post(url, data=json.dumps(json_body),
                      headers=headers,
                      auth=HTTPBasicAuth('admin', 'admin'))
    except Exception as e:
        logger.error("Failed to create external tunnel endpoint on"
                     " ODL for external tep ip %s with error %s"
                     % (remote_tep_ip, e))
    return None


def is_fib_entry_present_on_odl(odl_nodes, ip_prefix, vrf_id):
    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    if installer_type in ['fuel']:
        ip, _ = get_node_ip_and_netmask(odl_nodes[0], 'ens6')
        port = 8282
    else:
        ip = odl_nodes[0].ip
        port = 8081
    url = ('http://admin:admin@{ip}:{port}/restconf/config/odl-fib:fibEntries/'
           'vrfTables/{vrf}/'.format(ip=ip, port=str(port), vrf=vrf_id))
    logger.error("url is %s" % url)
    try:
        vrf_table = requests.get(url).json()
        is_ipprefix_exists = False
        for vrf_entry in vrf_table['vrfTables'][0]['vrfEntry']:
            if vrf_entry['destPrefix'] == ip_prefix:
                is_ipprefix_exists = True
                break
        return is_ipprefix_exists
    except Exception as e:
        logger.error('Failed to find ip prefix %s with error %s'
                     % (ip_prefix, e))
    return False
