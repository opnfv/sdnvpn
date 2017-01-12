#!/bin/python
import os
from utils.utils_log import LOG, for_all_methods, log_enter_exit
from utils.service import Service
from utils.node_manager import NodeManager
from utils.ssh_util import SSH_CONFIG
from common import config as CONFIG
from utils import utils_yaml


@for_all_methods(log_enter_exit)
class ODLReInstaller(Service):

    def run(self, sys_args, config):
        cloner_info_path = sys_args.cloner_info
        SSH_CONFIG['ID_RSA_PATH'] = (cloner_info_path + CONFIG.ID_RSA_PATH +
                                     'id_rsa')
        node_config = utils_yaml.read_dict_from_yaml(
            cloner_info_path + CONFIG.NODE_YAML_PATH)
        # copy ODL to all nodes where it need to be copied
        self.nodes = NodeManager(node_config['servers']).get_nodes()
        for node in self.nodes:
            LOG.info('Disconnecting OpenVSwitch from controller on node %s'
                     % node.name)
            node.execute('ovs-vsctl del-controller br-int', as_root=True)

        for node in self.nodes:
            if 'ODL' in node.config:
                tar_tmp_path = '/tmp/odl-artifact/'
                if node.config['ODL'].get('active'):
                    tarball_name = os.path.basename(sys_args.odl_artifact)
                    node.copy('to', sys_args.odl_artifact,
                              '/tmp/odl-artifact/' + tarball_name)
                    node.execute('rm -rf /opt/opendaylight/*', as_root=True)
                    node.execute('mkdir -p /opt/opendaylight/*', as_root=True)
                    LOG.info('Extracting %s to /opt/opendaylight/ on node %s'
                             % (tarball_name, node.name))
                    node.execute('tar -zxf %s --strip-components=1 -C '
                                 '/opt/opendaylight/'
                                 % (tar_tmp_path + tarball_name), as_root=True)
                    node.execute('chown -R odl:odl /opt/opendaylight',
                                 as_root=True)
                    node.execute('rm -rf ' + tar_tmp_path, as_root=True)
                    LOG.info('Installing and Starting Opendaylight on node %s'
                             % node.name)
                    node.copy('to', 'odl_reinstaller/install_odl.pp',
                              tar_tmp_path)
                    node.execute('puppet apply --modulepath='
                                 '/etc/puppet/modules/ %sinstall_odl.pp '
                                 '--verbose --debug --trace '
                                 '--detailed-exitcodes'
                                 % tar_tmp_path, check_exit_code=[2],
                                 as_root=True)
        # --detailed-exitcodes: Provide extra information about the run via
        # exit codes. If enabled, 'puppet apply' will use the following exit
        # codes:
        # 0: The run succeeded with no changes or failures; the system was
        #    already in the desired state.
        # 1: The run failed.
        # 2: The run succeeded, and some resources were changed.
        # 4: The run succeeded, and some resources failed.
        # 6: The run succeeded, and included both changes and failures.

        for node in self.nodes:
            LOG.info('Connecting OpenVSwitch to controller on node %s'
                     % node.name)
            ovs_controller = node.config.get('ovs-controller')
            if ovs_controller:
                node.execute('ovs-vsctl set-controller br-int %s'
                             % ovs_controller, as_root=True)

    def create_cli_parser(self, parser):
        parser.add_argument('--cloner-info',
                            help=("Give the path to the clone info"),
                            required=True)
        parser.add_argument('--odl-artifact',
                            help=("Path to Opendaylight tarball"),
                            required=True)
        return parser

    @staticmethod
    def reinstall_odl(node, odl_tarball):
        tar_tmp_path = '/tmp/odl-artifact/'
        node.copy('to', odl_tarball, tar_tmp_path + odl_tarball)
        node.execute('rm -rf /opt/opendaylight/*', as_root=True)
        node.execute('mkdir -p /opt/opendaylight/*', as_root=True)
        LOG.info('Extracting %s to /opt/opendaylight/ on node %s'
                 % (odl_tarball, node.name))
        node.execute('tar -zxf %s --strip-components=1 -C '
                     '/opt/opendaylight/'
                     % (tar_tmp_path + odl_tarball), as_root=True)
        node.execute('chown -R odl:odl /opt/opendaylight', as_root=True)
        node.execute('rm -rf ' + tar_tmp_path, as_root=True)
        LOG.info('Installing and Starting Opendaylight on node %s' % node.name)
        node.execute('puppet apply -e "include opendaylight" '
                     '--modulepath=/etc/puppet/modules/ '
                     '--verbose --debug --trace --detailed-exitcodes',
                     check_exit_code=[2], as_root=True)

    @staticmethod
    def reconnect_ovs(node):
        LOG.info('Connecting OpenVSwitch to controller on node %s' % node.name)
        ovs_controller = node.config.get('ovs-controller')
        node.execute('ovs-vsctl set-controller br-int %s'
                     % ovs_controller, as_root=True)
        ovs_manager_str = ' '.join(node.config.get('ovs-managers'))
        node.execute('ovs-vsctl set-manager %s' % ovs_manager_str,
                     as_root=True)


def main():
    main = ODLReInstaller()
    main.start()

if __name__ == '__main__':
    main()
