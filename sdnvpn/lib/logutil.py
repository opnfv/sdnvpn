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

from sdnvpn.lib import config as sdnvpn_config


common_config = sdnvpn_config.CommonConfig()


def getLogger(module_name):
    logger = logging.getLogger(module_name)
    setLogHandler(logger)
    return logger


def setLogHandler(logger):
        handler = logging.FileHandler(common_config.result_file)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
