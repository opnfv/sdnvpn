#!/bin/python
#
# Copyright (c) 2015 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

import argparse
import importlib
import sys
import time
import yaml

import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils
from sdnvpn.lib import config as sdnvpn_config


parser = argparse.ArgumentParser()
parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")
args = parser.parse_args()

COMMON_CONFIG = sdnvpn_config.CommonConfig()

TEST_DB_URL = COMMON_CONFIG.test_db
logger = ft_logger.Logger("sdnvpn-run-tests").getLogger()


def push_results(testname, start_time, end_time, criteria, details):
    logger.info("Push testcase '%s' results into the DB...\n" % testname)
    ft_utils.push_results_to_db("sdnvpn",
                                testname,
                                start_time,
                                end_time,
                                criteria,
                                details)


def main():

    with open(COMMON_CONFIG.config_file) as f:
        config_yaml = yaml.safe_load(f)

    testcases = config_yaml.get("testcases")
    overall_status = "PASS"
    for testcase in testcases:
        if testcases[testcase]['enabled']:
            test_name = testcase
            test_descr = testcases[testcase]['description']
            test_name_db = testcases[testcase]['testname_db']
            title = ("Running '%s - %s'" %
                     (test_name, test_descr))
            logger.info(title)
            logger.info("%s\n" % ("=" * len(title)))
            t = importlib.import_module(testcase, package=None)
            start_time = time.time()
            result = t.main()
            end_time = time.time()
            if result < 0:
                status = "FAIL"
                overall_status = "FAIL"
            else:
                status = result.get("status")
                details = result.get("details")
                logger.info("Results of test case '%s - %s':\n%s\n" %
                            (test_name, test_descr, result))

                if status == "FAIL":
                    overall_status = "FAIL"

            if args.report:
                push_results(
                    test_name_db, start_time, end_time, status, details)

    if overall_status == "FAIL":
        sys.exit(-1)

    sys.exit(0)


if __name__ == '__main__':
    main()
