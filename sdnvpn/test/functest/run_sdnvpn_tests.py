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
from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib.gather_logs import gather_logs

COMMON_CONFIG = sdnvpn_config.CommonConfig()


class SdnvpnFunctest(base.Feature):

    __logger = logging.getLogger(__name__)

    def execute(self):

        cmd_line = "neutron quota-update --subnet -1 --network -1 --port -1"
        self.__logger.info("Setting subnet/net quota to unlimited : %s"
                           % cmd_line)
        cmd = os.popen(cmd_line)
        output = cmd.read()
        self.__logger.debug(output)

        # Workaround for
        # https://jira.opnfv.org/projects/SDNVPN/issues/SDNVPN-115
        cmd_line = "nova quota-class-update --instances -1 default"
        self.__logger.info("Setting instances quota to unlimited : %s"
                           % cmd_line)
        cmd = os.popen(cmd_line)
        output = cmd.read()
        self.__logger.debug(output)

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

        try:
            gather_logs('overall')
        except Exception as ex:
            self.__logger.error(('Something went wrong in the Log gathering.'
                                 'Ex: %s, Trace: %s')
                                % ex, traceback.format_exc())

        if overall_status == "PASS":
            self.result = 100
            return base.Feature.EX_OK

        return base.Feature.EX_RUN_ERROR


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s'
                        '- %(levelname)s - %(message)s')
    SDNVPN = SdnvpnFunctest()
    sys.exit(SDNVPN.execute())
