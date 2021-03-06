#!/usr/bin/env python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Test whether router assoc can coexist with floating IP
# - Create VM1 in net1 with a subnet which is connected to a router
#    which is connected with the gateway
# - Create VM2 in net2 with a subnet without a router attached.
# - Create bgpvpn with iRT=eRT
# - Assoc the router of net1 with bgpvpn and assoc net 2 with the bgpvpn
# - Try to ping from one VM to the other
# - Assign a floating IP to the VM in the router assoc network
# - Ping it the floating ip
import logging
import sys

from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import openstack_utils as os_utils
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib.results import Results


logger = logging.getLogger(__name__)

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.testcase_8')


def main():
    conn = os_utils.get_os_connection()
    results = Results(COMMON_CONFIG.line_length, conn)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    neutron_client = os_utils.get_neutron_client()

    (floatingip_ids, instance_ids, router_ids, network_ids, image_ids,
     subnet_ids, interfaces, bgpvpn_ids) = ([] for i in range(8))

    try:
        image_id = os_utils.create_glance_image(
            conn, TESTCASE_CONFIG.image_name,
            COMMON_CONFIG.image_path, disk=COMMON_CONFIG.image_format,
            container="bare", public='public')
        image_ids.append(image_id)

        network_1_id, subnet_1_id, router_1_id = test_utils.create_network(
            conn,
            TESTCASE_CONFIG.net_1_name,
            TESTCASE_CONFIG.subnet_1_name,
            TESTCASE_CONFIG.subnet_1_cidr,
            TESTCASE_CONFIG.router_1_name)

        network_2_id, subnet_2_id, router_1_id = test_utils.create_network(
            conn,
            TESTCASE_CONFIG.net_2_name,
            TESTCASE_CONFIG.subnet_2_name,
            TESTCASE_CONFIG.subnet_2_cidr,
            TESTCASE_CONFIG.router_1_name)

        interfaces.append(tuple((router_1_id, subnet_1_id)))
        interfaces.append(tuple((router_1_id, subnet_2_id)))
        network_ids.extend([network_1_id, network_2_id])
        router_ids.append(router_1_id)
        subnet_ids.extend([subnet_1_id, subnet_2_id])

        sg_id = os_utils.create_security_group_full(
            conn, TESTCASE_CONFIG.secgroup_name,
            TESTCASE_CONFIG.secgroup_descr)
        test_utils.open_icmp(conn, sg_id)
        test_utils.open_http_port(conn, sg_id)

        compute_nodes = test_utils.assert_and_get_compute_nodes(conn)
        av_zone_1 = "nova:" + compute_nodes[0]
        # spawning the VMs on the same compute because fib flow (21) entries
        # are not created properly if vm1 and vm2 are attached to two
        # different computes
        vm_2 = test_utils.create_instance(
            conn,
            TESTCASE_CONFIG.instance_2_name,
            image_id,
            network_2_id,
            sg_id,
            secgroup_name=TESTCASE_CONFIG.secgroup_name,
            compute_node=av_zone_1)
        vm_2_ip = test_utils.get_instance_ip(conn, vm_2)

        u1 = test_utils.generate_ping_userdata([vm_2_ip])
        vm_1 = test_utils.create_instance(
            conn,
            TESTCASE_CONFIG.instance_1_name,
            image_id,
            network_1_id,
            sg_id,
            secgroup_name=TESTCASE_CONFIG.secgroup_name,
            compute_node=av_zone_1,
            userdata=u1)
        instance_ids.extend([vm_1.id, vm_2.id])
        # TODO: uncomment the lines 107-134 once ODL fixes
        # the bug https://jira.opendaylight.org/browse/NETVIRT-932
        # results.record_action("Create VPN with eRT==iRT")
        # vpn_name = "sdnvpn-8"
        # kwargs = {
        #     "import_targets": TESTCASE_CONFIG.targets,
        #     "export_targets": TESTCASE_CONFIG.targets,
        #     "route_distinguishers": TESTCASE_CONFIG.route_distinguishers,
        #     "name": vpn_name
        # }
        # bgpvpn = test_utils.create_bgpvpn(neutron_client, **kwargs)
        # bgpvpn_id = bgpvpn['bgpvpn']['id']
        # logger.debug("VPN created details: %s" % bgpvpn)
        # bgpvpn_ids.append(bgpvpn_id)

        # msg = ("Associate router '%s' and net '%s' to the VPN."
        #        % (TESTCASE_CONFIG.router_1_name,
        #           TESTCASE_CONFIG.net_2_name))
        # results.record_action(msg)
        # results.add_to_summary(0, "-")

        # test_utils.create_router_association(
        #     neutron_client, bgpvpn_id, router_1_id)
        # test_utils.create_network_association(
        #     neutron_client, bgpvpn_id, network_2_id)

        # test_utils.wait_for_bgp_router_assoc(
        #     neutron_client, bgpvpn_id, router_1_id)
        # test_utils.wait_for_bgp_net_assoc(
        #     neutron_client, bgpvpn_id, network_2_id)

        # Wait for VMs to get ips.
        instances_up = test_utils.wait_for_instances_up(vm_2)
        instances_dhcp_up = test_utils.wait_for_instances_get_dhcp(vm_1)

        if (not instances_up or not instances_dhcp_up):
            logger.error("One or more instances are down")
            # TODO: Handle this appropriately

        logger.info("Waiting for the VMs to connect to each other using the"
                    " updated network configuration")
        test_utils.wait_before_subtest()

        results.get_ping_status(vm_1, vm_2, expected="PASS", timeout=200)
        results.add_to_summary(0, "=")

        msg = "Assign a Floating IP to %s" % vm_1.name
        results.record_action(msg)

        vm1_port = test_utils.get_port(conn, vm_1.id)
        fip_added = os_utils.attach_floating_ip(conn, vm1_port.id)

        if fip_added:
            results.add_success(msg)
        else:
            results.add_failure(msg)

        fip = fip_added.floating_ip_address

        results.add_to_summary(0, "=")
        results.record_action("Ping %s via Floating IP" % vm_1.name)
        results.add_to_summary(0, "-")
        results.ping_ip_test(fip)

        floatingip_ids.append(fip_added.id)

    except Exception as e:
        logger.error("exception occurred while executing testcase_8: %s", e)
        raise
    finally:
        test_utils.cleanup_nova(conn, instance_ids)
        test_utils.cleanup_glance(conn, image_ids)
        test_utils.cleanup_neutron(conn, neutron_client, floatingip_ids,
                                   bgpvpn_ids, interfaces, subnet_ids,
                                   router_ids, network_ids)

    return results.compile_summary()


if __name__ == '__main__':
    sys.exit(main())
