#!/usr/bin/python
#
# Copyright (c) 2015 All rights reserved
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
#   - Verify that the OpenDaylight and functest Quaggas peer
# - Exchange routing information with Quagga:
#   - Create a network, instance and BGPVPN in OpenStack
#   - Verify the route to the instance is present in the OpenDaylight FIB
#   - Verify that the functest Quagga also learns these routes
import os

import quagga
import utils as test_utils
from results import Results
import config as sdnvpn_config

import functest.utils.openstack_utils as os_utils
import functest.utils.functest_utils as ft_utils
import functest.utils.functest_logger as ft_logger


COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig("testcase_3")

logger = ft_logger.Logger("sdnvpn-testcase-3").getLogger()

LINE_LENGTH = 90

CONTROLLER_IP = test_utils.get_controller_ip()


def main():
    results = Results(LINE_LENGTH)
    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    # Taken from the sfc tests
    if not os.path.isfile(COMMON_CONFIG.ubuntu_image_path):
        logger.info("Downloading image")
        ft_utils.download_url(
            "http://artifacts.opnfv.org/sfc/demo/sf_nsh_colorado.qcow2",
            "/home/opnfv/functest/data/")
    else:
        logger.info("Using old image")

    glance_client = os_utils.get_glance_client()
    neutron_client = os_utils.get_neutron_client()

    sg_id = os_utils.create_security_group_full(neutron_client,
                                                TESTCASE_CONFIG.secgroup_name,
                                                TESTCASE_CONFIG.secgroup_descr)
    test_utils.open_icmp_ssh(neutron_client, sg_id)
    net_id, _, _ = test_utils.create_network(neutron_client,
                                             TESTCASE_CONFIG.net_1_name,
                                             TESTCASE_CONFIG.subnet_1_name,
                                             TESTCASE_CONFIG.subnet_1_cidr,
                                             TESTCASE_CONFIG.router_1_name)

    quagga_net_id, _, _ = test_utils.create_network(
        neutron_client,
        TESTCASE_CONFIG.quagga_net_name,
        TESTCASE_CONFIG.quagga_subnet_name,
        TESTCASE_CONFIG.quagga_subnet_cidr,
        TESTCASE_CONFIG.quagga_router_name)

    ubuntu_image_id = os_utils.create_glance_image(
        glance_client,
        COMMON_CONFIG.ubuntu_image_name,
        COMMON_CONFIG.ubuntu_image_path,
        disk="qcow2",
        container="bare",
        public=True)

    test_name = "Set up stand-alone Quagga"
    results.add_subtest(
        test_name,
        quagga.create_quagga_vm(CONTROLLER_IP,
                                sg_id,
                                quagga_net_id,
                                ubuntu_image_id,
                                TESTCASE_CONFIG))

    results.add_to_summary(0, "=")

    logger.info("\n%s" % results.summary)


if __name__ == '__main__':
    main()
