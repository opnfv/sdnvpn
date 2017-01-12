import re
import processutils
from processutils import execute
from utils.node import Node


class TripleoHelper():

    @staticmethod
    def find_overcloud_ips():
        try:
            res, _ = TripleoHelper.get_underlcoud().execute(
                "source /home/stack/stackrc; nova list",
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
                                 '$2}\'', shell=True)
        for node in vnode_names.split('\n'):
            if 'baremetal' in node:
                admin_net_mac, _ = execute(
                    'virsh domiflist %s |grep admin |awk \'{print $5}\''
                    % node, shell=True)
                if admin_net_mac.replace('\n', '') == mac:
                    return node
        raise Exception('Could not find corresponding virtual node for MAC: %s'
                        % mac)

    @staticmethod
    def get_underloud_ip():
        out, _ = execute('virsh domifaddr undercloud ', shell=True)
        return re.findall('([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', out)[0]

    @staticmethod
    def get_underlcoud():
        return Node('underloud', address=TripleoHelper.get_underloud_ip(),
                    user='stack')


class TripleOHelperException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value
