#!/bin/bash
#
# Copyright (c) 2015 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#

import importlib
import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils
import yaml


logger = ft_logger.Logger("sdnvpn").getLogger()

with open('config.yaml') as f:
    config_yaml = yaml.safe_load(f)

testcases = config_yaml.get("testcases")
for testcase in testcases:
    title = ("Running '%s - %s'" %
             (testcase, testcases[testcase]['description']))
    print(title)
    print("%s\n" % ("=" * len(title)))
    if testcases[testcase]['type'] == 'python':
        t = importlib.import_module(testcase, package=None)
        t.main()
    else:
        cmd = "bash " + testcase + ".sh"
        result = ft_utils.execute_command(cmd, logger, exit_on_error=False)
