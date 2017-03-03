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
from sdnvpn.lib import utils as test_utils

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

    deploymentHandler, openstack_nodes = test_utils.get_handler_nodes()

    controllers = [node for node in openstack_nodes
                   if node.is_odl()]

    msg = 'Verify that OpenDaylight can ' \
          'start/communicate with zrpcd/Quagga'
    results.record_action(msg)
    results.add_to_summary(0, "-")
    if not controllers:
        msg = ("Controller (ODL) list is empty")
        logger.info(msg)
        results.add_failure(msg)
    else:
        msg = ("Controller (ODL) list is ready")
        logger.info(msg)
        results.add_success(msg)

    for controller in controllers:
        logger.info("Starting bgp speaker of controller at IP %s "
                    % controller.ip)
        logger.info("Checking if zrpcd is "
                    "running on the controller node")

        cmd = "systemctl status zrpcd"
        output = controller.run_cmd(cmd)
        msg = ("zrpcd is running")

        if not output:
            logger.info("zrpcd is not running on the controller node")
            results.add_failure(msg)
        else:
            logger.info("zrpcd is running on the controller node")
            results.add_success(msg)

        results.add_to_summary(0, "-")

        # TODO here we need the external ip of the controller
        cmd_start_quagga = '/opt/opendaylight/bin/client ' \
                           '"odl:configure-bgp -op start-bgp-server ' \
                           '--as-num 100 ' \
                           '--router-id {0}"'.format(controller.ip)

        controller.run_cmd(cmd_start_quagga)

        logger.info("Checking if bgpd is running"
                    " on the controller node")

        # Check if there is a non-zombie bgpd process
        output_bgpd = controller.run_cmd("ps --no-headers -C "
                                         "bgpd -o state")
        states = output_bgpd.split()
        running = any([s != 'Z' for s in states])

        msg = ("bgpd is running")
        if not running:
            logger.info("bgpd is not running on the controller node")
            results.add_failure(msg)
        else:
            logger.info("bgpd is running on the controller node")
            results.add_success(msg)

        results.add_to_summary(0, "-")

        cmd_stop_quagga = '/opt/opendaylight/bin/client -v ' \
                          '"odl:configure -bgp -op stop-bgp-server"'

        controller.run_cmd(cmd_stop_quagga)

        # disabled because of buggy upstream
        # https://github.com/6WIND/zrpcd/issues/15
        # logger.info("Checking if bgpd is still running"
        #             " on the controller node")

        # output_bgpd = controller.run_cmd("ps --no-headers -C " \
        #                                  "bgpd -o state")
        # states = output_bgpd.split()
        # running = any([s != 'Z' for s in states])

        # msg = ("bgpd is stopped")
        # if not running:
        #     logger.info("bgpd is not running on the controller node")
        #     results.add_success(msg)
        # else:
        #     logger.info("bgpd is still running on the controller node")
        #     results.add_failure(msg)

    return results.compile_summary()


if __name__ == '__main__':
    main()
