#!/bin/python
import os
from utils.utils_log import LOG, for_all_methods, log_enter_exit, LOG_PATH
from utils.service import Service
from utils.node_manager import NodeManager
from utils.ssh_util import SSH_CONFIG


@for_all_methods(log_enter_exit)
class ODLReInstaller(Service):

    def run(self, sys_args, config):
        SSH_CONFIG['ID_RSA_PATH'] = sys_args.id_rsa
        # copy ODL to all nodes where it need to be copied
        self.nodes = NodeManager(config['servers']).get_nodes()
        for node in self.nodes:
            LOG.info('Disconnecting OpenVSwitch from controller on node %s' % node.name)
            node.execute('ovs-vsctl del-controller br-int', as_root=True)

        for node in self.nodes:
            if 'ODL' in node.config:
                tar_tmp_path = '/tmp/odl-artifact/'
                if node.config['ODL'].get('dir_exsist'):
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
                if node.config['ODL'].get('active'):
                    LOG.info('Installing and Starting Opendaylight on node %s'
                             % node.name)
                    node.copy('to', 'odl_reinstaller/install_odl.pp',
                              tar_tmp_path)
                    node.execute('puppet apply --modulepath='
                                 '/etc/puppet/modules/ %sinstall_odl.pp '
                                 '--verbose --debug --trace'
                                 '--detailed-exitcodes'
                                 % tar_tmp_path, ccheck_exit_code=[2],
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
        parser.add_argument('-c', '--config',
                            help=("Give the path to the node config file "
                                  "(node.yaml)"),
                            required=True)
        parser.add_argument('--odl-artifact',
                            help=("Path to Opendaylight tarball"),
                            required=True)
        parser.add_argument('--id-rsa',
                            help=("Path to the identity file which can "
                                  "be used to connect to the overcloud"),
                            required=True)
        return parser


def main():
    main = ODLReInstaller()
    main.start()

if __name__ == '__main__':
    main()
