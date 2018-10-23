#!/usr/bin/env python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

import base64
import logging
import sys
import pkg_resources

from random import randint
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import openstack_utils as os_utils
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib.results import Results

logger = logging.getLogger(__name__)

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.testcase_2bis')


def main():
    conn = os_utils.get_os_connection()
    results = Results(COMMON_CONFIG.line_length, conn)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    conn = os_utils.get_os_connection()
    # neutron client is needed as long as bgpvpn heat module
    # is not yet installed by default in apex (APEX-618)
    neutron_client = os_utils.get_neutron_client()

    image_ids = []
    bgpvpn_ids = []

    try:
        logger.debug("Using private key %s injected to the VMs."
                     % COMMON_CONFIG.keyfile_path)
        keyfile = open(COMMON_CONFIG.keyfile_path, 'r')
        key_buf = keyfile.read()
        keyfile.close()
        key = base64.b64encode(key_buf)

        # image created outside HOT (OS::Glance::Image deprecated since ocata)
        image_id = os_utils.create_glance_image(
            conn, TESTCASE_CONFIG.image_name,
            COMMON_CONFIG.image_path, disk=COMMON_CONFIG.image_format,
            container="bare", public='public')
        image_ids = [image_id]

        compute_nodes = test_utils.assert_and_get_compute_nodes(conn)

        az_1 = "nova:" + compute_nodes[0]
        # av_zone_2 = "nova:" + compute_nodes[1]

        file_path = pkg_resources.resource_filename(
            'sdnvpn', TESTCASE_CONFIG.hot_file_name)
        templ = open(file_path, 'r').read()
        logger.debug("Template is read: '%s'" % templ)
        env = test_utils.get_heat_environment(TESTCASE_CONFIG, COMMON_CONFIG)
        logger.debug("Environment is read: '%s'" % env)

        env['name'] = TESTCASE_CONFIG.stack_name
        env['template'] = templ
        env['parameters']['image_n'] = TESTCASE_CONFIG.image_name
        env['parameters']['av_zone_1'] = az_1
        env['parameters']['id_rsa_key'] = key

        stack_id = os_utils.create_stack(conn, **env)
        if stack_id is None:
            logger.error("Stack create start failed")
            raise SystemError("Stack create start failed")

        test_utils.wait_stack_for_status(conn, stack_id, 'CREATE_COMPLETE')

        net_1_output = os_utils.get_output(conn, stack_id, 'net_1_o')
        network_1_id = net_1_output['output_value']
        net_2_output = os_utils.get_output(conn, stack_id, 'net_2_o')
        network_2_id = net_2_output['output_value']

        vm_stack_output_keys = ['vm1_o', 'vm2_o', 'vm3_o', 'vm4_o', 'vm5_o']
        vms = test_utils.get_vms_from_stack_outputs(conn,
                                                    stack_id,
                                                    vm_stack_output_keys)

        logger.debug("Entering base test case with stack '%s'" % stack_id)

        msg = ("Create VPN1 with eRT=iRT")
        results.record_action(msg)
        vpn1_name = "sdnvpn-1-" + str(randint(100000, 999999))
        kwargs = {
            "import_targets": TESTCASE_CONFIG.targets2,
            "export_targets": TESTCASE_CONFIG.targets2,
            "route_targets": TESTCASE_CONFIG.targets2,
            "route_distinguishers": TESTCASE_CONFIG.route_distinguishers1,
            "name": vpn1_name
        }
        bgpvpn1 = test_utils.create_bgpvpn(neutron_client, **kwargs)
        bgpvpn1_id = bgpvpn1['bgpvpn']['id']
        logger.debug("VPN1 created details: %s" % bgpvpn1)
        bgpvpn_ids.append(bgpvpn1_id)

        msg = ("Associate network '%s' to the VPN." %
               TESTCASE_CONFIG.heat_parameters['net_1_name'])
        results.record_action(msg)
        results.add_to_summary(0, "-")

        test_utils.create_network_association(
            neutron_client, bgpvpn1_id, network_1_id)

        logger.info("Waiting for the VMs to connect to each other using the"
                    " updated network configuration for VPN1")
        test_utils.wait_before_subtest()

        # Remember: vms[X] has instance_X+1_name

        # 10.10.10.12 should return sdnvpn-2 to sdnvpn-1
        results.check_ssh_output(
            vms[0], vms[1],
            expected=TESTCASE_CONFIG.heat_parameters['instance_2_name'],
            timeout=200)

        results.add_to_summary(0, "-")
        msg = ("Create VPN2 with eRT=iRT")
        results.record_action(msg)
        vpn2_name = "sdnvpn-2-" + str(randint(100000, 999999))
        kwargs = {
            "import_targets": TESTCASE_CONFIG.targets1,
            "export_targets": TESTCASE_CONFIG.targets1,
            "route_targets": TESTCASE_CONFIG.targets1,
            "route_distinguishers": TESTCASE_CONFIG.route_distinguishers2,
            "name": vpn2_name
        }
        bgpvpn2 = test_utils.create_bgpvpn(neutron_client, **kwargs)
        bgpvpn2_id = bgpvpn2['bgpvpn']['id']
        logger.debug("VPN created details: %s" % bgpvpn2)
        bgpvpn_ids.append(bgpvpn2_id)

        msg = ("Associate network '%s' to the VPN2." %
               TESTCASE_CONFIG.heat_parameters['net_2_name'])
        results.record_action(msg)
        results.add_to_summary(0, "-")

        test_utils.create_network_association(
            neutron_client, bgpvpn2_id, network_2_id)

        test_utils.wait_for_bgp_net_assoc(neutron_client,
                                          bgpvpn1_id, network_1_id)
        test_utils.wait_for_bgp_net_assoc(neutron_client,
                                          bgpvpn2_id, network_2_id)

        logger.info("Waiting for the VMs to connect to each other using the"
                    " updated network configuration for VPN2")
        test_utils.wait_before_subtest()

        # 10.10.10.11 should return "not reachable" to sdnvpn-4
        results.check_ssh_output(vms[3], vms[0],
                                 expected="not reachable",
                                 timeout=30)

    except Exception as e:
        logger.error("exception occurred while executing testcase_2bis: %s", e)
        raise
    finally:
        test_utils.cleanup_glance(conn, image_ids)
        test_utils.cleanup_neutron(conn, neutron_client, [], bgpvpn_ids,
                                   [], [], [], [])

        try:
            test_utils.delete_stack_and_wait(conn, stack_id)
        except Exception as e:
            logger.error(
                "exception occurred while executing testcase_2bis: %s", e)

    return results.compile_summary()


if __name__ == '__main__':
    sys.exit(main())
