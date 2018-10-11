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
import time

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
    conn = os_utils.get_os_connection()
    results = Results(COMMON_CONFIG.line_length, conn)
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
    health_cmd = "sudo docker ps -f name=opendaylight_api -f " \
                 "health=healthy -q"
    if installer_type in ["fuel"]:
        odl_nodes = [node for node in openstack_nodes
                     if "running" in node.run_cmd(fuel_cmd)]
    elif installer_type in ["apex"]:
        odl_nodes = [node for node in openstack_nodes
                     if node.run_cmd(health_cmd)
                     if "Running" in node.run_cmd(apex_cmd)]
    else:
        logger.error("Incompatible installer type")

    computes = [node for node in openstack_nodes if node.is_compute()]

    msg = ("Verify that OpenDaylight can start/communicate with zrpcd/Quagga")
    results.record_action(msg)
    results.add_to_summary(0, "-")
    if not odl_nodes:
        msg = ("ODL node list is empty. Skipping rest of tests.")
        logger.info(msg)
        results.add_failure(msg)
        return results.compile_summary()
    else:
        msg = ("ODL node list is ready")
        logger.info(msg)
        results.add_success(msg)

    logger.info("Checking if zrpcd is "
                "running on the opendaylight nodes")

    for odl_node in odl_nodes:
        output_zrpcd = odl_node.run_cmd("ps --no-headers -C "
                                        "zrpcd -o state")
        states = output_zrpcd.split()
        running = any([s != 'Z' for s in states])
        msg = ("zrpcd is running in {name}".format(name=odl_node.name))

        if not running:
            logger.info("zrpcd is not running on the opendaylight node {name}"
                        .format(name=odl_node.name))
            results.add_failure(msg)
        else:
            logger.info("zrpcd is running on the opendaylight node {name}"
                        .format(name=odl_node.name))
            results.add_success(msg)

        results.add_to_summary(0, "-")

    # Find the BGP entity owner in ODL because of this bug:
    # https://jira.opendaylight.org/browse/NETVIRT-1308
    msg = ("Found BGP entity owner")
    odl_node = test_utils.get_odl_bgp_entity_owner(odl_nodes)
    if odl_node is None:
        logger.error("Failed to find the BGP entity owner")
        results.add_failure(msg)
    else:
        logger.info('BGP entity owner is {name}'
                    .format(name=odl_node.name))
        results.add_success(msg)
    results.add_to_summary(0, "-")

    installer_type = str(os.environ['INSTALLER_TYPE'].lower())
    if installer_type in ['apex']:
        odl_interface = 'br-ex'
    elif installer_type in ['fuel']:
        odl_interface = 'br-ctl'
    else:
        logger.error("Incompatible installer type")
    odl_ip, odl_netmask = test_utils.get_node_ip_and_netmask(
        odl_node, odl_interface)

    logger.info("Starting bgp speaker of opendaylight node at IP %s "
                % odl_ip)

    # Ensure that ZRPCD ip & port are well configured within ODL
    add_client_conn_to_bgp = "bgp-connect -p 7644 -h 127.0.0.1 add"
    test_utils.run_odl_cmd(odl_node, add_client_conn_to_bgp)

    # Start bgp daemon
    start_quagga = "odl:configure-bgp -op start-bgp-server " \
                   "--as-num 100 --router-id {0}".format(odl_ip)
    test_utils.run_odl_cmd(odl_node, start_quagga)

    # we need to wait a bit until the bgpd is up
    time.sleep(5)

    logger.info("Checking if bgpd is running on the opendaylight node")

    # Check if there is a non-zombie bgpd process
    output_bgpd = odl_node.run_cmd("ps --no-headers -C "
                                   "bgpd -o state")
    states = output_bgpd.split()
    running = any([s != 'Z' for s in states])

    msg = ("bgpd is running")
    if not running:
        logger.info("bgpd is not running on the opendaylight node")
        results.add_failure(msg)
    else:
        logger.info("bgpd is running on the opendaylight node")
        results.add_success(msg)

    results.add_to_summary(0, "-")

    # We should be able to restart the speaker
    # but the test is disabled because of buggy upstream
    # https://github.com/6WIND/zrpcd/issues/15
    # stop_quagga = 'odl:configure-bgp -op stop-bgp-server'
    # test_utils.run_odl_cmd(odl_node, stop_quagga)

    # logger.info("Checking if bgpd is still running"
    #             " on the opendaylight node")

    # output_bgpd = odl_node.run_cmd("ps --no-headers -C " \
    #                                "bgpd -o state")
    # states = output_bgpd.split()
    # running = any([s != 'Z' for s in states])

    # msg = ("bgpd is stopped")
    # if not running:
    #     logger.info("bgpd is not running on the opendaylight node")
    #     results.add_success(msg)
    # else:
    #     logger.info("bgpd is still running on the opendaylight node")
    #     results.add_failure(msg)

    # Taken from the sfc tests
    if not os.path.isfile(COMMON_CONFIG.ubuntu_image_path):
        logger.info("Downloading image")
        image_dest_path = '/'.join(
            COMMON_CONFIG.ubuntu_image_path.split('/')[:-1])
        os_utils.download_url(
            "http://artifacts.opnfv.org/sdnvpn/"
            "ubuntu-16.04-server-cloudimg-amd64-disk1.img",
            image_dest_path)
    else:
        logger.info("Using old image")

    neutron_client = os_utils.get_neutron_client()

    (floatingip_ids, instance_ids, router_ids, network_ids, image_ids,
     subnet_ids, interfaces, bgpvpn_ids, flavor_ids) = ([] for i in range(9))
    quagga_vm = None
    fake_fip = None

    try:
        _, flavor_id = test_utils.create_custom_flavor()
        flavor_ids.append(flavor_id)

        sg_id = os_utils.create_security_group_full(
            conn, TESTCASE_CONFIG.secgroup_name,
            TESTCASE_CONFIG.secgroup_descr)
        test_utils.open_icmp(conn, sg_id)
        test_utils.open_http_port(conn, sg_id)

        test_utils.open_bgp_port(conn, sg_id)

        image_id = os_utils.create_glance_image(
            conn, TESTCASE_CONFIG.image_name,
            COMMON_CONFIG.image_path, disk=COMMON_CONFIG.image_format,
            container="bare", public='public')
        image_ids.append(image_id)

        net_1_id, subnet_1_id, router_1_id = test_utils.create_network(
            conn,
            TESTCASE_CONFIG.net_1_name,
            TESTCASE_CONFIG.subnet_1_name,
            TESTCASE_CONFIG.subnet_1_cidr,
            TESTCASE_CONFIG.router_1_name)

        quagga_net_id, subnet_quagga_id, \
            router_quagga_id = test_utils.create_network(
                conn,
                TESTCASE_CONFIG.quagga_net_name,
                TESTCASE_CONFIG.quagga_subnet_name,
                TESTCASE_CONFIG.quagga_subnet_cidr,
                TESTCASE_CONFIG.quagga_router_name)

        interfaces.append(tuple((router_1_id, subnet_1_id)))
        interfaces.append(tuple((router_quagga_id, subnet_quagga_id)))
        network_ids.extend([net_1_id, quagga_net_id])
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
            conn,
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
        # fake_fip is needed to bypass NAT
        # see below for the reason why.
        fake_fip = os_utils.create_floating_ip(conn)
        # pin quagga to some compute
        floatingip_ids.append(fake_fip['fip_id'])
        compute_node = conn.compute.hypervisors().next()
        compute_node = conn.compute.get_hypervisor(compute_node)
        quagga_compute_node = "nova:" + compute_node.name
        # Map the hypervisor used above to a compute handle
        # returned by releng's manager
        for comp in computes:
            if compute_node.host_ip in comp.run_cmd("sudo ip a"):
                compute = comp
                break
        quagga_bootstrap_script = quagga.gen_quagga_setup_script(
            odl_ip,
            fake_fip['fip_addr'],
            odl_netmask,
            TESTCASE_CONFIG.external_network_ip_prefix,
            TESTCASE_CONFIG.route_distinguishers,
            TESTCASE_CONFIG.import_targets,
            TESTCASE_CONFIG.export_targets)

        quagga_vm = test_utils.create_instance(
            conn,
            TESTCASE_CONFIG.quagga_instance_name,
            ubuntu_image_id,
            quagga_net_id,
            sg_id,
            fixed_ip=TESTCASE_CONFIG.quagga_instance_ip,
            flavor=COMMON_CONFIG.custom_flavor_name,
            userdata=quagga_bootstrap_script,
            compute_node=quagga_compute_node)

        instance_ids.append(quagga_vm.id)

        quagga_vm_port = test_utils.get_port(conn,
                                             quagga_vm.id)
        fip_added = os_utils.attach_floating_ip(conn,
                                                quagga_vm_port.id)

        msg = ("Assign a Floating IP to %s " %
               TESTCASE_CONFIG.quagga_instance_name)
        if fip_added:
            results.add_success(msg)
            floatingip_ids.append(fip_added.id)
        else:
            results.add_failure(msg)

        test_utils.attach_instance_to_ext_br(quagga_vm, compute)

        testcase = "Bootstrap quagga inside an OpenStack instance"
        cloud_init_success = test_utils.wait_for_cloud_init(conn, quagga_vm)
        if cloud_init_success:
            results.add_success(testcase)
        else:
            results.add_failure(testcase)
        results.add_to_summary(0, "=")

        results.add_to_summary(0, '-')
        results.add_to_summary(1, "Peer Quagga with OpenDaylight")
        results.add_to_summary(0, '-')

        neighbor = quagga.odl_add_neighbor(fake_fip['fip_addr'],
                                           odl_ip,
                                           odl_node)
        peer = quagga.check_for_peering(odl_node)

        if neighbor and peer:
            results.add_success("Peering with quagga")
        else:
            results.add_failure("Peering with quagga")

        test_utils.add_quagga_external_gre_end_point(odl_nodes,
                                                     fake_fip['fip_addr'])
        test_utils.wait_before_subtest()

        msg = ("Create VPN to define a VRF")
        results.record_action(msg)
        vpn_name = vpn_name = "sdnvpn-3"
        kwargs = {
            "import_targets": TESTCASE_CONFIG.import_targets,
            "export_targets": TESTCASE_CONFIG.export_targets,
            "route_targets": TESTCASE_CONFIG.route_targets,
            "route_distinguishers": TESTCASE_CONFIG.route_distinguishers,
            "name": vpn_name
        }
        bgpvpn = test_utils.create_bgpvpn(neutron_client, **kwargs)
        bgpvpn_id = bgpvpn['bgpvpn']['id']
        logger.debug("VPN1 created details: %s" % bgpvpn)
        bgpvpn_ids.append(bgpvpn_id)

        msg = ("Associate network '%s' to the VPN." %
               TESTCASE_CONFIG.net_1_name)
        results.record_action(msg)
        results.add_to_summary(0, "-")

        # create a vm and connect it with network1,
        # which is going to be bgpvpn associated
        userdata_common = test_utils.generate_ping_userdata(
            [TESTCASE_CONFIG.external_network_ip])

        compute_node = conn.compute.hypervisors().next()
        av_zone_1 = "nova:" + compute_node.name
        vm_bgpvpn = test_utils.create_instance(
            conn,
            TESTCASE_CONFIG.instance_1_name,
            image_id,
            net_1_id,
            sg_id,
            fixed_ip=TESTCASE_CONFIG.instance_1_ip,
            secgroup_name=TESTCASE_CONFIG.secgroup_name,
            compute_node=av_zone_1,
            userdata=userdata_common)
        instance_ids.append(vm_bgpvpn.id)

        # wait for VM to get IP
        instance_up = test_utils.wait_for_instances_get_dhcp(vm_bgpvpn)
        if not instance_up:
            logger.error("One or more instances are down")

        test_utils.create_network_association(
            neutron_client, bgpvpn_id, net_1_id)

        test_utils.wait_before_subtest()

        msg = ("External IP prefix %s is exchanged with ODL"
               % TESTCASE_CONFIG.external_network_ip_prefix)
        fib_added = test_utils.is_fib_entry_present_on_odl(
            odl_nodes,
            TESTCASE_CONFIG.external_network_ip_prefix,
            TESTCASE_CONFIG.route_distinguishers)
        if fib_added:
            results.add_success(msg)
        else:
            results.add_failure(msg)

        # TODO: uncomment the following once OVS is installed with > 2.8.3 and
        # underlay connectivity is established between vxlan overlay and
        # external network.
        # results.get_ping_status_target_ip(
        #    vm_bgpvpn,
        #    TESTCASE_CONFIG.external_network_name,
        #    TESTCASE_CONFIG.external_network_ip,
        #    expected="PASS",
        #    timeout=300)

        results.add_to_summary(0, "=")
        logger.info("\n%s" % results.summary)

    except Exception as e:
        logger.error("exception occurred while executing testcase_3: %s", e)
        raise
    finally:
        if quagga_vm is not None:
            test_utils.detach_instance_from_ext_br(quagga_vm, compute)
        test_utils.cleanup_nova(conn, instance_ids, flavor_ids)
        test_utils.cleanup_glance(conn, image_ids)
        test_utils.cleanup_neutron(conn, neutron_client, floatingip_ids,
                                   bgpvpn_ids, interfaces, subnet_ids,
                                   router_ids, network_ids)
        if fake_fip is not None:
            bgp_nbr_disconnect_cmd = ("bgp-nbr -i %s -a 200 del"
                                      % fake_fip['fip_addr'])
            test_utils.run_odl_cmd(odl_node, bgp_nbr_disconnect_cmd)
        bgp_server_stop_cmd = ("bgp-rtr -r %s -a 100 del"
                               % odl_ip)
        odl_zrpc_disconnect_cmd = "bgp-connect -p 7644 -h 127.0.0.1 del"
        test_utils.run_odl_cmd(odl_node, bgp_server_stop_cmd)
        test_utils.run_odl_cmd(odl_node, odl_zrpc_disconnect_cmd)

    return results.compile_summary()


if __name__ == '__main__':
    sys.exit(main())
