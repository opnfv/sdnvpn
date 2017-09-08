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
import logging
import re
import sys
import time
import traceback

from functest.utils import openstack_utils as os_utils
from multiprocessing import Process, Manager, Lock
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import utils as test_utils
from sdnvpn.lib.results import Results

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")

args = parser.parse_args()

logger = logging.getLogger('__name__')

std_out_lock = Lock()

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.testcase_10')


def monitor(in_data, out_data, vm):
    # At the beginning of ping we might have some
    # failures, so we ignore the first 10 pings
    lines_offset = 10
    while in_data["stop_thread"] is False:
        try:
            time.sleep(1)
            vm_console_out_lines = vm.get_console_output().split('\n')
            if lines_offset < len(vm_console_out_lines):
                for console_line in vm_console_out_lines[lines_offset:-1]:
                    is_ping_error = re.match(r'ping.*KO', console_line)
                    if is_ping_error and out_data["error_msg"] == "":
                        out_data["error_msg"] += ("Ping failure from "
                                                  "instance {}".
                                                  format(vm.name))
                        # Atomic write to std out
                        with std_out_lock:
                            logging.error("Failure during ping from "
                                          "instance {}: {}".
                                          format(vm.name, console_line))
                    elif re.match(r'ping.*OK', console_line):
                        # Atomic write to std out
                        with std_out_lock:
                            logging.info("Ping from instance {}: {}".
                                         format(vm.name, console_line))
                lines_offset = len(vm_console_out_lines)
        except:
            # Atomic write to std out
            with std_out_lock:
                logging.error("Failure in monitor_thread of instance {}".
                              format(vm.name))
    # Return to main process
    return


def main():
    results = Results(COMMON_CONFIG.line_length)

    results.add_to_summary(0, "=")
    results.add_to_summary(2, "STATUS", "SUBTEST")
    results.add_to_summary(0, "=")

    nova_client = os_utils.get_nova_client()
    neutron_client = os_utils.get_neutron_client()
    glance_client = os_utils.get_glance_client()

    (floatingip_ids, instance_ids, router_ids, network_ids, image_ids,
     subnet_ids, interfaces, bgpvpn_ids) = ([] for i in range(8))
    image_id = os_utils.create_glance_image(glance_client,
                                            TESTCASE_CONFIG.image_name,
                                            COMMON_CONFIG.image_path,
                                            disk=COMMON_CONFIG.image_format,
                                            container="bare",
                                            public='public')
    image_ids.append(image_id)

    network_1_id = test_utils.create_net(neutron_client,
                                         TESTCASE_CONFIG.net_1_name)
    subnet_1_id = test_utils.create_subnet(neutron_client,
                                           TESTCASE_CONFIG.subnet_1_name,
                                           TESTCASE_CONFIG.subnet_1_cidr,
                                           network_1_id)

    network_ids.append(network_1_id)
    subnet_ids.append(subnet_1_id)

    sg_id = os_utils.create_security_group_full(neutron_client,
                                                TESTCASE_CONFIG.secgroup_name,
                                                TESTCASE_CONFIG.secgroup_descr)

    compute_nodes = test_utils.assert_and_get_compute_nodes(nova_client)
    av_zone_1 = "nova:" + compute_nodes[0]
    av_zone_2 = "nova:" + compute_nodes[1]

    # boot INSTANCES
    vm_2 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_2_name,
        image_id,
        network_1_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1)
    vm2_ip = test_utils.get_instance_ip(vm_2)

    u1 = test_utils.generate_ping_userdata([vm2_ip], 1)
    vm_1 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_1_name,
        image_id,
        network_1_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_1,
        userdata=u1)
    vm1_ip = test_utils.get_instance_ip(vm_1)

    u3 = test_utils.generate_ping_userdata([vm1_ip, vm2_ip], 1)
    vm_3 = test_utils.create_instance(
        nova_client,
        TESTCASE_CONFIG.instance_3_name,
        image_id,
        network_1_id,
        sg_id,
        secgroup_name=TESTCASE_CONFIG.secgroup_name,
        compute_node=av_zone_2,
        userdata=u3)
    vm3_ip = test_utils.get_instance_ip(vm_3)
    # We do not put vm_2 id in instance_ids table because we will
    # delete the current instance during the testing process
    instance_ids.extend([vm_1.id, vm_3.id])

    # Wait for VMs to get ips.
    instances_up = test_utils.wait_for_instances_up(vm_1, vm_2,
                                                    vm_3)

    if not instances_up:
        logger.error("One or more instances is down")
        # TODO: Handle this appropriately
    # Create monitor threads to monitor traffic between vm_1, vm_2 and vm_3
    m = Manager()
    monitor_input1 = m.dict()
    monitor_output1 = m.dict()
    monitor_input1["stop_thread"] = False
    monitor_output1["error_msg"] = ""
    monitor_thread1 = Process(target=monitor, args=(monitor_input1,
                                                    monitor_output1, vm_1,))
    monitor_input2 = m.dict()
    monitor_output2 = m.dict()
    monitor_input2["stop_thread"] = False
    monitor_output2["error_msg"] = ""
    monitor_thread2 = Process(target=monitor, args=(monitor_input2,
                                                    monitor_output2, vm_2,))
    monitor_input3 = m.dict()
    monitor_output3 = m.dict()
    monitor_input3["stop_thread"] = False
    monitor_output3["error_msg"] = ""
    monitor_thread3 = Process(target=monitor, args=(monitor_input3,
                                                    monitor_output3, vm_3,))
    # Lists of all monitor threads and their inputs and outputs.
    threads = [monitor_thread1, monitor_thread2, monitor_thread3]
    thread_inputs = [monitor_input1, monitor_input2, monitor_input3]
    thread_outputs = [monitor_output1, monitor_output2, monitor_output3]
    try:
        logging.info("Starting all monitor threads")
        # Start all monitor threads
        for thread in threads:
            thread.start()
        logging.info("Wait before subtest")
        test_utils.wait_before_subtest()
        monitor_err_msg = ""
        for thread_output in thread_outputs:
            if thread_output["error_msg"] != "":
                monitor_err_msg += " ,{}".format(thread_output["error_msg"])
                thread_output["error_msg"] = ""
        results.record_action("Check ping status of vm_1, vm_2, and vm_3")
        results.add_to_summary(0, "-")
        if len(monitor_err_msg) == 0:
            results.add_success("Ping succeeds")
        else:
            results.add_failure(monitor_err_msg)
        # Stop monitor thread 2 and delete instance vm_2
        thread_inputs[1]["stop_thread"] = True
        if not os_utils.delete_instance(nova_client, vm_2.id):
            logging.error("Fail to delete vm_2 instance during "
                          "testing process")
            raise Exception("Fail to delete instance vm_2.")
        # Create a new vm (vm_4) on compute 1 node
        u4 = test_utils.generate_ping_userdata([vm1_ip, vm3_ip], 1)
        vm_4 = test_utils.create_instance(
            nova_client,
            TESTCASE_CONFIG.instance_4_name,
            image_id,
            network_1_id,
            sg_id,
            secgroup_name=TESTCASE_CONFIG.secgroup_name,
            compute_node=av_zone_1,
            userdata=u4)
        instance_ids.append(vm_4.id)
        # Wait for VMs to get ips.
        instances_up = test_utils.wait_for_instances_up(vm_4)
        if not instances_up:
            logger.error("Instance vm_4 failed to start.")
            # TODO: Handle this appropriately
        # Create and start a new monitor thread for vm_4
        monitor_input4 = m.dict()
        monitor_output4 = m.dict()
        monitor_input4["stop_thread"] = False
        monitor_output4["error_msg"] = ""
        monitor_thread4 = Process(target=monitor, args=(monitor_input4,
                                                        monitor_output4,
                                                        vm_4,))
        threads.append(monitor_thread4)
        thread_inputs.append(monitor_input4)
        thread_outputs.append(monitor_output4)
        logging.info("Starting monitor thread of vm_4")
        threads[3].start()
        test_utils.wait_before_subtest()
        monitor_err_msg = ""
        for thread_output in thread_outputs:
            if thread_output["error_msg"] != "":
                monitor_err_msg += " ,{}".format(thread_output["error_msg"])
                thread_output["error_msg"] = ""
        results.record_action("Check ping status of vm_1, vm_3 and vm_4. "
                              "Instance vm_2 is deleted")
        results.add_to_summary(0, "-")
        if len(monitor_err_msg) == 0:
            results.add_success("Ping succeeds")
        else:
            results.add_failure(monitor_err_msg)

    except:
        logging.exception("======== EXCEPTION =========")
        exc_type, exc_value, exc_tb = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_tb)
    finally:
        # Give a stop signal to all threads
        logging.info("Sending stop signal to monitor thread")
        for thread_input in thread_inputs:
            thread_input["stop_thread"] = True
        # Wait for all threads to stop and return to the main process
        for thread in threads:
            thread.join()

    test_utils.cleanup_nova(nova_client, instance_ids, image_ids)
    test_utils.cleanup_neutron(neutron_client, floatingip_ids, bgpvpn_ids,
                               interfaces, subnet_ids, router_ids,
                               network_ids)

    return results.compile_summary()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
