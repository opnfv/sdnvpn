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
import os
import argparse

from sdnvpn.lib import quagga
import sdnvpn.lib.utils as test_utils
import sdnvpn.lib.config as sdnvpn_config

import functest.utils.openstack_utils as os_utils
import functest.utils.functest_utils as ft_utils
import functest.utils.functest_logger as ft_logger

from sdnvpn.lib.results import Results

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig("testcase_3")

logger = ft_logger.Logger("sdnvpn-testcase-3").getLogger()

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")

args = parser.parse_args()


def main():
    results = Results(COMMON_CONFIG.line_length)
    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    openstack_nodes = test_utils.get_nodes()

    # node.is_odl() doesn't work in Apex
    # https://jira.opnfv.org/browse/RELENG-192
    controllers = [node for node in openstack_nodes
                   if "running" in
                   node.run_cmd("sudo systemctl status opendaylight")]
    computes = [node for node in openstack_nodes if node.is_compute()]

    msg = ("Verify that OpenDaylight can start/communicate with zrpcd/Quagga")
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

    controller = controllers[0]  # We don't handle HA well
    get_ext_ip_cmd = "sudo ip a | grep br-ex | grep inet | awk '{print $2}'"
    ext_net_cidr = controller.run_cmd(get_ext_ip_cmd).strip().split('\n')
    ext_net_mask = ext_net_cidr[0].split('/')[1]
    controller_ext_ip = ext_net_cidr[0].split('/')[0]

    logger.info("Starting bgp speaker of controller at IP %s "
                % controller_ext_ip)
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

    start_quagga = "odl:configure-bgp -op start-bgp-server " \
                   "--as-num 100 --router-id {0}".format(controller_ext_ip)
    test_utils.run_odl_cmd(controller, start_quagga)

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

    # We should be able to restart the speaker
    # but the test is disabled because of buggy upstream
    # https://github.com/6WIND/zrpcd/issues/15
    # stop_quagga = 'odl:configure-bgp -op stop-bgp-server'
    # test_utils.run_odl_cmd(controller, stop_quagga)

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

    # Taken from the sfc tests
    if not os.path.isfile(COMMON_CONFIG.ubuntu_image_path):
        logger.info("Downloading image")
        ft_utils.download_url(
            "http://artifacts.opnfv.org/sdnvpn/"
            "ubuntu-16.04-server-cloudimg-amd64-disk1.img",
            "/home/opnfv/functest/data/")
    else:
        logger.info("Using old image")

    glance_client = os_utils.get_glance_client()
    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()

    sg_id = os_utils.create_security_group_full(neutron_client,
                                                TESTCASE_CONFIG.secgroup_name,
                                                TESTCASE_CONFIG.secgroup_descr)
    test_utils.open_icmp(neutron_client, sg_id)
    test_utils.open_http_port(neutron_client, sg_id)

    test_utils.open_bgp_port(neutron_client, sg_id)
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

    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    if installer_type == "fuel":
        disk = 'raw'
    elif installer_type == "apex":
        disk = 'qcow2'
    else:
        logger.error("Incompatible installer type")

    ubuntu_image_id = os_utils.create_glance_image(
        glance_client,
        COMMON_CONFIG.ubuntu_image_name,
        COMMON_CONFIG.ubuntu_image_path,
        disk,
        container="bare",
        public="public")

    # NOTE(rski) The order of this seems a bit weird but
    # there is a reason for this, namely
    # https://jira.opnfv.org/projects/SDNVPN/issues/SDNVPN-99
    # so we create the quagga instance using cloud-init
    # and immediately give it a floating IP.
    # The cloud-init script should contain a small sleep for
    # this to work.
    # We also create the FIP first because it is used in the
    # cloud-init script.
    fip = os_utils.create_floating_ip(neutron_client)
    # fake_fip is needed to bypass NAT
    # see below for the reason why.
    fake_fip = os_utils.create_floating_ip(neutron_client)
    # pin quagga to some compute
    compute_node = nova_client.hypervisors.list()[0]
    quagga_compute_node = "nova:" + compute_node.hypervisor_hostname
    # Map the hypervisor used above to a compute handle
    # returned by releng's manager
    for comp in computes:
        if compute_node.host_ip in comp.run_cmd("sudo ip a"):
            compute = comp
            break
    quagga_bootstrap_script = quagga.gen_quagga_setup_script(
        controller_ext_ip,
        fake_fip['fip_addr'],
        ext_net_mask)

    test_utils.create_custom_flavor()

    quagga_vm = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.quagga_instance_name,
        ubuntu_image_id,
        quagga_net_id,
        sg_id,
        fixed_ip=TESTCASE_CONFIG.quagga_instance_ip,
        flavor=COMMON_CONFIG.custom_flavor_name,
        userdata=quagga_bootstrap_script,
        compute_node=quagga_compute_node)

    fip_added = os_utils.add_floating_ip(nova_client,
                                         quagga_vm.id,
                                         fip['fip_addr'])

    msg = "Assign a Floating IP to %s " % TESTCASE_CONFIG.quagga_instance_name
    if fip_added:
        results.add_success(msg)
    else:
        results.add_failure(msg)

    test_utils.attach_instance_to_ext_br(quagga_vm, compute)

    testcase = "Bootstrap quagga inside an OpenStack instance"
    cloud_init_success = test_utils.wait_for_cloud_init(quagga_vm)
    if cloud_init_success:
        results.add_success(testcase)
    else:
        results.add_failure(testcase)
    results.add_to_summary(0, "=")

    results.add_to_summary(0, '-')
    results.add_to_summary(1, "Peer Quagga with OpenDaylight")
    results.add_to_summary(0, '-')

    neighbor = quagga.odl_add_neighbor(fake_fip['fip_addr'],
                                       controller_ext_ip,
                                       controller)
    peer = quagga.check_for_peering(controller)

    test_utils.detach_instance_from_ext_br(quagga_vm, compute)

    if neighbor and peer:
        results.add_success("Peering with quagga")
    else:
        results.add_failure("Peering with quagga")

    return results.compile_summary()


if __name__ == '__main__':
    main()
