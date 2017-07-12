# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# performes:
# - Gather
#   - odl logs
#   - ovs logs
#   - neutron logs
#   - odl datastore state
#   - ovs state (openflow and dp)
#   - optional - memory dump from odl

import os
import inspect

import sdnvpn.lib.utils as test_utils
import functest.utils.functest_utils as ft_utils
from functest.utils.constants import CONST

LIB_PATH = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory


def gather_logs(name):
    openstack_nodes = test_utils.get_nodes()

    ft_utils.execute_command_raise('rm -rf /tmp/sdnvpn-logs/; mkdir -p /tmp/sdnvpn-logs/')
    for node in openstack_nodes:
        node.put_file('%s/../sh_utils/fetch-log-script.sh' % LIB_PATH, '/tmp/fetch-log-script.sh')
        node.run_cmd('sudo bash /tmp/fetch-log-script.sh')
        node.get_file('/tmp/log_output.tar.gz', '/tmp/log_output-%s.tar.gz' % node.get_dict()['name'])
        ft_utils.execute_command_raise('mkdir -p /tmp/sdnvpn-logs/')
        ft_utils.execute_command_raise(
            'cd /tmp/sdnvpn-logs/; tar -xzvf /tmp/log_output-%s.tar.gz --strip-components=1'
            % node.get_dict()['name'])

    ft_utils.execute_command_raise('cd %s;tar czvf sdnvpn-logs-%s.tar.gz -C /tmp/ sdnvpn-logs/'
                                    % (CONST.__getattribute__('dir_results'), name))


if __name__ == '__main__':
    gather_logs('test')
