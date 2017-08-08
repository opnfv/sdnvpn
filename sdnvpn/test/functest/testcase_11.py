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
    'sdnvpn.test.functest.testcase_11')


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
        # Get a list of groups, before start topology
        initial_ovs_groups = test_utils.get_ovs_groups(compute_nodes,
                                                       [ovs_br])

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
            # TODO: Handle this appropriately

        logging.info("Wait before subtest")
        test_utils.wait_before_subtest()
        # Get added OVS groups
        added_ovs_groups = (len(initial_ovs_groups) -
                            len(test_utils.get_ovs_groups(
                                compute_nodes, [ovs_br])))
        # Check if group added successfully
        results.record_action("Check if a new group was added to OVS")
        msg = "New OVS group added"
        results.add_to_summary(0, "-")
        if added_ovs_groups != 0:
            results.add_success(msg)
        else:
            results.add_failure(msg)
        results.add_to_summary(0, "=")
        # Backup OVS controller connection info.
        # To support HA changes should be made here.
        get_ext_ip_cmd = "sudo ovs-vsctl get-controller {}".format(ovs_br)
        ovs_controller_conn = (compute_nodes[0].run_cmd(get_ext_ip_cmd).
                               strip().split('\n')[0])
        # Disconnect OVS from controller
        for compute_node in compute_nodes:
            compute_node.run_cmd("sudo ovs-vsctl del-controller {}".
                                 format(ovs_br))
    except Exception as e:
        logger.error("exception occurred while executing testcase_1: %s", e)
        raise
    finally:
        # Cleanup topology
        test_utils.cleanup_nova(nova_client, instance_ids, image_ids)
        test_utils.cleanup_neutron(neutron_client, floatingip_ids, bgpvpn_ids,
                                   interfaces, subnet_ids, router_ids,
                                   network_ids)
    # Connect again OVS to Controller
    for compute_node in compute_nodes:
        compute_node.run_cmd("sudo ovs-vsctl set-controller {} {}".
                             format(ovs_br, ovs_controller_conn))
    logging.info("Wait before subtest")
    test_utils.wait_before_subtest()
    # Get OVS groups added after the reconnection
    added_ovs_groups = (len(initial_ovs_groups) -
                        len(test_utils.get_ovs_groups(
                            compute_nodes, [ovs_br])))

    # Check if group removed successfully
    results.record_action("Check if group was removed from OVS "
                          "after deleting the topology.")
    msg = ""
    # After removing the topology, groups must be equal to the initial
    if added_ovs_groups != 0:
        msg += " Additional group was not deleted from OVS"
    results.add_to_summary(0, "-")
    if len(msg) == 0:
        msg = "Group was deleted from ovs"
        results.add_success(msg)
    else:
        results.add_failure(msg)

    return results.compile_summary()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
