#!/bin/bash
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
import time
import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils
import yaml

""" tests configuration """
parser = argparse.ArgumentParser()
parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")
args = parser.parse_args()

TEST_DB_URL = ft_utils.get_parameter_from_yaml('results.test_db_url')
logger = ft_logger.Logger("sdnvpn-run-tests").getLogger()
REPO_PATH = os.environ['repos_dir'] + '/sdnvpn/'


def push_results(testname, start_time, end_time, criteria, details):
    logger.info("Push testcase '%s' results into the DB...\n" % testname)
    ft_utils.push_results_to_db("sdnvpn",
                                testname,
                                logger,
                                start_time,
                                end_time,
                                criteria,
                                details)


def main():

    with open(REPO_PATH + 'test/functest/config.yaml') as f:
        config_yaml = yaml.safe_load(f)

    testcases = config_yaml.get("testcases")
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
            if result < 0:
                result = {"status": "FAILED", "details": "execution error."}
            logger.info("Results of test case '%s':\n%s" % (test_name, result))
            end_time = time.time()
            # duration = end_time - start_time
            criteria = result.get("status")
            details = result.get("details")
            if args.report:
                push_results(
                    test_name_db, start_time, end_time, criteria, details)

    exit(0)


if __name__ == '__main__':
    main()
