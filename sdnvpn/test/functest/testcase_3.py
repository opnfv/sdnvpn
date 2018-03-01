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
import os
import sys

from sdnvpn.lib import quagga
from sdnvpn.lib import openstack_utils as os_utils
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib.results import Results


logger = logging.getLogger(__name__)

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    "sdnvpn.test.functest.testcase_3")


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

    output_zrpcd = controller.run_cmd("ps --no-headers -C "
                                      "zrpcd -o state")
    states = output_zrpcd.split()
    running = any([s != 'Z' for s in states])

    msg = ("zrpcd is running")

    if not running:
        logger.info("zrpcd is not running on the controller node")
        results.add_failure(msg)
    else:
        logger.info("zrpcd is running on the controller node")
        results.add_success(msg)

    results.add_to_summary(0, "-")

    # Ensure that ZRPCD ip & port are well configured within ODL
    add_client_conn_to_bgp = "bgp-connect -p 7644 -h 127.0.0.1 add"
    test_utils.run_odl_cmd(controller, add_client_conn_to_bgp)

    # Start bgp daemon
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
        os_utils.download_url(
            "http://artifacts.opnfv.org/sdnvpn/"
            "ubuntu-16.04-server-cloudimg-amd64-disk1.img",
            "/home/opnfv/functest/data/")
    else:
        logger.info("Using old image")

    glance_client = os_utils.get_glance_client()
    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()

    (floatingip_ids, instance_ids, router_ids, network_ids, image_ids,
     subnet_ids, interfaces, bgpvpn_ids, flavor_ids) = ([] for i in range(9))

    try:
        sg_id = os_utils.create_security_group_full(
            neutron_client, TESTCASE_CONFIG.secgroup_name,
            TESTCASE_CONFIG.secgroup_descr)
        test_utils.open_icmp(neutron_client, sg_id)
        test_utils.open_http_port(neutron_client, sg_id)

        test_utils.open_bgp_port(neutron_client, sg_id)
        net_id, subnet_1_id, router_1_id = test_utils.create_network(
            neutron_client,
            TESTCASE_CONFIG.net_1_name,
            TESTCASE_CONFIG.subnet_1_name,
            TESTCASE_CONFIG.subnet_1_cidr,
            TESTCASE_CONFIG.router_1_name)

        quagga_net_id, subnet_quagga_id, \
            router_quagga_id = test_utils.create_network(
                neutron_client,
                TESTCASE_CONFIG.quagga_net_name,
                TESTCASE_CONFIG.quagga_subnet_name,
                TESTCASE_CONFIG.quagga_subnet_cidr,
                TESTCASE_CONFIG.quagga_router_name)

        interfaces.append(tuple((router_1_id, subnet_1_id)))
        interfaces.append(tuple((router_quagga_id, subnet_quagga_id)))
        network_ids.extend([net_id, quagga_net_id])
        router_ids.extend([router_1_id, router_quagga_id])
        subnet_ids.extend([subnet_1_id, subnet_quagga_id])

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

        image_ids.append(ubuntu_image_id)

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

        floatingip_ids.extend([fip['fip_id'], fake_fip['fip_id']])
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

        _, flavor_id = test_utils.create_custom_flavor()
        flavor_ids.append(flavor_id)

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

        instance_ids.append(quagga_vm)

        fip_added = os_utils.add_floating_ip(nova_client,
                                             quagga_vm.id,
                                             fip['fip_addr'])

        msg = ("Assign a Floating IP to %s " %
               TESTCASE_CONFIG.quagga_instance_name)
        if fip_added:
            results.add_success(msg)
        else:
            results.add_failure(msg)
        test_utils.attach_instance_to_ext_br(quagga_vm, compute)

        try:
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

        finally:
            test_utils.detach_instance_from_ext_br(quagga_vm, compute)

        if neighbor and peer:
            results.add_success("Peering with quagga")
        else:
            results.add_failure("Peering with quagga")

    except Exception as e:
        logger.error("exception occurred while executing testcase_3: %s", e)
        raise
    finally:
        test_utils.cleanup_nova(nova_client, instance_ids, flavor_ids)
        test_utils.cleanup_glance(glance_client, image_ids)
        test_utils.cleanup_neutron(neutron_client, floatingip_ids,
                                   bgpvpn_ids, interfaces, subnet_ids,
                                   router_ids, network_ids)

    return results.compile_summary()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
