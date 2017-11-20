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
import sys

from functest.utils import openstack_utils as os_utils
from random import randint
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib.results import Results

logger = logging.getLogger(__name__)

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.testcase_13')


def main():
    results = Results(COMMON_CONFIG.line_length)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()
    glance_client = os_utils.get_glance_client()

    (floatingip_ids, instance_ids, router_ids, network_ids, image_ids,
     subnet_ids, interfaces, bgpvpn_ids, flavor_ids) = ([] for i in range(9))

    try:
        image_id = os_utils.create_glance_image(
            glance_client,
            COMMON_CONFIG.ubuntu_image_name,
            COMMON_CONFIG.ubuntu_image_path,
            disk="qcow2",
            container="bare",
            public="public")
        image_ids.append(image_id)

        _, flavor_id = test_utils.create_custom_flavor()
        flavor_ids.append(flavor_id)

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
        av_zone_2 = "nova:" + compute_nodes[1]

        u1 = test_utils.generate_userdata_interface_create(
            TESTCASE_CONFIG.interface_name,
            TESTCASE_CONFIG.interface_number,
            TESTCASE_CONFIG.extra_route_ip,
            TESTCASE_CONFIG.extra_route_subnet_mask)
        # boot INTANCES
        vm_1 = test_utils.create_instance(
            nova_client,
            TESTCASE_CONFIG.instance_1_name,
            image_id,
            network_1_id,
            sg_id,
            flavor=COMMON_CONFIG.custom_flavor_name,
            secgroup_name=TESTCASE_CONFIG.secgroup_name,
            compute_node=av_zone_1,
            userdata=u1)
        vm_1_ip = test_utils.get_instance_ip(vm_1)

        vm1_port = test_utils.get_port(neutron_client, vm_1.id)
        test_utils.update_port_allowed_address_pairs(
            neutron_client,
            vm1_port['id'],
            [test_utils.AllowedAddressPair(
                TESTCASE_CONFIG.extra_route_cidr,
                vm1_port['mac_address'])])

        vm_2 = test_utils.create_instance(
            nova_client,
            TESTCASE_CONFIG.instance_2_name,
            image_id,
            network_1_id,
            sg_id,
            flavor=COMMON_CONFIG.custom_flavor_name,
            secgroup_name=TESTCASE_CONFIG.secgroup_name,
            compute_node=av_zone_1,
            userdata=u1)
        vm_2_ip = test_utils.get_instance_ip(vm_2)

        vm2_port = test_utils.get_port(neutron_client, vm_2.id)
        test_utils.update_port_allowed_address_pairs(
            neutron_client,
            vm2_port['id'],
            [test_utils.AllowedAddressPair(
                TESTCASE_CONFIG.extra_route_cidr,
                vm2_port['mac_address'])])

        test_utils.async_Wait_for_instances([vm_1, vm_2])

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

        msg = ("Associate router '%s' to the VPN." %
               TESTCASE_CONFIG.router_1_name)
        results.record_action(msg)
        results.add_to_summary(0, "-")

        test_utils.create_router_association(
            neutron_client, bgpvpn_id, router_1_id)

        test_utils.update_router_extra_route(
            neutron_client, router_1_id,
            [test_utils.ExtraRoute(TESTCASE_CONFIG.extra_route_cidr,
                                   vm_1_ip),
             test_utils.ExtraRoute(TESTCASE_CONFIG.extra_route_cidr,
                                   vm_2_ip)])

        image_2_id = os_utils.create_glance_image(
            glance_client, TESTCASE_CONFIG.image_name,
            COMMON_CONFIG.image_path, disk=COMMON_CONFIG.image_format,
            container="bare", public='public')
        image_ids.append(image_2_id)

        logger.info("Waiting for the VMs to connect to each other using the"
                    " updated network configuration")
        test_utils.wait_before_subtest()

        u3 = test_utils.generate_ping_userdata(
            [TESTCASE_CONFIG.extra_route_ip])
        vm_3 = test_utils.create_instance(
            nova_client,
            TESTCASE_CONFIG.instance_3_name,
            image_2_id,
            network_1_id,
            sg_id,
            flavor=COMMON_CONFIG.custom_flavor_name,
            secgroup_name=TESTCASE_CONFIG.secgroup_name,
            compute_node=av_zone_2,
            userdata=u3)

        instance_ids.extend([vm_1.id, vm_2.id, vm_3.id])

        instance_dhcp_up = test_utils.wait_for_instances_get_dhcp(vm_3)

        if (not instance_dhcp_up):
            logger.error("vm_3 instance is down")

        results.get_ping_status_target_ip(vm_3,
                                          TESTCASE_CONFIG.extra_route_name,
                                          TESTCASE_CONFIG.extra_route_ip,
                                          expected="PASS",
                                          timeout=300)

        results.add_to_summary(0, "=")
        logger.info("\n%s" % results.summary)

    except Exception as e:
        logger.error("exception occurred while executing testcase_13: %s", e)
        raise
    finally:
        test_utils.update_router_no_extra_route(neutron_client, router_ids)
        test_utils.cleanup_nova(nova_client, instance_ids)
        test_utils.cleanup_glance(glance_client, image_ids)
        test_utils.cleanup_neutron(neutron_client, floatingip_ids,
                                   bgpvpn_ids, interfaces, subnet_ids,
                                   router_ids, network_ids)

    return results.compile_summary()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
