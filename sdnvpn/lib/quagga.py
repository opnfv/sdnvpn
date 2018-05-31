#!/usr/bin/env python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
"""Utilities for setting up quagga peering"""

import logging
import re
import time

import functest.utils.functest_utils as ft_utils
import sdnvpn.lib.config as config
from sdnvpn.lib.utils import run_odl_cmd, exec_cmd

logger = logging.getLogger('sdnvpn-quagga')

COMMON_CONFIG = config.CommonConfig()


def odl_add_neighbor(neighbor_ip, controller_ip, controller):
    # Explicitly pass controller_ip because controller.ip
    # Might not be accessible from the Quagga instance
    command = 'configure-bgp -op add-neighbor --as-num 200'
    command += ' --ip %s --use-source-ip %s' % (neighbor_ip, controller_ip)
    success = run_odl_cmd(controller, command)
    # The run_cmd api is really whimsical
    logger.info("Maybe stdout of %s: %s", command, success)
    return success


def bootstrap_quagga(fip_addr, controller_ip):
    script = gen_quagga_setup_script(
        controller_ip,
        fip_addr)
    cmd = "sshpass -popnfv ssh opnfv@%s << EOF %s EOF" % (fip_addr, script)
    rc = ft_utils.execute_command(cmd)
    return rc == 0


def gen_quagga_setup_script(controller_ip,
                            fake_floating_ip,
                            ext_net_mask):
    with open(COMMON_CONFIG.quagga_setup_script_path) as f:
        template = f.read()
    script = template % (controller_ip,
                         fake_floating_ip,
                         ext_net_mask)
    return script


def check_for_peering(controller):
    cmd = 'show-bgp --cmd \\"ip bgp neighbors\\"'
    tries = 20
    neighbors = None
    bgp_state_regex = re.compile("(BGP state =.*)")
    opens_regex = re.compile("Opens:(.*)")
    while tries > 0:
        if neighbors and 'Established' in neighbors:
            break
        neighbors = run_odl_cmd(controller, cmd)
        logger.info("Output of %s: %s", cmd, neighbors)
        if neighbors:
            opens = opens_regex.search(neighbors)
            if opens:
                logger.info("Opens sent/received: %s", opens.group(1))
            state = bgp_state_regex.search(neighbors)
            if state:
                logger.info("Peering state: %s", state.group(1))
        tries -= 1
        time.sleep(1)

    if not neighbors or 'Established' not in neighbors:
        logger.error("Quagga failed to peer with OpenDaylight")
        logger.error("OpenDaylight status: %s", neighbors)
        return False

    logger.info("Quagga peered with OpenDaylight")
    return True


def check_for_route_exchange(ip):
    """Check that Quagga has learned the route to an IP"""
    logger.debug("Checking that '%s' is in the Zebra routing table", ip)
    routes, success = exec_cmd("vtysh -c 'show ip route'", verbose=True)
    if not success:
        return False
    logger.debug("Zebra routing table: %s", routes)
    return ip in routes
