import os
import commands
import re
import time
import yaml

from utils import processutils
from odl_reinstaller.odl_reinstaller import ODLReInstaller
from utils.node import Node
from utils.utils_log import log_enter_exit, for_all_methods, LOG
from utils.service import Service
from utils.shutil import shutil
from utils.node_manager import NodeManager
from utils.ssh_util import SshUtil
from common import config as CONFIG
from deployment_cloner.deployment_cloner import DeploymentCloner


@for_all_methods(log_enter_exit)
class TripleOManager(Service):

    def __init__(self):
        self.node_info = {'servers': {}}
        self.overcloud_user = 'heat-admin'
        self.netvirt_url = "restconf/operational/network-topology:" \
                           "network-topology/topology/netvirt:1"

    def create_cli_parser(self, parser):
        parser.add_argument('--introspect',
                            help="Gather node info and dump info",
                            default=False,
                            action='store_true')
        parser.add_argument('--update-opendaylight',
                            help="Remove current OpenDaylight and disconnect"
                                 "OVS instances, then reinstall ODL",
                            default=False,
                            action='store_true',
                            dest='update_odl')
        parser.add_argument('--out',
                            help="Directory where env_info will be written to",
                            default=os.getcwd(),
                            required=False)
        parser.add_argument('--pod-config',
                            help="Config file when cleaning the deployment",
                            default=None,
                            required=False,
                            dest='pod_config')
        parser.add_argument('--artifact',
                            help="OpenDaylight Tarball to be installed when "
                                 "--update-opendaylight is used",
                            default=None,
                            required=False)
        parser.add_argument('--ssh-key-file',
                            help="SSH private key file to use when updating "
                                 "ODL on new snapshot deployment",
                            default=SshUtil.get_id_rsa(),
                            required=False,
                            dest='ssh_key_file')
        return parser

    def run(self, sys_args, config):
        if sys_args.introspect is True:
            self.gen_node_info()
            self.gen_env_info(sys_args.out)
        if sys_args.update_odl is True:
            if sys_args.pod_config is not False:
                self.load_config(sys_args.pod_config)
            elif not bool(self.node_info['servers']):
                raise TripleOManagerException("No config found for cleaning "
                                              "deployment.  Please "
                                              "provide config via --config "
                                              "argument")
            if sys_args.artifact is None:
                raise TripleOManagerException("ODL Tarball must be provided "
                                              "as --artifact when updating "
                                              "ODL")
            self.check_node_config()
            self.prepare_for_ci_pipeline(sys_args.artifact,
                                         ssh_key_file=sys_args.ssh_key_file)

    def prepare_for_ci_pipeline(self, odl_tarball, ssh_key_file=None):
        node_manager = NodeManager(config=self.node_info['servers'],
                                   ssh_key_file=ssh_key_file)
        odl_node = None
        # Clean All Nodes
        LOG.info("Removing previous OpenDaylight and disconnecting OVS")
        for node in node_manager.get_nodes():
            # Check if ODL runs on this node
            rv, _ = node.execute('ps aux |grep -v grep |grep karaf',
                                 as_root=True, check_exit_code=[0, 1])
            if 'java' in rv:
                odl_node = node
                node.execute('systemctl stop opendaylight', as_root=True)

            # Disconnect ovs
            node.execute('ovs-vsctl del-controller br-int', as_root=True)
            node.execute('ovs-vsctl del-manager')

        # Bring ODL up back
        LOG.info("Installing new OpenDaylight")
        ODLReInstaller.reinstall_odl(odl_node, odl_tarball)

        # Wait for ODL to come back up
        full_netvirt_url = "http://{}:8081/{}".format(odl_node.config.get(
            'address'), self.netvirt_url)
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
        for node in node_manager.get_nodes():
            ODLReInstaller.reconnect_ovs(node)

    def gen_env_info(self, output_dir=None):
        shutil.mkdir_if_not_exist(output_dir)
        self.write_out_yaml_config(self.node_info,
                                   output_dir + CONFIG.NODE_YAML_PATH)

    def load_config(self, cfg):
        with open(cfg, 'r') as f:
            self.node_info = yaml.safe_load(f)

    @staticmethod
    def find_overcloud_ips():
        ret, res = commands.getstatusoutput('opnfv-util undercloud '
                                            'stack "source '
                                            '/home/stack/stackrc; nova list"')
        if ret != 0:
            raise TripleOManagerException("Error unable to issue nova list "
                                          "on undercloud.  Please verify "
                                          "undercloud is up")
        else:
            return re.findall('ctlplane=([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', res)

    @staticmethod
    def introspect_node(node, cmd):
        try:
            stdout, (stderr, rc) = node.execute(cmd)
        except processutils.ProcessExecutionError as e:
            raise TripleOManagerException("Error while executing {} on node "
                                          "{}: {}".format(cmd, node.address,
                                                          e.message))
        return stdout.rstrip()

    def gen_node_info(self):
        overcloud_ip_list = TripleOManager.find_overcloud_ips()

        for node_ip in overcloud_ip_list:
            node = Node('intro-%s' % node_ip, address=node_ip,
                        user=self.overcloud_user)
            node_mac = None
            virsh_domain = None
            server_name = self.introspect_node(node, 'hostname')
            if 'overcloud-controller' in server_name:
                node_type = 'controller'
            elif 'overcloud-novacompute' in server_name:
                node_type = 'compute'
            else:
                raise TripleOManagerException('Unknown type '
                                              '(controller/compute) %s '
                                              % server_name)
            try:
                commands.getstatusoutput('ping -c 1 %s' % node_ip)
                ret, res = commands.getstatusoutput('/usr/sbin/arp -a '
                                                    '%s' % node_ip)
                node_mac = \
                    re.search('([0-9a-z]+:){5}[0-9a-z]+', res).group(0)
                virsh_domain = \
                    DeploymentCloner().get_virtual_node_name_from_mac(node_mac)
            except AttributeError:
                LOG.warning("Unable to find MAC address for node {"
                            "}".format(node_ip))

            # find ovs controller and manager
            ovs_controller = self.introspect_node(
                node, 'sudo ovs-vsctl get-controller br-int')
            ovs_managers = self.introspect_node(
                node, 'sudo ovs-vsctl get-manager').split("\n")
            self.node_info['servers'][server_name] = {
                 'address': node_ip,
                 'user': self.overcloud_user,
                 'type': node_type,
                 'orig-ctl-mac': node_mac,
                 'vNode-name': virsh_domain,
                 'ovs-controller': ovs_controller,
                 'ovs-managers': ovs_managers}

    @staticmethod
    def write_out_yaml_config(config, path):
        with open(path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)


class TripleOManagerException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


def main():
    TripleOManager().start()

if __name__ == '__main__':
    main()
