#!/bin/python
import os
from utils.utils_log import LOG, for_all_methods, log_enter_exit
from utils.service import Service
from utils.processutils import execute
from utils import utils_yaml
from utils.shutil import shutil
MAX_NODES = 5


@for_all_methods(log_enter_exit)
class TestEnvironment(Service):

    NODE_NAME = 'baremetal'
    TEMPLATES = '../xml/templates'
    NETWORKS = ['br-admin', 'br-private', 'br-public', 'br-storage']

    def run(self, sys_args, config):
        self.BUILD_DIR = '../build/apex-%s' % sys_args.env_number
        self.env = sys_args.env_number
        self.cleanup()
        if sys_args.cleanup:
            return
        if not sys_args.cloner_info or not sys_args.snapshot_disks:
            LOG.error('--cloner-info, --snapshot-disks have to be given if not'
                      ' only cleanup.')
            exit(1)
        node_info = utils_yaml.read_dict_from_yaml(sys_args.cloner_info +
                                                   '/node.yaml')
        nodes = node_info['servers']
        number_of_nodes = len(nodes)
        disk_home = self.BUILD_DIR + '/disks/'
        shutil.mkdir_if_not_exsist(disk_home)
        # Create Snapshots
        for i in range(number_of_nodes):
            disk_name = '%s%s.qcow2' % (self.NODE_NAME, i)
            self.create_snapshot('%s/%s' % (sys_args.snapshot_disks,
                                            disk_name),
                                 '%s/%s' % (disk_home, disk_name))

        # Create Nets is not exsisting
        nets_template = self.TEMPLATES + '/nets/'
        nets_config = self.BUILD_DIR + '/nets/'
        shutil.mkdir_if_not_exsist(nets_config)
        shutil.copy('to', nets_template + '*', nets_config)
        for net in self.NETWORKS:
            xml_path = '%s/%s.xml' % (nets_config, net)
            net_name = '%s-%s' % (net, self.env)
            shutil.replace_string_in_file(xml_path, 'NaMe', self.env)
            if not self.check_if_net_exists(net_name):
                LOG.info('Creating network %s from %s'
                         % (net_name, xml_path))
                execute('virsh net-define ' + xml_path)
                execute('virsh net-start ' + net_name)
                execute('ip addr flush dev ' + net_name, as_root=True)

        # Create virtual Nodes
        dom_template = self.TEMPLATES + '/nodes/baremetalX.xml'
        dom_config = self.BUILD_DIR + '/nodes/baremetalX.xml'
        shutil.mkdir_if_not_exsist(self.BUILD_DIR + '/nodes/')
        LOG.info('Creating virtual Nodes')
        for name, node in nodes.iteritems():
            orig_node_name = node['vNode-name']
            node_name = orig_node_name + '-' + self.env
            LOG.info('Create node %s' % node_name)
            type = node['type']
            if type == 'compute':
                cpu = 2
                mem = 2
            elif type == 'controller':
                cpu = 8
                mem = 10
            else:
                raise Exception('Unknown node type! %s' % type)
            shutil.copy('to', dom_template, dom_config)
            shutil.replace_string_in_file(dom_config, 'NaMe', node_name)
            disk_full_path = os.path.abspath('%s/%s.qcow2' % (disk_home,
                                                              orig_node_name))
            shutil.replace_string_in_file(dom_config, 'DiSk', disk_full_path)
            shutil.replace_string_in_file(dom_config, 'vCpU', str(cpu))
            shutil.replace_string_in_file(dom_config, 'MeMoRy', str(mem))
            shutil.replace_string_in_file(dom_config, 'InDeX', self.env)

            execute('virsh define ' + dom_config)
            execute('virsh start ' + node_name)

            cores_per_environment = 8
            cores = '%s-%s' % (int(self.env) * 8, int(self.env) * 8 +
                               cores_per_environment - 1)
            LOG.info('Pining vCPU of node %s to cores %s' % (node_name, cores))
            for i in range(cpu):
                execute('virsh vcpupin %(node)s %(nodes_cpu)s %(host_cpu)s' %
                        {'node': node_name,
                         'nodes_cpu': i,
                         'host_cpu': cores})

    def check_if_net_exists(self, net):
        rv, _ = execute('virsh net-list')
        if (' ' + net + ' ') in rv:
            return True
        return False

    def create_snapshot(self, orig, path):
        LOG.info('Creating snapshot of %s in %s' % (orig, path))
        execute('qemu-img create -f qcow2 -b %s %s' % (orig, path),
                as_root=True)

    def cleanup(self):
        for i in range(MAX_NODES):
            rv, (_, rc) = execute('virsh destroy %(name)s%(i)s-%(env)s'
                                  % {'i': i, 'env': self.env,
                                     'name': self.NODE_NAME},
                                  check_exit_code=[0, 1])
            if rc == 0:
                LOG.info(rv)
            rv, (_, rc) = execute('virsh undefine %(name)s%(i)s-%(env)s'
                                  % {'i': i, 'env': self.env,
                                     'name': self.NODE_NAME},
                                  check_exit_code=[0, 1])
            if rc == 0:
                LOG.info(rv)
        execute('rm -rf ' + self.BUILD_DIR)

    def create_cli_parser(self, parser):
        parser.add_argument('--env-number', help="Number of the environment",
                            required=True)
        parser.add_argument('--cloner-info', help="Path to the cloner-info",
                            required=False)
        parser.add_argument('--snapshot-disks', help="Path to the snapshots",
                            required=False)
        parser.add_argument('--cleanup', help="Only Cleanup",
                            required=False, action='store_true')
        return parser


def main():
    main = TestEnvironment()
    main.start()

if __name__ == '__main__':
    main()
