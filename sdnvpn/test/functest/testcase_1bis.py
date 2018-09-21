#!/usr/bin/env python
#
# Copyright (c) 2018 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

import logging
import sys

from random import randint
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import openstack_utils as os_utils
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib.results import Results

logger = logging.getLogger(__name__)

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.testcase_1bis')


def main():
    results = Results(COMMON_CONFIG.line_length)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    conn = os_utils.get_cloud_connection()
    # neutron client is needed as long as bgpvpn heat module
    # is not yet installed by default in apex (APEX-618)
    neutron_client = os_utils.get_neutron_client()
    # needed to create the image (OS::Glance::Image deprecated since ocata)
    glance_client = os_utils.get_glance_client()
    # needed to get the availability zones list
    # and the vm objects
    nova_client = os_utils.get_nova_client()

    image_ids = []
    bgpvpn_ids = []

    try:
        image_id = os_utils.create_glance_image(
            glance_client, TESTCASE_CONFIG.image_name,
            COMMON_CONFIG.image_path, disk=COMMON_CONFIG.image_format,
            container="bare", public='public')
        image_ids = [image_id]

        compute_nodes = test_utils.assert_and_get_compute_nodes(nova_client)
        az_1 = "nova:" + compute_nodes[0]
        az_2 = "nova:" + compute_nodes[1]

        templ = open(TESTCASE_CONFIG.hot_file_name, 'r').read()
        logger.debug("Template is read: '%s'" % templ)
        env = test_utils.get_heat_environment(TESTCASE_CONFIG, COMMON_CONFIG)
        logger.debug("Environment is read: '%s'" % env)

        kwargs = {
            "name": TESTCASE_CONFIG.stack_name,
            "template": templ,
            "environment": env,
            "parameters": {
                "image_n": TESTCASE_CONFIG.image_name,
                "av_zone_1": az_1,
                "av_zone_2": az_2
            }
        }
        stack_id = os_utils.create_stack(conn, **kwargs)

        test_utils.wait_stack_create(conn, stack_id)

        net_1_output = os_utils.get_output(conn, stack_id, 'net_1_o')
        network_1_id = net_1_output['output']['output_value']
        net_2_output = os_utils.get_output(conn, stack_id, 'net_2_o')
        network_2_id = net_2_output['output']['output_value']

        vm_stack_output_keys = ['vm1_o', 'vm2_o', 'vm3_o', 'vm4_o', 'vm5_o']
        vms = test_utils.get_vms_from_stack_outputs(conn,
                                                    nova_client,
                                                    stack_id,
                                                    vm_stack_output_keys)

        logger.debug("Entering base test case with stack '%s'" % stack_id)

        msg = ("Create VPN with eRT<>iRT")
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
               TESTCASE_CONFIG.heat_parameters['net_1_name'])
        results.record_action(msg)
        results.add_to_summary(0, "-")

        test_utils.create_network_association(
            neutron_client, bgpvpn_id, network_1_id)

        # Remember: vms[X] is former vm__X+1

        results.get_ping_status(vms[0], vms[1], expected="PASS", timeout=200)
        results.get_ping_status(vms[0], vms[2], expected="PASS", timeout=30)
        results.get_ping_status(vms[0], vms[3], expected="FAIL", timeout=30)

        msg = ("Associate network '%s' to the VPN." %
               TESTCASE_CONFIG.heat_parameters['net_2_name'])
        results.add_to_summary(0, "-")
        results.record_action(msg)
        results.add_to_summary(0, "-")

        test_utils.create_network_association(
            neutron_client, bgpvpn_id, network_2_id)

        test_utils.wait_for_bgp_net_assocs(neutron_client,
                                           bgpvpn_id,
                                           network_1_id,
                                           network_2_id)

        logger.info("Waiting for the VMs to connect to each other using the"
                    " updated network configuration")
        test_utils.wait_before_subtest()

        results.get_ping_status(vms[3], vms[4], expected="PASS", timeout=30)
        # TODO enable again when isolation in VPN with iRT != eRT works
        # results.get_ping_status(vms[0], vms[3], expected="FAIL", timeout=30)
        # results.get_ping_status(vms[0], vms[4], expected="FAIL", timeout=30)

        msg = ("Update VPN with eRT=iRT ...")
        results.add_to_summary(0, "-")
        results.record_action(msg)
        results.add_to_summary(0, "-")

        # use bgpvpn-create instead of update till NETVIRT-1067 bug is fixed
        # kwargs = {"import_targets": TESTCASE_CONFIG.targets1,
        #           "export_targets": TESTCASE_CONFIG.targets1,
        #           "name": vpn_name}
        # bgpvpn = test_utils.update_bgpvpn(neutron_client,
        #                                   bgpvpn_id, **kwargs)

        test_utils.delete_bgpvpn(neutron_client, bgpvpn_id)
        bgpvpn_ids.remove(bgpvpn_id)
        kwargs = {
            "import_targets": TESTCASE_CONFIG.targets1,
            "export_targets": TESTCASE_CONFIG.targets1,
            "route_distinguishers": TESTCASE_CONFIG.route_distinguishers,
            "name": vpn_name
        }

        test_utils.wait_before_subtest()

        bgpvpn = test_utils.create_bgpvpn(neutron_client, **kwargs)
        bgpvpn_id = bgpvpn['bgpvpn']['id']
        logger.debug("VPN re-created details: %s" % bgpvpn)
        bgpvpn_ids.append(bgpvpn_id)

        msg = ("Associate network '%s' to the VPN." %
               TESTCASE_CONFIG.heat_parameters['net_1_name'])
        results.record_action(msg)
        results.add_to_summary(0, "-")

        test_utils.create_network_association(
            neutron_client, bgpvpn_id, network_1_id)

        test_utils.create_network_association(
            neutron_client, bgpvpn_id, network_2_id)

        test_utils.wait_for_bgp_net_assocs(neutron_client,
                                           bgpvpn_id,
                                           network_1_id,
                                           network_2_id)
        # The above code has to be removed after re-enabling bgpvpn-update

        logger.info("Waiting for the VMs to connect to each other using the"
                    " updated network configuration")
        test_utils.wait_before_subtest()

        results.get_ping_status(vms[0], vms[3], expected="PASS", timeout=30)
        results.get_ping_status(vms[0], vms[4], expected="PASS", timeout=30)

    except Exception as e:
        logger.error("exception occurred while executing testcase_1bis: %s", e)
        raise
    finally:
        test_utils.cleanup_glance(glance_client, image_ids)
        test_utils.cleanup_neutron(neutron_client, [], bgpvpn_ids,
                                                   [], [], [], [])

        test_utils.delete_stack_and_wait(conn, stack_id)

    return results.compile_summary()


if __name__ == '__main__':
    sys.exit(main())
