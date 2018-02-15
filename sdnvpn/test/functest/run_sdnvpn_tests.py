#!/bin/python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

import importlib
import logging
import os
import sys
import traceback
import yaml

from functest.core import feature as base
from functest.utils import openstack_utils as os_utils
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib.gather_logs import gather_logs
from sdnvpn.lib import utils as test_utils

COMMON_CONFIG = sdnvpn_config.CommonConfig()


class SdnvpnFunctest(base.Feature):

    __logger = logging.getLogger(__name__)

    def execute(self):

        nova_client = os_utils.get_nova_client()
        neutron_client = os_utils.get_neutron_client()

        tenant_id = os_utils.get_tenant_id(os_utils.get_keystone_client(),
                                           os.environ['OS_PROJECT_NAME'])

        neutron_quota = test_utils.get_neutron_quota(neutron_client, tenant_id)
        (neutron_nw_quota, neutron_subnet_quota, neutron_port_quota,
         neutron_router_quota) = (
            neutron_quota['network'], neutron_quota['subnet'],
            neutron_quota['port'], neutron_quota['router'])
        instances_quota = test_utils.get_nova_instances_quota(nova_client)

        self.__logger.info("Setting net/subnet/port/router "
                           "quota to unlimited")
        test_utils.update_nw_subnet_port_quota(
            neutron_client,
            tenant_id,
            COMMON_CONFIG.neutron_nw_quota,
            COMMON_CONFIG.neutron_subnet_quota,
            COMMON_CONFIG.neutron_port_quota,
            COMMON_CONFIG.neutron_router_quota)
        test_utils.create_default_flavor()

        # Workaround for
        # https://jira.opnfv.org/projects/SDNVPN/issues/SDNVPN-115
        self.__logger.info("Setting instances quota class to unlimited")
        test_utils.update_instance_quota_class(
            nova_client,
            COMMON_CONFIG.nova_instances_quota_class)

        with open(COMMON_CONFIG.config_file) as f:
            config_yaml = yaml.safe_load(f)

        testcases = config_yaml.get("testcases")
        overall_status = "PASS"
        for tc in testcases:
            if testcases[tc]['enabled']:
                test_name = tc
                test_descr = testcases[tc]['description']
                title = ("Running '%s - %s'" %
                         (test_name, test_descr))
                self.__logger.info(title)
                self.__logger.info("%s\n" % ("=" * len(title)))
                t = importlib.import_module(test_name, package=None)
                try:
                    result = t.main()
                except Exception as ex:
                    result = -1
                    self.__logger.info("Caught Exception in %s: %s Trace: %s"
                                       % (test_name, ex,
                                          traceback.format_exc()))
                if result < 0:
                    status = "FAIL"
                    overall_status = "FAIL"
                    self.__logger.info("Testcase %s failed" % test_name)
                else:
                    status = result.get("status")
                    self.details.update(
                        {test_name: {'status': status,
                                     'details': result.get("details")}})
                    self.__logger.info("Results of test case '%s - %s':\n%s\n"
                                       % (test_name, test_descr, result))

                    if status == "FAIL":
                        overall_status = "FAIL"

        self.__logger.info("Resetting subnet/net/port quota")
        test_utils.update_nw_subnet_port_quota(neutron_client,
                                               tenant_id,
                                               neutron_nw_quota,
                                               neutron_subnet_quota,
                                               neutron_port_quota,
                                               neutron_router_quota)

        self.__logger.info("Resetting instances quota class")
        test_utils.update_instance_quota_class(nova_client, instances_quota)

        try:
            installer_type = str(os.environ['INSTALLER_TYPE'].lower())
            if installer_type in ["fuel", "apex"]:
                gather_logs('overall')
            else:
                self.__logger.info("Skipping log gathering because installer"
                                   "type %s is neither fuel nor apex" %
                                   installer_type)
        except Exception as ex:
            self.__logger.error(('Something went wrong in the Log gathering.'
                                 'Ex: %s, Trace: %s')
                                % (ex, traceback.format_exc()))

        if overall_status == "PASS":
            self.result = 100
            return base.Feature.EX_OK

        return base.Feature.EX_RUN_ERROR


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s'
                        '- %(levelname)s - %(message)s')
    SDNVPN = SdnvpnFunctest()
    sys.exit(SDNVPN.execute())
