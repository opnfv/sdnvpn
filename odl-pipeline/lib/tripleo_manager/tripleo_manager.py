import os
import commands
import paramiko
import re
import yaml

from utils import processutils
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
        self.node_info = {'servers': []}
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
            if config is not False:
                self.load_config(sys_args.pod_config)
            elif not bool(self.node_info['servers']):
                raise TripleOManagerException("No config found for cleaning "
                                              "deployment.  Please either "
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
                node.execute('rm -rf /opt/opendaylight', as_root=True)

            # Disconnect ovs
            node.execute('ovs-vsctl del-controller br-int', as_root=True)
            node.execute('ovs-vsctl del-manager')

        # Bring ODL up back
        LOG.info("Installing new OpenDaylight")
        self.reinstall_odl(odl_node, odl_tarball)

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

        # Reconnect OVS instances
        LOG.info("Reconnecting OVS instances")
        for node in node_manager.get_nodes():
            self.reconnect_ovs(node)

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

    def introspect_node(self, ip, cmd):

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(ip, username=self.overcloud_user)
        except paramiko.SSHException as e:
            raise TripleOManagerException("Unable to ssh into overcloud node "
                                          "with ip {}, full stack trace is "
                                          "{}".format(ip, e.message))
        stdin, stdout, stderr = ssh.exec_command(cmd)
        if stderr.rstrip() != '':
            raise TripleOManagerException("Error while executing {} on node "
                                          "{}: {}".format(cmd, ip, stderr))
        return stdout.rstrip()

    def gen_node_info(self):
        overcloud_ip_list = self.find_overcloud_ips()

        for node_ip in overcloud_ip_list:
            node_mac = None
            virsh_domain = None
            server_name = self.introspect_node(node_ip, 'hostname')
            if 'overcloud-controller' in server_name:
                node_type = 'controller'
            elif 'overcloud-novacompute' in server_name:
                node_type = 'compute'
            else:
                raise TripleOManagerException('Unknown type '
                                              '(controller/compute) %s '
                                              % server_name)
            try:
                node_mac = re.match('([0-9a-z]+:){5}[0-9a-z]+',
                                    processutils.execute('arp -a ' +
                                                         node_ip)).group(0)
                virsh_domain = \
                    DeploymentCloner.get_virtual_node_name_from_mac(node_mac)
            except AttributeError:
                LOG.warning("Unable to find MAC address for node {"
                            "}".format(node_ip))

            # find ovs controller and manager
            ovs_controller = self.introspect_node(
                node_ip, 'sudo ovs-vsctl get-controller br-int')
            ovs_managers = self.introspect_node(
                node_ip, 'sudo ovs-vsctl get-manager').split("\n")
            self.node_info['servers'].append(
                {'name': server_name,
                 'address': node_ip,
                 'user': self.overcloud_user,
                 'type': node_type,
                 'orig-ctl-mac': node_mac,
                 'vNode-name': virsh_domain,
                 'ovs-controller': ovs_controller,
                 'ovs-managers': ovs_managers})

    @staticmethod
    def write_out_yaml_config(config, path):
        with open(path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

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
        node.execute('puppet apply -e "include opendaylight"'
                     '--modulepath=/etc/puppet/modules/'
                     '--verbose --debug --trace --detailed-exitcodes',
                     check_exit_code=[2], as_root=True)

    @staticmethod
    def reconnect_ovs(node):
        LOG.info('Connecting OpenVSwitch to controller on node %s'% node.name)
        ovs_controller = node.config.get('ovs-controller')
        node.execute('ovs-vsctl set-controller br-int %s'
                     % ovs_controller, as_root=True)
        ovs_manager_str = ' '.join(node.config.get('ovs-managers'))
        node.execute('ovs-vsctl set-manager %s' % ovs_manager_str,
                     as_root=True)


def main():
    TripleOManager().start()

if __name__ == '__main__':
    main()


class TripleOManagerException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value
