#!/bin/python
import time

from utils import processutils
from utils.utils_log import LOG, for_all_methods, log_enter_exit
from utils.service import Service
from utils.node_manager import NodeManager
from common import constants
from utils import utils_yaml


@for_all_methods(log_enter_exit)
class ODLReInstaller(Service):
    def __init__(self):
        self.netvirt_url = "restconf/operational/network-topology:" \
                           "network-topology/topology/netvirt:1"

    def run(self, sys_args, config):
        pod_config = sys_args.pod_config
        node_config = utils_yaml.read_dict_from_yaml(
            pod_config + constants.NODE_YAML_PATH)
        # TODO Add validation of incoming node config
        # self.check_node_config()

        # copy ODL to all nodes where it need to be copied
        self.nodes = NodeManager(node_config['servers']).get_nodes()
        for node in self.nodes:
            node.execute('ovs-vsctl del-controller br-int', as_root=True)
        odl_node = None
        for node in self.nodes:
            # Check if ODL runs on this node
            rv, _ = node.execute('ps aux |grep -v grep |grep karaf',
                                 as_root=True, check_exit_code=[0, 1])
            if 'java' in rv:
                odl_node = node
                node.execute('systemctl stop opendaylight', as_root=True)

            ODLReInstaller.disconnect_ovs(node)

        # Bring ODL up back
        LOG.info("Installing new OpenDaylight")
        if odl_node is None:
            LOG.error("Unable to locate node running OpenDaylight for upgrade")
            raise ODLReinstallertException("Unable to find node running ODL")
        ODLReInstaller.reinstall_odl(odl_node, sys_args.odl_artifact)

        # Wait for ODL to come back up
        full_netvirt_url = "http://{}:8081/{}".format(
            odl_node.config['address'], self.netvirt_url)
        counter = 1
        while counter < 10:
            try:
                odl_node.execute("curl --fail -u admin:admin {}".format(
                    full_netvirt_url))
                LOG.info("New OpenDaylight NetVirt is Up")
                break
            except processutils.ProcessExecutionError:
                LOG.warning("NetVirt not up. Attempt: {}".format(counter))
                if counter >= 10:
                    LOG.warning("NetVirt not detected as up after 10 "
                                "attempts...deployment may be unstable!")
            counter += 1
            time.sleep(10)

        # Reconnect OVS instances
        LOG.info("Reconnecting OVS instances")
        for node in self.nodes:
            ODLReInstaller.connect_ovs(node)

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
        # --detailed-exitcodes: Provide extra information about the run via
        # exit codes. If enabled, 'puppet apply' will use the following exit
        # codes:
        # 0: The run succeeded with no changes or failures; the system was
        #    already in the desired state.
        # 1: The run failed.
        # 2: The run succeeded, and some resources were changed.
        # 4: The run succeeded, and some resources failed.
        # 6: The run succeeded, and included both changes and failures.

    @staticmethod
    def disconnect_ovs(node):
        LOG.info('Disconnecting OpenVSwitch from controller on node %s'
                 % node.name)
        node.execute('ovs-vsctl del-controller br-int', as_root=True)
        node.execute('ovs-vsctl del-manager', as_root=True)

    @staticmethod
    def connect_ovs(node):
        LOG.info('Connecting OpenVSwitch to controller on node %s' % node.name)
        ovs_controller = node.config['ovs-controller']
        node.execute('ovs-vsctl set-controller br-int %s'
                     % ovs_controller, as_root=True)
        ovs_manager_str = ' '.join(node.config['ovs-managers'])
        node.execute('ovs-vsctl set-manager %s' % ovs_manager_str,
                     as_root=True)

    def create_cli_parser(self, parser):
        parser.add_argument('--pod_config',
                            help=("Give the path to the clone info"),
                            required=True)
        parser.add_argument('--odl-artifact',
                            help=("Path to Opendaylight tarball"),
                            required=True)
        return parser


class ODLReinstallertException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


def main():
    main = ODLReInstaller()
    main.start()

if __name__ == '__main__':
    main()
