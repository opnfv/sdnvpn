#!/usr/bin/python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

import argparse
import functest.utils.functest_logger as ft_logger
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib.results import Results
from opnfv.deployment.factory import Factory as DeploymentFactory

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")

args = parser.parse_args()

logger = ft_logger.Logger("sdnvpn-testcase-3").getLogger()

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig("testcase_3")


def main():
    results = Results(COMMON_CONFIG.line_length)
    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    # TODO unhardcode this to work with apex
    deploymentHandler = DeploymentFactory.get_handler(
        'fuel',
        '10.20.0.2',
        'root',
        'r00tme')

    openstack_nodes = deploymentHandler.get_nodes()

    controllers = [node for node in openstack_nodes
                   if node.is_controller()]

    for controller in controllers:
        logger.info("Starting bgp speaker of controller at IP %s "
                    % controller.ip)

        logger.info("Checking if zrpc daemon is "
                    "runnning on the controller node")

        cmd = "systemctl status zrpcd"
        output = controller.run_cmd(cmd)

        if not output:
            logger.info("zrpc daemon is not runnning on the controller node")
        else:
            logger.info("zrpc daemon is runnning on the controller node")

        # TODO here we need the external ip of the controller
        cmd_start_quagga = '/opt/opendaylight/bin/client "odl:configure-bgp ' \
        '-op start-bgp-server --as-num 100 --router-id {0}"'.format(
            controller.ip)

        # output_start_quagga =
        controller.run_cmd(cmd_start_quagga)

        logger.info("Checking if bgpd daemon is runnning"
                    " on the controller node")

        output_bgpd = controller.run_cmd(
            "ps --no-headers -C bgpd -o args,state")

        if not output_bgpd:
            logger.info("bgpd daemon is not runnning on the controller node")
        else:
            logger.info("bgpd daemon is runnning on the controller node")

        # TODO stop bgpd


if __name__ == '__main__':
    main()
