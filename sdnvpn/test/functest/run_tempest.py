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
import uuid

from functest.core import tenantnetwork
from functest.opnfv_tests.openstack.tempest.tempest import TempestCommon
import os_client_config
import shade
from six.moves import configparser

from sdnvpn.lib import config as sdnvpn_config
from sdnvpn.lib import openstack_utils as os_utils


logger = logging.getLogger('sdnvpn-tempest')

COMMON_CONFIG = sdnvpn_config.CommonConfig()
TESTCASE_CONFIG = sdnvpn_config.TestcaseConfig(
    'sdnvpn.test.functest.run_tempest')


class BgpvpnTempest(TempestCommon):
    def __init__(self, **kwargs):
        try:
            cloud_config = os_client_config.get_config()
            guid = str(uuid.uuid4())
            self.case_name = kwargs['case_name']
            self.orig_cloud = shade.OperatorCloud(cloud_config=cloud_config)
            self.cloud = self.orig_cloud
            self.project = tenantnetwork.NewProject(
                self.orig_cloud, self.case_name, guid)
            self.project.create()
        except Exception:
            raise Exception("Cannot create user or project")
        super(BgpvpnTempest, self).__init__(**kwargs)

    def configure(self, **kwargs):
        super(BgpvpnTempest, self).configure(**kwargs)
        glance_client = os_utils.get_glance_client()
        img_ref = os_utils.create_glance_image(glance_client,
                                               TESTCASE_CONFIG.image_name,
                                               COMMON_CONFIG.image_path,
                                               disk=COMMON_CONFIG.image_format,
                                               container='bare',
                                               public='public')
        nova_client = os_utils.get_nova_client()
        flav_ref = os_utils.get_flavor_id(nova_client,
                                          COMMON_CONFIG.default_flavor)
        rconfig = configparser.RawConfigParser()
        rconfig.read(self.conf_file)
        rconfig.set('service_available', 'bgpvpn', 'True')
        logger.debug("Updating %s with bgpvpn=True"
                     % self.conf_file)
        rconfig.set('compute', 'flavor_ref', flav_ref)
        logger.debug("Updating %s with flavor_id %s"
                     % (self.conf_file, flav_ref))
        rconfig.set('compute', 'image_ref', img_ref)
        with open(self.conf_file, 'wb') as config_file:
            rconfig.write(config_file)
        self.backup_tempest_config(self.conf_file, self.res_dir)


def main():
    try:
        test_case = BgpvpnTempest(**TESTCASE_CONFIG.functest_conf)
    except Exception as e:
        logger.error("Initialization of bgpvpn tempest failed: %s" % e)
        result = 'FAIL'
    else:
        test_case.check_requirements()
        try:
            test_case.run(**TESTCASE_CONFIG.functest_conf['run']['args'])
        except KeyError:
            test_case.run()
        result = 'PASS' if (test_case.is_successful() == os.EX_OK) else 'FAIL'
        test_case.clean()

    return {'result': result,
            'details': 'Tempest testcases have been completed'}


if __name__ == '__main__':
    main()
