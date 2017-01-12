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

    def create_cli_parser(self, parser):
        parser.add_argument('--out',
                            help="Directory where env_info will be written to",
                            required=True)
        return parser

    def run(self, sys_args, config):
        dest_dir = sys_args.out if sys_args.out[:-1] == '/'\
            else (sys_args.out + '/')
        self.gen_node_info()
        shutil.mkdir_if_not_exist(dest_dir)
        utils_yaml.write_dict_to_yaml(self.node_info,
                                      sys_args + constants.NODE_YAML_PATH)

    def gen_node_info(self):
        overcloud_ip_list = TripleoHelper.find_overcloud_ips()

        for node_ip in overcloud_ip_list:
            LOG.info('Introspecting node %s' % node_ip)
            node = Node('intro-%s' % node_ip, address=node_ip,
                        user=self.overcloud_user)
            node_mac = None
            virsh_domain = None
            server_name, _ = node.execute('hostname')
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
            ovs_controller, _ = node.execute('ovs-vsctl get-controller br-int')
            out, _ = node.execute('ovs-vsctl get-manager')
            ovs_managers = out.split("\n")
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
        underloud = TripleoHelper.get_underlcoud()
        # copy overcloudrc
        underloud.copy('from', dest, './overcloudrc')

        # copy ssh id
        underloud.copy('from', dest, '.ssh/id_rsa')


class TripleOInspectorException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


def main():
    TripleOIntrospector().start()

if __name__ == '__main__':
    main()
