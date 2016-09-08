"""Utilities for setting up quagga peering"""

import re
import time

import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils
import sdnvpn.lib.config as config
from sdnvpn.lib.utils import run_odl_cmd, exec_cmd

logger = ft_logger.Logger("sdnvpn-quagga").getLogger()

COMMON_CONFIG = config.CommonConfig()


def odl_add_neighbor(neighbor_ip, controller):
    command = 'configure-bgp -op add-neighbor --as-num 200'
    command += ' --ip %s --use-source-ip %s' % (neighbor_ip, controller.ip)
    success = run_odl_cmd(controller, command)
    return success


def bootstrap_quagga(fip_addr, controller_ip):
    script = gen_quagga_setup_script(
        controller_ip,
        fip_addr)
    cmd = "sshpass -popnfv ssh opnfv@%s << EOF %s EOF" % (fip_addr, script)
    rc = ft_utils.execute_command(cmd)
    return rc == 0


def gen_quagga_setup_script(controller_ip, instance_floating_ip):
    with open(COMMON_CONFIG.quagga_setup_script_path) as f:
        template = f.read()
    script = template % (controller_ip, instance_floating_ip)
    return script


def check_for_peering(controller):
    cmd = 'show-bgp --cmd "ip bgp neighbors"'
    tries = 90
    neighbors = None
    bgp_state_regex = re.compile("(BGP state =.*)")
    opens_regex = re.compile("Opens:(.*)")
    while not neighbors or 'Established' not in neighbors and tries > 0:
        neighbors = run_odl_cmd(controller, cmd)
        opens = opens_regex.search(neighbors)
        if opens:
            logger.debug("Opens sent/received: %s", opens.group(1))
        state = bgp_state_regex.search(neighbors)
        if state:
            logger.debug(state.group(1))
        tries -= 1
        time.sleep(2)

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
