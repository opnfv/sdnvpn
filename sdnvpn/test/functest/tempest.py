#!/usr/bin/python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#
import ConfigParser
import logging
import os
import re
import shutil

import functest.opnfv_tests.openstack.tempest.conf_utils as tempest_utils

logger = logging.getLogger('sdnvpn-tempest')


def main():
    verifier_repo_dir = tempest_utils.get_verifier_repo_dir(None)
    src_tempest_dir = tempest_utils.get_verifier_deployment_dir(None, None)

    if not src_tempest_dir:
        logger.error("Rally deployment not found.")
        exit(-1)

    tempest_utils.configure_verifier(src_tempest_dir)

    src_tempest_conf = os.path.join(src_tempest_dir, 'tempest.conf')
    bgpvpn_tempest_conf = os.path.join(src_tempest_dir, 'bgpvpn_tempest.conf')
    bgpvpn_tempest_list = os.path.join(src_tempest_dir, 'tempest_list.txt')

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

    cmd = ("cd {0};"
           "testr list-tests networking_bgpvpn_tempest > {1};"
           "cd -;".format(verifier_repo_dir, bgpvpn_tempest_list))
    logger.info("Generating bgpvpn tempest list: %s" % cmd)
    os.popen(cmd)

    cmd_line = ("tempest run --config-file {0} -t --whitelist-file {1}"
                .format(bgpvpn_tempest_conf, bgpvpn_tempest_list))
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
        if int(failed) == 0:
            status = "PASS"
        else:
            status = "FAIL"

        return {"status": status, "details": results}
    except:
        logger.error("Problem when parsing the results.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
