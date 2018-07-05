#!/usr/bin/env python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

import logging
import sys

from random import randint
from sdnvpn.lib import quagga
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import openstack_utils as os_utils
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib.results import Results

logger = logging.getLogger(__name__)

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.testcase_14')

(floatingip_ids, instance_ids, router_ids, network_ids, image_ids,
 subnet_ids, interfaces, bgpvpn_ids, flavor_ids) = ([] for i in range(9))

nova_client = os_utils.get_nova_client()
neutron_client = os_utils.get_neutron_client()
glance_client = os_utils.get_glance_client()


def main():
    results = Results(COMMON_CONFIG.line_length)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    try:

        image_id = os_utils.create_glance_image(
            glance_client, TESTCASE_CONFIG.image_name,
            COMMON_CONFIG.image_path, disk=COMMON_CONFIG.image_format,
            container="bare", public='public')
        image_ids.append(image_id)

        network_1_id, subnet_1_id, router_1_id = test_utils.create_network(
            neutron_client,
            TESTCASE_CONFIG.net_1_name,
            TESTCASE_CONFIG.subnet_1_name,
            TESTCASE_CONFIG.subnet_1_cidr,
            TESTCASE_CONFIG.router_1_name)

        interfaces.append(tuple((router_1_id, subnet_1_id)))
        network_ids.extend([network_1_id])
        subnet_ids.extend([subnet_1_id])
        router_ids.extend([router_1_id])

        sg_id = os_utils.create_security_group_full(
            neutron_client, TESTCASE_CONFIG.secgroup_name,
            TESTCASE_CONFIG.secgroup_descr)

        compute_nodes = test_utils.assert_and_get_compute_nodes(nova_client)

        av_zone_1 = "nova:" + compute_nodes[0]

        # boot INTANCES
        vm_1 = test_utils.create_instance(
            nova_client,
            TESTCASE_CONFIG.instance_1_name,
            image_id,
            network_1_id,
            sg_id,
            secgroup_name=TESTCASE_CONFIG.secgroup_name,
            compute_node=av_zone_1)
        instance_ids.append(vm_1.id)
        instance_dhcp_up = test_utils.wait_for_instances_get_dhcp(vm_1)
        if (not instance_dhcp_up):
            logger.error("vm_1 instance is down")

        msg = ("Create VPN with multiple RDs")
        results.record_action(msg)
        vpn_name = "sdnvpn-" + str(randint(100000, 999999))
        kwargs = {
            "import_targets": TESTCASE_CONFIG.targets1,
            "export_targets": TESTCASE_CONFIG.targets2,
            "route_distinguishers": TESTCASE_CONFIG.route_distinguishers,
            "name": vpn_name
        }
        bgpvpn = test_utils.create_bgpvpn(neutron_client, **kwargs)
        bgpvpn_id = bgpvpn['bgpvpn']['id']
        logger.debug("VPN created details: %s" % bgpvpn)
        bgpvpn_ids.append(bgpvpn_id)

        msg = ("Associate network '%s' to the VPN." %
               TESTCASE_CONFIG.net_1_name)
        results.record_action(msg)
        results.add_to_summary(0, "-")

        test_utils.create_network_association(
            neutron_client, bgpvpn_id, network_1_id)

        configure_zrpcd_for_odl()
        configure_bgp_neighbors()
        # TODO: Add code for external tunnel creation, validating route
        # exchange and group/flow validation and cleanup

    except Exception as e:
        logger.error("exception occurred while executing testcase_14: %s", e)
        raise
    finally:
        test_utils.cleanup_nova(nova_client, instance_ids)
        test_utils.cleanup_glance(glance_client, image_ids)
        test_utils.cleanup_neutron(neutron_client, floatingip_ids,
                                   bgpvpn_ids, interfaces, subnet_ids,
                                   router_ids, network_ids)

    return results.compile_summary()


def configure_zrpcd_for_odl():
    controller = get_controller()
    add_client_conn_to_bgp = "bgp-connect -p 7644 -h 127.0.0.1 add"
    test_utils.run_odl_cmd(controller, add_client_conn_to_bgp)
    # Start bgp daemon
    start_quagga = "odl:configure-bgp -op start-bgp-server " \
                   "--as-num 100 --router-id {0}".format(
                       get_controller_ext_ip(controller))
    test_utils.run_odl_cmd(controller, start_quagga)


def configure_bgp_neighbors():
    _, flavor_id = test_utils.create_custom_flavor()
    flavor_ids.append(flavor_id)

    quagga_net_id, subnet_quagga_id, router_quagga_id \
        = test_utils.create_network(neutron_client,
                                    TESTCASE_CONFIG.quagga_net_name,
                                    TESTCASE_CONFIG.quagga_subnet_name,
                                    TESTCASE_CONFIG.quagga_subnet_cidr,
                                    TESTCASE_CONFIG.quagga_router_name)
    interfaces.append(tuple((router_quagga_id, subnet_quagga_id)))
    network_ids.append(quagga_net_id)
    router_ids.append(router_quagga_id)
    subnet_ids.append(subnet_quagga_id)

    controller = get_controller()
    controller_ext_ip = get_controller_ext_ip(controller)
    ext_net_mask = get_controller_net_mask(controller)

    fake_fip_1 = os_utils.create_floating_ip(neutron_client)
    floatingip_ids.append(fake_fip_1['fip_id'])
    fake_fip_2 = os_utils.create_floating_ip(neutron_client)
    floatingip_ids.append(fake_fip_2['fip_id'])

    ubuntu_image_id = os_utils.create_glance_image(
        glance_client,
        COMMON_CONFIG.ubuntu_image_name,
        COMMON_CONFIG.ubuntu_image_path,
        'qcow2',
        container="bare",
        public="public")
    image_ids.append(ubuntu_image_id)

    sg_id = os_utils.create_security_group_full(
        neutron_client, TESTCASE_CONFIG.secgroup_name,
        TESTCASE_CONFIG.secgroup_descr)

    bootup_quagga(quagga_net_id, ubuntu_image_id, sg_id,
                  fake_fip_1['fip_addr'],
                  TESTCASE_CONFIG.quagga_instance_name_1,
                  controller_ext_ip, ext_net_mask,
                  nova_client.hypervisors.list()[0],
                  TESTCASE_CONFIG.external_ip_label_dcgw_1)
    bootup_quagga(quagga_net_id, ubuntu_image_id, sg_id,
                  fake_fip_2['fip_addr'],
                  TESTCASE_CONFIG.quagga_instance_name_2,
                  controller_ext_ip, ext_net_mask,
                  nova_client.hypervisors.list()[0],
                  TESTCASE_CONFIG.external_ip_label_dcgw_2)

    quagga.odl_add_neighbor(fake_fip_1['fip_addr'],
                            controller_ext_ip,
                            controller)
    quagga.odl_add_neighbor(fake_fip_2['fip_addr'],
                            controller_ext_ip,
                            controller)
    peers = quagga.check_for_peering(controller)
    if not peers:
        logger.error("BGP peer is not established")
    return [fake_fip_1['fip_addr'], fake_fip_2['fip_addr']]


def bootup_quagga(quagga_net_id, image_id, sg_id, instance_ip, instance_name,
                  controller_ext_ip, net_mask, compute, label):
    quagga_bootstrap_script = quagga.gen_quagga_setup_script(
        controller_ext_ip,
        instance_ip,
        net_mask,
        TESTCASE_CONFIG.external_network_ip_prefix,
        label,
        TESTCASE_CONFIG.route_distinguishers,
        TESTCASE_CONFIG.import_targets,
        TESTCASE_CONFIG.export_targets)
    quagga_vm = test_utils.create_instance(
        nova_client,
        instance_name,
        image_id,
        quagga_net_id,
        sg_id,
        flavor=COMMON_CONFIG.custom_flavor_name,
        userdata=quagga_bootstrap_script,
        compute_node=compute)
    instance_ids.append(quagga_vm.id)
    quagga_vm_port = test_utils.get_port(neutron_client,
                                         quagga_vm.id)
    fip_added = os_utils.attach_floating_ip(neutron_client,
                                            quagga_vm_port['id'])
    floatingip_ids.append(fip_added['floatingip']['id'])
    test_utils.attach_instance_to_ext_br(quagga_vm, compute)
    cloud_init_success = test_utils.wait_for_cloud_init(quagga_vm)
    if cloud_init_success:
        logger.info("quagga vm %s is booted successfully" % quagga_vm)
    else:
        logger.error("quagga vm %s is failed to boot" % quagga_vm)


def get_controller_ext_ip(controller):
    get_ext_ip_cmd = "sudo ip a | grep br-ex | grep inet | awk '{print $2}'"
    ext_net_cidr = controller.run_cmd(get_ext_ip_cmd).strip().split('\n')
    return ext_net_cidr[0].split('/')[0]


def get_controller_net_mask(controller):
    get_ext_ip_cmd = "sudo ip a | grep br-ex | grep inet | awk '{print $2}'"
    ext_net_cidr = controller.run_cmd(get_ext_ip_cmd).strip().split('\n')
    return ext_net_cidr[0].split('/')[1]


def get_controller():
    openstack_nodes = test_utils.get_nodes()
    controllers = [node for node in openstack_nodes
                   if "running" in
                   node.run_cmd("sudo systemctl status opendaylight")]
    return test_utils.get_odl_bgp_entity_owner(controllers)


if __name__ == '__main__':
    sys.exit(main())
