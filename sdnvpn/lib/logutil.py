#!/usr/bin/env python
#
# Copyright (c) 2018 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
import logging
import os.path

from xtesting.core import feature


def getLogger(module_name):
    logger = logging.getLogger(module_name)
    log_file = "{}/{}.log".format("/var/lib/xtesting/results", "bgpvpn")
    if not os.path.exists(log_file):
        open(log_file, 'w+')
    feature.Feature.configure_logger(logger, log_file)
    return logger
