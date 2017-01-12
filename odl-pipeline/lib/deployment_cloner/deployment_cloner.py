#!/bin/python
from utils import utils_yaml
from utils.utils_log import for_all_methods, log_enter_exit
from utils.service import Service
from utils.node_manager import NodeManager
from utils.processutils import execute
from common import config as CONFIG


@for_all_methods(log_enter_exit)
class DeploymentCloner(Service):

    undercloud_root_dir = '~/DeploymentCloner/'

    def create_cli_parser(self, parser):
        parser.add_argument('--undercloud-ip', help="ip of undercloud",
                            required=True)
        parser.add_argument('--dest-dir', help="where everything should go to",
                            required=True)
        return parser

    def undercloud_dict(self, undercloud_ip):
        return {'address': undercloud_ip,
                'user': 'stack'}

    def run(self, sys_args, config):
        dest_dir = sys_args.dest_dir if sys_args.dest_dir[:-1] == '/'\
            else (sys_args.dest_dir + '/')
        self.node_manager = NodeManager()
        underlcloud = self.node_manager.add_node(
            'undercloud',
            self.undercloud_dict(sys_args.undercloud_ip))
        # copy all files to undercloud
        underlcloud.copy('to', '.', self.undercloud_root_dir)
        # generate the undercloud yaml
        underlcloud.execute('cd %s; ./tripleo_manager.sh --out ./cloner-info/'
                            % self.undercloud_root_dir, log_true=True)
        underlcloud.copy('from', dest_dir,
                         self.undercloud_root_dir + '/cloner-info/')
        node_yaml_path = dest_dir + '/cloner-info/' + CONFIG.NODE_YAML_PATH
        node_yaml = utils_yaml.read_dict_from_yaml(node_yaml_path)
        for name, node in node_yaml['servers'].iteritems():
            node['vNode-name'] = self.get_virtual_node_name_from_mac(
                node['orig-ctl-mac'])
        utils_yaml.write_dict_to_yaml(node_yaml, node_yaml_path)
        # TODO copy qcow and tar it

    @staticmethod
    def get_virtual_node_name_from_mac(mac):
        vNode_names, _ = execute('virsh list|awk \'{print $2}\'', shell=True)
        for node in vNode_names.split('\n'):
            if 'baremetal' in node:
                admin_net_mac, _ = execute(
                    'virsh domiflist %s |grep admin |awk \'{print $5}\''
                    % node, shell=True)
                if admin_net_mac.replace('\n', '') == mac:
                    return node
        raise Exception('Could not find corresponding virtual node for MAC: %s'
                        % mac)


def main():
    main = DeploymentCloner()
    main.start()

if __name__ == '__main__':
    main()
