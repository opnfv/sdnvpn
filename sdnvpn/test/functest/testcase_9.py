#!/usr/bin/env python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Tests performed:
# - Peering OpenDaylight with Quagga:
#   - Set up a Quagga instance in the functest container
#   - Start a BGP router with OpenDaylight
#   - Add the functest Quagga as a neighbor
#   - Verify that the OpenDaylight and gateway Quagga peer
import logging
import sys
import os

from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib.results import Results

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    "sdnvpn.test.functest.testcase_9")

logger = logging.getLogger('__name__')


def main():
    results = Results(COMMON_CONFIG.line_length)
    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    openstack_nodes = test_utils.get_nodes()
    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    # node.is_odl() doesn't work in Apex
    # https://jira.opnfv.org/browse/RELENG-192
    fuel_cmd = "sudo systemctl status opendaylight"
    apex_cmd = "sudo docker exec opendaylight_api " \
               "/opt/opendaylight/bin/status"
    health_cmd = "sudo docker ps | grep opendaylight_api"
    if installer_type in ["fuel"]:
        controllers = [node for node in openstack_nodes
                       if "running" in node.run_cmd(fuel_cmd)]
    elif installer_type in ["apex"]:
        controllers = [node for node in openstack_nodes
                       if "healthy" in node.run_cmd(health_cmd)
                       if "Running" in node.run_cmd(apex_cmd)]

    msg = ("Verify that all OpenStack nodes OVS br-int have "
           "fail_mode set to secure")
    results.record_action(msg)
    results.add_to_summary(0, "-")
    if not controllers:
        msg = ("Controller (ODL) list is empty. Skipping rest of tests.")
        logger.info(msg)
        results.add_failure(msg)
        return results.compile_summary()
    else:
        msg = ("Controller (ODL) list is ready")
        logger.info(msg)
        results.add_success(msg)
    # Get fail_mode status on all nodes
    fail_mode_statuses = test_utils.is_fail_mode_secure()
    for node_name, status in fail_mode_statuses.iteritems():
        msg = 'Node {} br-int is fail_mode secure'.format(node_name)
        if status:
            results.add_success(msg)
        else:
            results.add_failure(msg)

    return results.compile_summary()


if __name__ == '__main__':
    sys.exit(main())
