#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#
import re
import processutils
from processutils import execute
from utils.node import Node


class TripleoHelper():

    @staticmethod
    def find_overcloud_ips():
        try:
            res, _ = TripleoHelper.get_undercloud().execute(
                "'source /home/stack/stackrc; nova list'",
                shell=True)
        except processutils.ProcessExecutionError as e:
            raise TripleOHelperException(
                "Error unable to issue nova list "
                "on undercloud.  Please verify "
                "undercloud is up.  Full error: {"
                "}".format(e.message))
        return re.findall('ctlplane=([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', res)

    @staticmethod
    def get_virtual_node_name_from_mac(mac):
        vnode_names, _ = execute('virsh list|awk \'{print '
                                 '$2}\'', shell=True, as_root=True)
        for node in vnode_names.split('\n'):
            if 'baremetal' in node:
                admin_net_mac, _ = execute(
                    'virsh domiflist %s |grep admin |awk \'{print $5}\''
                    % node, shell=True, as_root=True)
                if admin_net_mac.replace('\n', '') == mac:
                    return node
        raise Exception('Could not find corresponding virtual node for MAC: %s'
                        % mac)

    @staticmethod
    def get_undercloud_ip():
        out, _ = execute('virsh domifaddr undercloud', shell=True,
                         as_root=True)
        return re.findall('([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', out)[0]

    @staticmethod
    def get_undercloud():
        return Node('undercloud', address=TripleoHelper.get_undercloud_ip(),
                    user='stack', password='stack')


class TripleOHelperException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value
