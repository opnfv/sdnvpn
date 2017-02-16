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
# from sdnvpn.lib import utils as test_utils
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib.results import Results
from opnfv.deployment.factory import Factory as DeploymentFactory
import sys

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

    deploymentHandler = DeploymentFactory.get_handler(
        COMMON_CONFIG.installer_type,
        COMMON_CONFIG.installer_ip,
        COMMON_CONFIG.installer_user,
        installer_pwd=COMMON_CONFIG.installer_password)

    cluster = COMMON_CONFIG.installer_cluster
    openstack_nodes = (deploymentHandler.get_nodes({'cluster': cluster})
                       if cluster is not None
                       else deploymentHandler.get_nodes())

    controller_nodes = [node for node in openstack_nodes
                        if node.is_controller()]

    for obj in controller_nodes:
        print("OBJECT CONTROLLER IS: %s" % obj)
        if hasattr(obj, 'ip'):
            controller_ip = obj.ip
        else:
            logger.info('There is no controller ip. Exiting')
            sys.exit(1)

        logger.info("Check if zrpc daemon is runnning on the controller node")

        cmd = "ps --no-headers -C zrpcd -o args,state"
        output = obj.run_cmd(cmd)

        if not output:
            logger.info("zrpc daemon is not runnning on the controller node")
        else:
            logger.info("zrpc daemon is runnning on the controller node")

        cmd_start_quagga = '/opt/opendaylight/bin/client "odl:configure-bgp '
        '-op start-bgp-server --as-num 100 --router-id {0}"'.format(
            controller_ip)

        # output_start_quagga =
        obj.run_cmd(cmd_start_quagga)

        cmd_bgpd = "ps --no-headers -C bgpd -o args,state"
        logger.info("Check if bgpd daemon is runnning on the controller node")

        output_bgpd = obj.run_cmd(cmd_bgpd)

        if not output_bgpd:
            logger.info("bgpd daemon is not runnning on the controller node")
        else:
            logger.info("bgpd daemon is runnning on the controller node")


if __name__ == '__main__':
    main()
