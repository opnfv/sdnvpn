#!/usr/bin/python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0

import yaml
import os

from functest.utils.constants import CONST
import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils

logger = ft_logger.Logger("sndvpn_test_config").getLogger()


class CommonConfig(object):
    """
    Common configuration parameters across testcases
    """
    def __init__(self):
        self.repo_path = CONST.dir_repo_sdnvpn
        self.config_file = os.path.join(self.repo_path,
                                        'sdnvpn/test/functest/config.yaml')
        self.keyfile_path = os.path.join(self.repo_path,
                                         'sdnvpn/artifacts/id_rsa')
        self.test_db = CONST.results_test_db_url
        self.quagga_setup_script_path = os.path.join(
            self.repo_path,
            "sdnvpn/artifacts/quagga_setup.sh")
        self.line_length = 90  # length for the summary table
        self.vm_boot_timeout = 180
        self.default_flavor = ft_utils.get_parameter_from_yaml(
            "defaults.flavor", self.config_file)
        self.image_filename = CONST.openstack_image_file_name
        self.image_format = CONST.openstack_image_disk_format
        self.image_path = '{0}/{1}'.format(CONST.dir_functest_data,
                                           self.image_filename)
        # This is the ubuntu image used by sfc
        # Basically vanilla ubuntu + some scripts in there
        # We can use it to setup a quagga instance
        # TODO does functest have an ubuntu image somewhere?
        self.ubuntu_image_name = "sdnvpn-ubuntu"
        self.ubuntu_image_path = '{0}/{1}'.format(
            CONST.dir_functest_data,
            "ubuntu-16.04-server-cloudimg-amd64-disk1.img")
        self.custom_flavor_name = 'm1.custom'
        self.custom_flavor_ram = 1024
        self.custom_flavor_disk = 10
        self.custom_flavor_vcpus = 1


class TestcaseConfig(object):
    """
    Configuration for a testcase.
    Parse config.yaml into a dict and create an object out of it.
    """

    def __init__(self, testcase):
        common_config = CommonConfig()
        test_config = None
        with open(common_config.config_file) as f:
            testcases_yaml = yaml.safe_load(f)
            test_config = testcases_yaml['testcases'].get(testcase, None)
        if test_config is None:
            logger.error('Test {0} configuration is not present in {1}'
                         .format(testcase, common_config.config_file))
        # Update class fields with configuration variables dynamically
        self.__dict__.update(**test_config)
