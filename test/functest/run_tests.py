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
import os
import sys
import time
import yaml

import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils
import config as sdnvpn_config


parser = argparse.ArgumentParser()
parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")
args = parser.parse_args()

TEST_DB_URL = ft_utils.get_functest_config('results.test_db_url')
logger = ft_logger.Logger("sdnvpn-run-tests").getLogger()

COMMON_CONFIG = sdnvpn_config.CommonConfig()
config_file = os.path.join(
    COMMON_CONFIG.repo_path, 'test/functest/config.yaml')


def push_results(testname, start_time, end_time, criteria, details):
    logger.info("Push testcase '%s' results into the DB...\n" % testname)
    ft_utils.push_results_to_db("sdnvpn",
                                testname,
                                start_time,
                                end_time,
                                criteria,
                                details)


def main():

    with open(config_file) as f:
        config_yaml = yaml.safe_load(f)

    testcases = config_yaml.get("testcases")
    overall_details = {}
    overall_status = "PASS"
    overall_start_time = time.time()
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
            duration = end_time - start_time
            if result < 0:
                status = "FAIL"
                overall_status = "FAIL"
                overall_details.update({test_name_db: "execution error."})
            else:
                status = result.get("status")
                details = result.get("details")
                logger.info("Results of test case '%s - %s':\n%s\n" %
                            (test_name, test_descr, result))

                if status == "FAIL":
                    overall_status = "FAIL"

                dic = {"duration": duration, "status": status}
                overall_details.update({test_name_db: dic})
            if args.report:
                push_results(
                    test_name_db, start_time, end_time, status, details)

    overall_end_time = time.time()
    if args.report:
        push_results(
            "bgpvpn", overall_start_time, overall_end_time,
            overall_status, overall_details)

    if overall_status == "FAIL":
        sys.exit(-1)

    sys.exit(0)


if __name__ == '__main__':
    main()
