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
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib.results import Results

logger = logging.getLogger(__name__)

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.testcase_12')


def main():
    results = Results(COMMON_CONFIG.line_length)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()
    glance_client = os_utils.get_glance_client()
    openstack_nodes = test_utils.get_nodes()

    (floatingip_ids, instance_ids, router_ids, network_ids, image_ids,
     subnet_ids, interfaces, bgpvpn_ids) = ([] for i in range(8))

    try:
        image_id = os_utils.create_glance_image(
            glance_client, TESTCASE_CONFIG.image_name,
            COMMON_CONFIG.image_path, disk=COMMON_CONFIG.image_format,
            container="bare", public='public')
        image_ids.append(image_id)

        network_1_id = test_utils.create_net(neutron_client,
                                             TESTCASE_CONFIG.net_1_name)
        subnet_1_id = test_utils.create_subnet(neutron_client,
                                               TESTCASE_CONFIG.subnet_1_name,
                                               TESTCASE_CONFIG.subnet_1_cidr,
                                               network_1_id)

        network_ids.append(network_1_id)
        subnet_ids.append(subnet_1_id)

        sg_id = os_utils.create_security_group_full(
            neutron_client, TESTCASE_CONFIG.secgroup_name,
            TESTCASE_CONFIG.secgroup_descr)

        # Check required number of compute nodes
        compute_hostname = (
            nova_client.hypervisors.list()[0].hypervisor_hostname)
        compute_nodes = [node for node in openstack_nodes
                         if node.is_compute()]

        av_zone_1 = "nova:" + compute_hostname
        # List of OVS bridges to get groups
        ovs_br = "br-int"
        # Get a list of flows and groups, before start topology
        initial_ovs_flows = len(test_utils.get_ovs_flows(compute_nodes,
                                                         [ovs_br]))
        initial_ovs_groups = len(test_utils.get_ovs_groups(compute_nodes,
                                                           [ovs_br]))

        # boot INSTANCES
        vm_2 = test_utils.create_instance(
            nova_client,
            TESTCASE_CONFIG.instance_2_name,
            image_id,
            network_1_id,
            sg_id,
            secgroup_name=TESTCASE_CONFIG.secgroup_name,
            compute_node=av_zone_1)

        vm_1 = test_utils.create_instance(
            nova_client,
            TESTCASE_CONFIG.instance_1_name,
            image_id,
            network_1_id,
            sg_id,
            secgroup_name=TESTCASE_CONFIG.secgroup_name,
            compute_node=av_zone_1)
        instance_ids.extend([vm_1.id, vm_2.id])

        # Wait for VMs to get ips.
        instances_up = test_utils.wait_for_instances_up(vm_1, vm_2)

        if not instances_up:
            logger.error("One or more instances is down")

        logging.info("Wait before subtest")
        test_utils.wait_before_subtest()
        # Get added OVS flows and groups
        added_ovs_flows = len(test_utils.get_ovs_flows(compute_nodes,
                                                       [ovs_br]))
        added_ovs_groups = len(test_utils.get_ovs_groups(compute_nodes,
                                                         [ovs_br]))
        # Check if flows and groups added successfully
        results.record_action("Check if new flows and groups were added "
                              "to OVS")

        msg = "New OVS flows added"
        results.add_to_summary(0, "-")
        if added_ovs_flows - initial_ovs_flows > 0:
            results.add_success(msg)
        else:
            results.add_failure(msg)
        results.add_to_summary(0, "=")

        msg = "New OVS groups added"
        results.add_to_summary(0, "-")
        if added_ovs_groups - initial_ovs_groups > 0:
            results.add_success(msg)
        else:
            results.add_failure(msg)
        results.add_to_summary(0, "=")

        get_ext_ip_cmd = "sudo ovs-vsctl get-controller {}".format(ovs_br)
        ovs_controller_conn = (compute_nodes[0].run_cmd(get_ext_ip_cmd).
                               strip().split('\n')[0])

        for compute_node in compute_nodes:
            # Disconnect OVS from controller
            compute_node.run_cmd("sudo ovs-vsctl del-controller {}".
                                 format(ovs_br))
            test_utils.wait_before_subtest()
            # Connect again OVS to Controller
            compute_node.run_cmd("sudo ovs-vsctl set-controller {} {}".
                                 format(ovs_br, ovs_controller_conn))

        logging.info("Wait before subtest resync type 1")
        test_utils.wait_before_subtest()
        # Get OVS flows added after the reconnection
        resynced_ovs_flows = len(test_utils.get_ovs_flows(
            compute_nodes, [ovs_br]))
        # Get OVS groups added after the reconnection
        resynced_ovs_groups = len(test_utils.get_ovs_groups(
            compute_nodes, [ovs_br]))

        record_action_msg = ("Check if flows/groups are reprogrammed in OVS "
                             "after its reconnection by del/set controller.")
        record_test_result(added_ovs_flows, resynced_ovs_flows,
                           added_ovs_groups, resynced_ovs_groups,
                           record_action_msg, results)

        for compute_node in compute_nodes:
            # Disconnect OVS from controller
            compute_node.run_cmd("sudo iptables -A OUTPUT -p tcp --dport 6653"
                                 " -j DROP")
            test_utils.wait_before_subtest()
            # Connect again OVS to Controller
            compute_node.run_cmd("sudo iptables -D OUTPUT -p tcp --dport 6653"
                                 " -j DROP")

        logging.info("Wait before subtest resync type 2")
        test_utils.wait_before_subtest()
        # Get OVS flows added after the reconnection
        resynced_ovs_flows = len(test_utils.get_ovs_flows(
            compute_nodes, [ovs_br]))
        # Get OVS groups added after the reconnection
        resynced_ovs_groups = len(test_utils.get_ovs_groups(
            compute_nodes, [ovs_br]))

        record_action_msg = ("Check if flows/groups are reprogrammed in OVS "
                             "after its reconnection by firewall rule for "
                             "OF port block/unblok")
        record_test_result(added_ovs_flows, resynced_ovs_flows,
                           added_ovs_groups, resynced_ovs_groups,
                           record_action_msg, results)

    except Exception as e:
        logger.error("exception occurred while executing testcase_12: %s", e)
        raise
    finally:
        # Cleanup topology
        test_utils.cleanup_nova(nova_client, instance_ids)
        test_utils.cleanup_glance(glance_client, image_ids)
        test_utils.cleanup_neutron(neutron_client, floatingip_ids, bgpvpn_ids,
                                   interfaces, subnet_ids, router_ids,
                                   network_ids)

    return results.compile_summary()


def record_test_result(expected_flow_count, actual_flow_count,
                       expected_group_count, actual_group_count,
                       record_msg, results):
    results.record_action(record_msg)
    msg = "OVS flows are programmed after resync"
    results.add_to_summary(0, "-")
    if expected_flow_count - actual_flow_count == 0:
        results.add_success(msg)
    else:
        results.add_failure(msg)
    results.add_to_summary(0, "=")

    msg = "OVS groups are programmed after resync"
    results.add_to_summary(0, "-")
    if expected_group_count - actual_group_count != 0:
        results.add_success(msg)
    else:
        results.add_failure(msg)
    results.add_to_summary(0, "=")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
