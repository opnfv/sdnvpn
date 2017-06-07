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
import time
import traceback
import yaml

from functest.core import testcase
from sdnvpn.lib import config as sdnvpn_config

""" logging configuration """
logger = logging.getLogger(__name__)


COMMON_CONFIG = sdnvpn_config.CommonConfig()


class SdnvpnFunctest(testcase.TestCase):

    def run(self):
        self.start_time = time.time()

        cmd_line = "neutron quota-update --subnet -1 --network -1 --port -1"
        logger.info("Setting subnet/net quota to unlimited : %s" % cmd_line)
        cmd = os.popen(cmd_line)
        output = cmd.read()
        logger.debug(output)

        # Workaround for
        # https://jira.opnfv.org/projects/SDNVPN/issues/SDNVPN-115
        cmd_line = "nova quota-class-update --instances -1 default"
        logger.info("Setting instances quota to unlimited : %s" % cmd_line)
        cmd = os.popen(cmd_line)
        output = cmd.read()
        logger.debug(output)

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
                logger.info(title)
                logger.info("%s\n" % ("=" * len(title)))
                module = 'sdnvpn.test.functest.' + test_name
                t = importlib.import_module(module, package=None)
                try:
                    result = t.main()
                except Exception as ex:
                    result = -1
                    logger.info("Caught Exception in %s: %s Trace: %s" %
                                (test_name, ex, traceback.format_exc()))
                if result < 0:
                    status = "FAIL"
                    overall_status = "FAIL"
                    logger.info("Testcase %s failed" % test_name)
                else:
                    status = result.get("status")
                    self.details.update(
                        {test_name: {'status': status,
                                     'details': result.get("details")}})
                    logger.info("Results of test case '%s - %s':\n%s\n" %
                                (test_name, test_descr, result))

                    if status == "FAIL":
                        overall_status = "FAIL"

        self.stop_time = time.time()

        if overall_status == "FAIL":
            return testcase.TestCase.EX_OK

        return testcase.TestCase.EX_RUN_ERROR
