#!/bin/python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#
import os
import re
import time

from utils.processutils import ProcessExecutionError
from tripleo_introspector.tripleo_introspector import TripleOIntrospector
from utils import processutils
from utils.utils_log import LOG, for_all_methods, log_enter_exit
from utils.service import Service
from utils.node_manager import NodeManager
from utils import utils_yaml
from common.constants import EXTERNAL_NET


# Decorator for parsing neutron output
def raw_to_dict(func):
    def func_wrapper(*args, **kwargs):
        data_dict = {}
        kv_pattern = re.compile('^\|\s*([^\s]+)\s*\|\s*([^\s]+)\s*\|$')
        # used for matching values with '{}' which can contain spaces
        kv_pattern2 = re.compile('^\|\s*([^\s]+)\s*\|\s*\{(.+)\}\s*\|$')
        res = func(*args, **kwargs)
        raw_output = res.strip().split('\n')
        for line in raw_output:
            try:
                re_res = re.search(kv_pattern, line)
                if re_res is None:
                    re_res = re.search(kv_pattern2, line)
                if re_res.group(1) != 'Field':
                    data_dict[re_res.group(1)] = re_res.group(2)
            except AttributeError:
                continue
        return data_dict
    return func_wrapper


@for_all_methods(log_enter_exit)
class ODLReInstaller(Service):

    def __init__(self):
        self.netvirt_url = "restconf/operational/network-topology:" \
                           "network-topology/topology/netvirt:1"
        self.nodes = None
        self.odl_node = None
        self.controller_node = None
        self.neutron_ext_net = {}
        self.neutron_ext_subnet = {}

    def run(self, sys_args, config):
        pod_config = sys_args.pod_config
        odl_artifact = sys_args.odl_artifact
        node_config = utils_yaml.read_dict_from_yaml(pod_config)
        # TODO Add validation of incoming node config
        # self.check_node_config()
        self.nodes = NodeManager(node_config['servers']).get_nodes()
        # Copy overcloudrc file to controller
        self._set_controller_node()
        self.copy_rc_to_controller(sys_args.overcloudrc)
        # Read and store external networks + subnets
        self.get_ext_neutron_config()
        # Delete external networks + subnets
        self.delete_ext_neutron_config()
        # copy ODL to all nodes where it need to be copied
        for node in self.nodes:
            node.execute('ovs-vsctl del-controller br-int', as_root=True)
        for node in self.nodes:
            # Check if ODL runs on this node
            rv, _ = node.execute('ps aux |grep -v grep |grep karaf',
                                 as_root=True, check_exit_code=[0, 1])
            if 'java' in rv:
                self.odl_node = node
                LOG.info("ODL node found: {}".format(self.odl_node.name))
                node.execute('systemctl stop opendaylight', as_root=True)

            self.disconnect_ovs(node)

        # Upgrade ODL
        self.reinstall_odl(self.odl_node, odl_artifact)

        # Wait for ODL to come back up
        full_netvirt_url = "http://{}:8081/{}".format(
            self.odl_node.config['address'], self.netvirt_url)
        counter = 1
        while counter <= 10:
            try:
                self.odl_node.execute("curl --fail -u admin:admin {}".format(
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
            self.connect_ovs(node)
        # Sleep for a few seconds to allow TCP connections to come up
        time.sleep(5)
        # Validate OVS instances
        LOG.info("Validating OVS configuration")
        for node in self.nodes:
            self.validate_ovs(node)
        LOG.info("OpenDaylight Upgrade Successful!")

        # Reconfigure external neutron networks
        LOG.info("Reconfiguring Neutron")
        self.reconfigure_neutron()

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
        LOG.info('Deleting Tunnel and Patch interfaces')
        # Note this is required because ODL fails to reconcile pre-created
        # ports
        for br in 'br-int', 'br-ex':
            LOG.info("Checking for ports on {}".format(br))
            try:
                out, _ = node.execute('ovs-vsctl list-ports {} | grep -E '
                                      '"tun|patch"'.format(br),
                                      as_root=True, shell=True)
                ports = out.rstrip().split("\n")
                for port in ports:
                    LOG.info('Deleting port: {}'.format(port))
                    node.execute('ovs-vsctl del-port {} {}'.format(br, port),
                                 as_root=True)
            except ProcessExecutionError:
                LOG.info("No tunnel or patch ports configured")

    @staticmethod
    def connect_ovs(node):
        LOG.info('Connecting OpenVSwitch to controller on node %s' % node.name)
        ovs_manager_str = ' '.join(node.config['ovs-managers'])
        node.execute('ovs-vsctl set-manager %s' % ovs_manager_str,
                     as_root=True)

    @staticmethod
    def validate_ovs(node):
        LOG.info("Validating OVS configuration for node: {}".format(node.name))
        # Validate ovs manager is connected
        out, _ = node.execute('ovs-vsctl show ', as_root=True)
        mgr_search = \
            re.search('Manager\s+\"tcp:[0-9.]+:6640\"\n\s*'
                      'is_connected:\s*true', out)
        if mgr_search is None:
            raise ODLReinstallerException("OVS Manager is not connected")
        else:
            LOG.info("OVS is connected to OVSDB manager")

        # Validate ovs controller is configured
        cfg_controller = node.config['ovs-controller']
        ovs_controller = TripleOIntrospector().get_ovs_controller(node)
        if cfg_controller == '' or cfg_controller is None:
            if ovs_controller is None or ovs_controller == '':
                raise ODLReinstallerException("OVS controller is not set "
                                              "for node: {}"
                                              "".format(node.address))
        elif ovs_controller != cfg_controller:
            raise ODLReinstallerException("OVS controller is not set to the "
                                          "correct pod config value on {}. "
                                          "Config controller: {}, current "
                                          "controller: {}"
                                          "".format(node.address,
                                                    cfg_controller,
                                                    ovs_controller))
        LOG.info("OVS Controller set correctly")
        # Validate ovs controller is connected
        ctrl_search = \
            re.search('Controller\s+\"tcp:[0-9\.]+:6653\"\n\s*'
                      'is_connected:\s*true', out)
        if ctrl_search is None:
            raise ODLReinstallerException("OVS Controller is not connected")
        else:
            LOG.info("OVS is connected to OpenFlow controller")

    def copy_rc_to_controller(self, rc_file):
        if not os.path.isfile(rc_file):
            raise ODLReinstallerException("RC file: {} does not "
                                          "exist!".format(rc_file))
        if 'user' in self.controller_node.config:
            overcloud_path = "/home/{}/overcloudrc".format(
                self.controller_node.config['user'])
        else:
            overcloud_path = "/home/heat-admin/overcloudrc"
        self.controller_node.copy('to', rc_file, overcloud_path)
        LOG.info("overcloudrc copied to node {} to {}".format(
            self.controller_node.name, overcloud_path))

    def _set_controller_node(self):
        for node in self.nodes:
            if 'type' in node.config and node.config['type'] == 'controller':
                self.controller_node = node
                return
        raise ODLReinstallerException("Unable to detect control node")

    @staticmethod
    @raw_to_dict
    def exec_with_creds(node, cmd, **kwargs):
        full_cmd = "'source overcloudrc && {}'".format(cmd)
        res, _ = node.execute(full_cmd, shell=True, **kwargs)
        return res

    def get_ext_neutron_config(self):
        ctrl_node = self.controller_node
        self.neutron_ext_net = self.exec_with_creds(
            ctrl_node, 'neutron net-show {}'.format(EXTERNAL_NET))
        if self.neutron_ext_net:
            LOG.info("External Neutron network found: {}".format(
                self.neutron_ext_net))
            if 'subnets' in self.neutron_ext_net:
                self.neutron_ext_subnet = self.exec_with_creds(
                    ctrl_node, 'neutron subnet-show {}'.format(
                        self.neutron_ext_net['subnets']))
                LOG.info("External Neutron subnet found: {}".format(
                    self.neutron_ext_subnet))
            else:
                LOG.warn("Unable to find external Neutron subnet")
        else:
            LOG.warn("Unable to find external Neutron network")

    def delete_ext_neutron_config(self):
        if self.neutron_ext_subnet:
            ext_sub_id = self.neutron_ext_subnet['id']
            LOG.info("Deleting external neutron subnet: {}".format(ext_sub_id))
            self.exec_with_creds(self.controller_node,
                                 "neutron subnet-delete {}".format(ext_sub_id)
                                 )
            ext_net_id = self.neutron_ext_net['id']
            LOG.info("Deleting external neutron network: {}".format(ext_net_id)
                     )
            self.exec_with_creds(self.controller_node,
                                 "neutron net-delete {}".format(ext_net_id)
                                 )

    def reconfigure_neutron(self):
        if self.neutron_ext_net:
            LOG.info("Reconfiguring External neutron network")
            tenant = self.neutron_ext_net['project_id']
            physnet = self.neutron_ext_net['provider:physical_network']
            net_create_cmd = ("neutron net-create {} "
                              "--router:external=True --tenant-id {} "
                              "--provider:network_type flat "
                              "--provider:physical_network {}"
                              "".format(EXTERNAL_NET, tenant, physnet)
                              )
            self.exec_with_creds(self.controller_node, net_create_cmd)

        else:
            LOG.warn("No external Neutron network to reconfigure")
            return

        if self.neutron_ext_subnet:
            LOG.info("Reconfiguring External neutron subnet")
            subnet_name = self.neutron_ext_subnet['name']
            tenant = self.neutron_ext_subnet['project_id']
            gw = self.neutron_ext_subnet['gateway_ip']
            pool_pattern = re.compile(
                '"start":\s*"(([0-9]+\.){3}[0-9]+)",\s*'
                '"end":\s*"(([0-9]+\.){3}[0-9]+)'
            )

            allocation_match = re.search(
                pool_pattern, self.neutron_ext_subnet['allocation_pools'])
            (pool_start, pool_end) = (allocation_match.group(1),
                                      allocation_match.group(3))
            cidr = self.neutron_ext_subnet['cidr']
            subnet_create_cmd = ("neutron subnet-create "
                                 "--name {} "
                                 "--tenant-id {} "
                                 "--disable-dhcp "
                                 "{} "
                                 "--gateway {} "
                                 "--allocation_pool start={},end={} "
                                 "{}".format(subnet_name, tenant, EXTERNAL_NET,
                                             gw, pool_start, pool_end, cidr)
                                 )
            self.exec_with_creds(self.controller_node, subnet_create_cmd)
        else:
            LOG.info("No external Neutron subnet to reconfigure")
        LOG.info("Neutron reconfigured")

    def create_cli_parser(self, parser):
        parser.add_argument('--pod-config',
                            help="File containing pod configuration",
                            dest='pod_config',
                            required=True)
        parser.add_argument('--odl-artifact',
                            help="Path to Opendaylight tarball to use for "
                                 "upgrade",
                            dest='odl_artifact',
                            required=True)
        parser.add_argument('--credentials',
                            help="Path to OpenStack Credentials RC file",
                            dest='overcloudrc',
                            required=True)
        return parser


class ODLReinstallerException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


def main():
    ODLReInstaller().start()

if __name__ == '__main__':
    main()
