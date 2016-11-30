#
# Copyright (c) 2015 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#
import yaml


def write_dict_to_yaml(config, path):
    with open(path, 'w+') as f:
        yaml.dump(config, f, default_flow_style=False)


def read_dict_from_yaml(path):
    with open(path, 'r') as f:
        return yaml.load(f)
