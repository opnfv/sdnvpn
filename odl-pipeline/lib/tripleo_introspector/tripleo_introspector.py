import os
import re

from utils import processutils
from utils.node import Node
from utils.utils_log import log_enter_exit, for_all_methods, LOG
from utils.service import Service
from utils.shutil import shutil
from common import constants
from utils import utils_yaml
from utils.tripleo_helper import TripleoHelper


@for_all_methods(log_enter_exit)
class TripleOIntrospector(Service):

    def __init__(self):
        self.overcloud_user = 'heat-admin'
        self.node_info = {'servers': {}}

    def create_cli_parser(self, parser):
        parser.add_argument('--out-file',
                            help="File where pod config will be written to. "
                                 "Defaults to ./node.yaml",
                            default=constants.NODE_YAML_PATH,
                            dest="out_file",
                            required=False)
        return parser

    def run(self, sys_args, config):
        self.gen_node_info()
        shutil.mkdir_if_not_exist(os.path.dirname(sys_args.out_file))
        utils_yaml.write_dict_to_yaml(self.node_info, sys_args.out_file)

    def gen_node_info(self):
        overcloud_ip_list = TripleoHelper.find_overcloud_ips()

        for node_ip in overcloud_ip_list:
            LOG.info('Introspecting node %s' % node_ip)
            node = Node('intro-%s' % node_ip, address=node_ip,
                        user=self.overcloud_user)
            node_mac = None
            virsh_domain = None
            server_name, _ = node.execute('hostname')
            server_name = server_name.rstrip()
            if 'overcloud-controller' in server_name:
                node_type = 'controller'
            elif 'overcloud-novacompute' in server_name:
                node_type = 'compute'
            else:
                raise TripleOInspectorException('Unknown type '
                                                '(controller/compute) %s '
                                                % server_name)
            try:
                processutils.execute('ping -c 1 %s' % node_ip)
                res, _ = processutils.execute('/usr/sbin/arp -a '
                                              '%s' % node_ip)
                node_mac = \
                    re.search('([0-9a-z]+:){5}[0-9a-z]+', res).group(0)
                virsh_domain = \
                    TripleoHelper.get_virtual_node_name_from_mac(node_mac)
            except AttributeError:
                LOG.warning("Unable to find MAC address for node {"
                            "}".format(node_ip))

            # find ovs controller and manager
            ovs_controller = self.get_ovs_controller(node)
            out, _ = node.execute('ovs-vsctl get-manager', as_root=True)
            ovs_managers = out.rstrip().split("\n")
            if all(ovs_manager == '' for ovs_manager in ovs_managers):
                LOG.warning("OVS managers for node {} is empty!".format(
                    node_ip))
            self.node_info['servers'][server_name] = {
                'address': node_ip,
                'user': self.overcloud_user,
                'type': node_type,
                'orig-ctl-mac': node_mac,
                'vNode-name': virsh_domain,
                'ovs-controller': ovs_controller,
                'ovs-managers': ovs_managers}

    @staticmethod
    def copy_ssh_id_and_overcloudrc(dest):
        undercloud = TripleoHelper.get_undercloud()
        # copy overcloudrc
        undercloud.copy('from', dest, './overcloudrc')

        # copy ssh id
        undercloud.copy('from', dest, '.ssh/id_rsa')

    @staticmethod
    def get_ovs_controller(node):
        # find ovs controller and manager
        ovs_controller, _ = node.execute('ovs-vsctl get-controller '
                                         'br-int', as_root=True)
        ovs_controller = ovs_controller.rstrip()
        if ovs_controller == '':
            LOG.warning("OVS controller for node {} is empty!".format(
                node.address))
        else:
            return ovs_controller


class TripleOInspectorException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


def main():
    TripleOIntrospector().start()

if __name__ == '__main__':
    main()
