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
import pkg_resources

from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import openstack_utils as os_utils
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib.results import Results


logger = logging.getLogger(__name__)

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.testcase_8bis')


def main():
    conn = os_utils.get_os_connection()
    results = Results(COMMON_CONFIG.line_length, conn)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    # neutron client is needed as long as bgpvpn heat module
    # is not yet installed by default in apex (APEX-618)
    neutron_client = os_utils.get_neutron_client()

    image_ids = []
    bgpvpn_ids = []

    try:
        image_id = os_utils.create_glance_image(
            conn, TESTCASE_CONFIG.image_name,
            COMMON_CONFIG.image_path, disk=COMMON_CONFIG.image_format,
            container='bare', public='public')
        image_ids = [image_id]

        compute_nodes = test_utils.assert_and_get_compute_nodes(conn)
        az_1 = "nova:" + compute_nodes[0]
        # spawning the VMs on the same compute because fib flow (21) entries
        # are not created properly if vm1 and vm2 are attached to two
        # different computes

        file_path = pkg_resources.resource_filename(
            'sdnvpn', TESTCASE_CONFIG.hot_file_name)
        templ = open(file_path, 'r').read()
        logger.debug("Template is read: '%s'" % templ)
        env = test_utils.get_heat_environment(TESTCASE_CONFIG, COMMON_CONFIG)
        logger.debug("Environment is read: '%s'" % env)

        env['name'] = TESTCASE_CONFIG.stack_name
        env['parameters']['external_nw'] = os_utils.get_external_net(conn)
        env['template'] = templ
        env['parameters']['image_n'] = TESTCASE_CONFIG.image_name
        env['parameters']['av_zone_1'] = az_1

        stack_id = os_utils.create_stack(conn, **env)
        if stack_id is None:
            logger.error('Stack create start failed')
            raise SystemError('Stack create start failed')

        test_utils.wait_stack_for_status(conn, stack_id, 'CREATE_COMPLETE')

        router_1_output = os_utils.get_output(conn, stack_id, 'router_1_o')
        router_1_id = router_1_output['output_value']
        net_2_output = os_utils.get_output(conn, stack_id, 'net_2_o')
        network_2_id = net_2_output['output_value']

        vm_stack_output_keys = ['vm1_o', 'vm2_o']
        vms = test_utils.get_vms_from_stack_outputs(conn,
                                                    stack_id,
                                                    vm_stack_output_keys)

        logger.debug("Entering base test case with stack '%s'" % stack_id)

        # TODO: check if ODL fixed bug
        # https://jira.opendaylight.org/browse/NETVIRT-932
        results.record_action('Create VPN with eRT==iRT')
        vpn_name = 'sdnvpn-8'
        kwargs = {
            'import_targets': TESTCASE_CONFIG.targets,
            'export_targets': TESTCASE_CONFIG.targets,
            'route_distinguishers': TESTCASE_CONFIG.route_distinguishers,
            'name': vpn_name
        }
        bgpvpn = test_utils.create_bgpvpn(neutron_client, **kwargs)
        bgpvpn_id = bgpvpn['bgpvpn']['id']
        logger.debug("VPN created details: %s" % bgpvpn)
        bgpvpn_ids.append(bgpvpn_id)

        msg = ("Associate router '%s' and net '%s' to the VPN."
               % (TESTCASE_CONFIG.heat_parameters['router_1_name'],
                  TESTCASE_CONFIG.heat_parameters['net_2_name']))
        results.record_action(msg)
        results.add_to_summary(0, "-")

        test_utils.create_router_association(
            neutron_client, bgpvpn_id, router_1_id)
        test_utils.create_network_association(
            neutron_client, bgpvpn_id, network_2_id)

        test_utils.wait_for_bgp_router_assoc(
            neutron_client, bgpvpn_id, router_1_id)
        test_utils.wait_for_bgp_net_assoc(
            neutron_client, bgpvpn_id, network_2_id)

        results.get_ping_status(vms[0], vms[1], expected="PASS", timeout=200)
        results.add_to_summary(0, "=")

        msg = "Assign a Floating IP to %s - using stack update" % vms[0].name
        results.record_action(msg)

        file_path = pkg_resources.resource_filename(
            'sdnvpn', TESTCASE_CONFIG.hot_update_file_name)
        templ_update = open(file_path, 'r').read()
        logger.debug("Update template is read: '%s'" % templ_update)
        templ = test_utils.merge_yaml(templ, templ_update)

        env['name'] = TESTCASE_CONFIG.stack_name
        env['parameters']['external_nw'] = os_utils.get_external_net(conn)
        env['template'] = templ
        env['parameters']['image_n'] = TESTCASE_CONFIG.image_name
        env['parameters']['av_zone_1'] = az_1

        os_utils.update_stack(conn, stack_id, **env)

        test_utils.wait_stack_for_status(conn, stack_id, 'UPDATE_COMPLETE')

        fip_1_output = os_utils.get_output(conn, stack_id, 'fip_1_o')
        fip = fip_1_output['output_value']

        results.add_to_summary(0, "=")
        results.record_action("Ping %s via Floating IP" % vms[0].name)
        results.add_to_summary(0, "-")
        results.ping_ip_test(fip)

    except Exception as e:
        logger.error("exception occurred while executing testcase_8bis: %s", e)
        raise
    finally:
        test_utils.cleanup_glance(conn, image_ids)
        test_utils.cleanup_neutron(conn, neutron_client, [], bgpvpn_ids,
                                   [], [], [], [])

        try:
            test_utils.delete_stack_and_wait(conn, stack_id)
        except Exception as e:
            logger.error(
                "exception occurred while executing testcase_8bis: %s", e)

    return results.compile_summary()


if __name__ == '__main__':
    sys.exit(main())
