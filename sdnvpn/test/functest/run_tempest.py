#!/usr/bin/env python
#
# Copyright (c) 2018 All rights reserved
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

from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import openstack_utils as os_utils


logger = logging.getLogger('sdnvpn-tempest')

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.run_tempest')


def main():
    verifier_id = tempest_utils.get_verifier_id()
    deployment_id = tempest_utils.get_verifier_deployment_id()
    src_tempest_dir = tempest_utils.get_verifier_deployment_dir(
        verifier_id, deployment_id)

    if not src_tempest_dir:
        logger.error("Rally deployment not found.")
        exit(-1)

    tempest_utils.configure_verifier(src_tempest_dir)

    src_tempest_conf = os.path.join(src_tempest_dir, 'tempest.conf')
    bgpvpn_tempest_conf = os.path.join(src_tempest_dir, 'bgpvpn_tempest.conf')

    if not os.path.isfile(src_tempest_conf):
        logger.error("tempest.conf not found in %s." % src_tempest_conf)
        exit(-1)
    shutil.copy(src_tempest_conf, bgpvpn_tempest_conf)

    _, img_ref = os_utils.get_or_create_image(TESTCASE_CONFIG.image_name,
                                              COMMON_CONFIG.image_path,
                                              COMMON_CONFIG.image_format,
                                              extra_properties={})

    nova_client = os_utils.get_nova_client()
    flav_ref = os_utils.get_flavor_id(nova_client,
                                      COMMON_CONFIG.default_flavor)

    logger.info("Copying tempest.conf to %s." % bgpvpn_tempest_conf)
    config = ConfigParser.RawConfigParser()
    config.read(bgpvpn_tempest_conf)
    config.set('service_available', 'bgpvpn', 'True')
    logger.debug("Updating %s with bgpvpn=True" % bgpvpn_tempest_conf)
    config.set('compute', 'flavor_ref', flav_ref)
    logger.debug("Updating %s with flavor_id %s"
                 % (bgpvpn_tempest_conf, flav_ref))
    config.set('compute', 'image_ref', img_ref)
    logger.debug("Updating %s with image_id %s"
                 % (bgpvpn_tempest_conf, img_ref))
    with open(bgpvpn_tempest_conf, 'wb') as tempest_conf:
        config.write(tempest_conf)

    # TODO: Though --config-file parameter is set during the tempest run,
    # it looks for tempest.conf at /etc/tempest/ directory. so applying
    # the following workaround. Will remove it when the root cause is found.
    cmd = ("mkdir -p /etc/tempest;"
           "cp {0} /etc/tempest/tempest.conf".format(bgpvpn_tempest_conf))
    logger.info("Configuring default tempest conf file")
    os.popen(cmd)

    cmd_line = "tempest run -t --regex networking_bgpvpn_tempest " \
               "--config-file /etc/tempest/tempest.conf"
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
        m = re.search('- Failed:(.*)', output)
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
    except Exception as e:
        logger.error("Problem when parsing the results: %s", e)


if __name__ == '__main__':
    main()
