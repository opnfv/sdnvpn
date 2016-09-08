"""Utilities for setting up quagga peering"""

import os

import utils as test_utils
import functest.utils.functest_logger as ft_logger
import functest.utils.openstack_utils as os_utils
import config

logger = ft_logger.Logger("sdnvpn-quagga").getLogger()

COMMON_CONFIG = config.CommonConfig()
QUAGGA_SETUP_SCRIPT_TEMPLATE = os.path.join(COMMON_CONFIG.repo_path,
                                            'test',
                                            'functest',
                                            'quagga_setup.sh')


def create_quagga_vm(controller_ip,
                     sg_id,
                     quagga_net_id,
                     ubuntu_image_id,
                     test_config):
    """Setup quagga in an instance in the cloud"""
    nova_client = os_utils.get_nova_client()

    userdata = gen_quagga_setup_script(controller_ip,
                                       test_config.quagga_instance_ip)
    quagga_vm = test_utils.create_instance(
        nova_client,
        test_config.quagga_instance_name,
        ubuntu_image_id,
        quagga_net_id,
        sg_id,
        userdata=userdata,
        fixed_ip=test_config.quagga_instance_ip,
        flavor=test_config.quagga_instance_flavor)
    return quagga_vm


def gen_quagga_setup_script(controller_ip, instance_floating_ip):
    with open(QUAGGA_SETUP_SCRIPT_TEMPLATE) as f:
        template = f.read()
    script = template % (controller_ip, instance_floating_ip)
    return script
