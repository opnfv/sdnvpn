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
import logging
import os

from functest.opnfv_tests.openstack.tempest.tempest import TempestCommon
from six.moves import configparser

from sdnvpn.lib import config as sdnvpn_config


logger = logging.getLogger('sdnvpn-tempest')

TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.run_tempest')


class BgpvpnTempest(TempestCommon):
    def configure(self, **kwargs):
        super(BgpvpnTempest, self).configure(**kwargs)
        rconfig = configparser.RawConfigParser()
        rconfig.read(self.conf_file)
        rconfig.set('service_available', 'bgpvpn', 'True')
        logger.debug("Updating %s with bgpvpn=True"
                     % self.conf_file)
        with open(self.conf_file, 'wb') as config_file:
            rconfig.write(config_file)
        self.backup_tempest_config(self.conf_file, self.res_dir)


def main():
    try:
        test_case = BgpvpnTempest(**TESTCASE_CONFIG.functest_conf)
    except Exception as e:
        logger.error("Initialization of bgpvpn tempest failed: %s" % e)
        status = 'FAIL'
    else:
        test_case.check_requirements()
        try:
            test_case.run(**TESTCASE_CONFIG.functest_conf['run']['args'])
        except KeyError:
            test_case.run()
        status = 'PASS' if (test_case.is_successful() == os.EX_OK) else 'FAIL'
        test_case.clean()

    return {'status': status,
            'details': 'Tempest testcases have been completed'}


if __name__ == '__main__':
    main()
