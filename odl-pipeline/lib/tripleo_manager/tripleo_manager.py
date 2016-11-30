import os
import copy
import yaml
from novaclient.client import Client as nova
from novaclient import api_versions
import ironicclient.client
from neutronclient.v2_0.client import Client as neutron
from keystoneauth1 import identity
from keystoneauth1 import session

from utils.utils_log import log_enter_exit, for_all_methods, LOG
from utils.service import Service
from utils.processutils import execute
from utils.shutil import shutil
from utils.node_manager import NodeManager


@for_all_methods(log_enter_exit)
class TripleOManager(Service):

    def __init__(self):
        self.auth = None
        self.session = None
        self.novacl = self._get_nova_client()
        self.ironiccl = self._get_ironic_client()
        self.neutroncl = self._get_neutron_client()

    def create_cli_parser(self, parser):
        parser.add_argument('--out', help="where env_info should go to",
                            required=True)
        return parser

    def run(self, sys_args, config):
        self.gen_node_info()
        self.prepare_for_ci_pipeline()
        self.gen_env_info(sys_args, config)
        self.gen_virtual_deployment_info(sys_args, config)

    def gen_virtual_deployment_info(self, sys_args, config):
        pass

    def prepare_for_ci_pipeline(self):
        node_manager = NodeManager(config=self.node_info['servers'])
        for node in node_manager.get_nodes():

            # Check is ODL runs on this node
            self.node_info['servers'][node.name]['ODL'] = {}
            rv, _ = node.execute('ps aux |grep -v grep |grep karaf',
                                 as_root=True, check_exit_code=[0, 1])
            if 'java' in rv:
                self.node_info['servers'][node.name]['ODL']['active'] = True

            if (node.is_dir('/opt/opendaylight') or
                    node.is_file('/opt/opendaylight-was-there')):
                self.node_info['servers'][node.name]['ODL']['dir_exsist'] = \
                    True
                # Remove existing ODL version
                node.execute('touch /opt/opendaylight-was-there', as_root=True)
                node.execute('rm -rf /opt/opendaylight', as_root=True)

            # Store ovs controller info
            rv, _ = node.execute('ovs-vsctl get-controller br-int',
                                 as_root=True)
            self.node_info['servers'][node.name]['ovs-controller'] = \
                rv.replace('\n', '')

            # Disconnect ovs
            node.execute('ovs-vsctl del-controller br-int', as_root=True)

    def gen_env_info(self, sys_args, config):
        shutil.mkdir_if_not_exsist(sys_args.out)
        self.write_out_yaml_config(self.node_info, sys_args.out + '/node.yaml')

        # copy ssh key
        shutil.copy('to', '/home/stack/.ssh/id_rsa',
                    sys_args.out + '/undercloud_ssh/')
        shutil.copy('to', '/home/stack/.ssh/id_rsa.pub',
                    sys_args.out + '/undercloud_ssh/')
        # copy rc files
        shutil.copy('to', '/home/stack/stackrc', sys_args.out)
        shutil.copy('to', '/home/stack/overcloudrc', sys_args.out)

    def gen_node_info(self):
        for network in self.neutroncl.list_networks()['networks']:
            if network['name'] == 'ctlplane':
                ctlplane_id = network['id']
        if hasattr(self, 'node_info') and self.node_info:
            return self.node_info
        self.node_info = {'servers': {}}
        for server in self.novacl.servers.list():
            if 'overcloud-controller' in server.name:
                type = 'controller'
            elif 'overcloud-novacompute' in server.name:
                type = 'compute'
            else:
                raise Exception('Unknown type (controller/compute) %s '
                                % server.name)
            ctlplane_mac = None
            for interface in server.interface_list():
                if interface.net_id == ctlplane_id:
                    ctlplane_mac = interface.mac_addr
            if not ctlplane_mac:
                raise Exception('Could not find mac address for ctl-plane for '
                                'server %s' % server.name)
            self.node_info['servers'][server.name] = {
                'address': self.get_address_of_node(server=server),
                'user': 'heat-admin',
                'type': type,
                'orig-ctl-mac': ctlplane_mac}

    def write_out_yaml_config(self, config, path):
        with open(path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

    def _check_credentials(self):
        for cred in ['OS_USERNAME', 'OS_PASSWORD',
                     'OS_TENANT_NAME', 'OS_AUTH_URL']:
            if not os.environ.get(cred):
                raise Exception('Use export %s=...' % cred)

    def create_auth(self):
        self._check_credentials()
        if not self.auth:
            self.auth = identity.Password(
                auth_url=os.environ['OS_AUTH_URL'],
                username=os.environ['OS_USERNAME'],
                password=os.environ['OS_PASSWORD'],
                project_name=os.environ['OS_TENANT_NAME'])
        if not self.session:
            self.session = session.Session(auth=self.auth)

    def _get_nova_client(self):
        self.create_auth()
        return nova(api_versions.APIVersion("2.0"), session=self.session)

    def _get_ironic_client(self):
        self.create_auth()
        return ironicclient.client.get_client(1, session=self.session)

    def _get_neutron_client(self):
        self.create_auth()
        return neutron(session=self.session)

    def get_node_name_by_ilo_address(self, ilo_address):
        try:
            node_name = None
            for node in self.ironiccl.node.list():
                nova_uuid = node.instance_uuid
                if ilo_address == self.ironiccl.node.get_by_instance_uuid(
                                      nova_uuid).driver_info['ilo_address']:
                    node_name = self.novacl.servers.find(id=nova_uuid).name
                    break
            if not node_name:
                raise Exception('Cannot get nova instance for ilo address %s'
                                % ilo_address)
            return node_name
        except Exception as ex:
            LOG.error('Unsupported installer platform.')
            raise ex

    def get_address_of_node(self, server_name=None, server=None):
        if not (server_name or server):
            raise Exception('Either server_name or server needs to be given')
        if server_name:
            try:
                for server in self.novacl.servers.list():
                    if server.name == server_name:
                        return server.addresses['ctlplane'][0]['addr']
            except Exception as ex:
                LOG.error('Unsupported installer platform.')
                raise ex
        if server:
            return server.addresses['ctlplane'][0]['addr']


def main():
    main = TripleOManager()
    main.start()

if __name__ == '__main__':
    main()
