#!/usr/bin/python
#
# Copyright (c) 2015 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#
import ConfigParser
import os
import re
import shutil

import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils
from sdnvpn.lib import config as sdnvpn_config

logger = ft_logger.Logger("sdnvpn-tempest").getLogger()

COMMON_CONFIG = sdnvpn_config.CommonConfig()

SUCCESS_CRITERIA = ft_utils.get_parameter_from_yaml(
    "testcases.testcase_1.succes_criteria", COMMON_CONFIG.config_file)


def main():
    src_tempest_dir = ft_utils.get_deployment_dir()
    if not src_tempest_dir:
        logger.error("Rally deployment not found.")
        exit(-1)

    src_tempest_conf = src_tempest_dir + '/tempest.conf'
    bgpvpn_tempest_conf = src_tempest_dir + '/bgpvpn_tempest.conf'

    if not os.path.isfile(src_tempest_conf):
        logger.error("tempest.conf not found in %s." % src_tempest_conf)
        exit(-1)
    shutil.copy(src_tempest_conf, bgpvpn_tempest_conf)

    logger.info("Copying tempest.conf to %s." % bgpvpn_tempest_conf)
    config = ConfigParser.RawConfigParser()
    config.read(bgpvpn_tempest_conf)
    config.set('service_available', 'bgpvpn', 'True')
    logger.debug("Updating %s with bgpvpn=True" % bgpvpn_tempest_conf)
    with open(bgpvpn_tempest_conf, 'wb') as tempest_conf:
        config.write(tempest_conf)

    cmd_line = (src_tempest_dir +
                "/run_tempest.sh -C %s -t -N -- "
                "networking_bgpvpn_tempest" % bgpvpn_tempest_conf)
    logger.info("Executing: %s" % cmd_line)
    cmd = os.popen(cmd_line)
    output = cmd.read()
    logger.debug(output)
    # Results parsing
    error_logs = ""
    duration = 0
    failed = 0
    try:
        # Look For errors
        error_logs = ""
        for match in re.findall('(.*?)[. ]*FAILED', output):
            error_logs += match
        # look for duration
        m = re.search('tests in(.*)sec', output)
        duration = m.group(1)
        # Look for num tests run
        m = re.search('Ran:(.*)tests', output)
        num_tests = m.group(1)
        # Look for tests failed
        m = re.search('Failed:(.*)', output)
        failed = m.group(1)
        # Look for name of the tests
        testcases = re.findall("\{0\} (.*)", output)

        results = {"duration": duration,
                   "num_tests": num_tests, "failed": failed,
                   "tests": testcases}
        status = "PASS"
        if 100 - (100 * int(failed) / int(num_tests)) < int(SUCCESS_CRITERIA):
            status = "FAILED"
        return {"status": status, "details": results}
    except:
        logger.error("Problem when parsing the results.")


if __name__ == '__main__':
    main()
