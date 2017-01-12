#
# Copyright (c) 2015 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#
from ssh_util import SshUtil


class NodeManager(object):

    env_nodes = []
    env_node_dict = {}
    primary_controller = None

    def __init__(self, config=None, ssh_key_file=None):
        self.ssh_key_file = ssh_key_file
        if config is not None:
            for (node_name, node_config) in config.iteritems():
                self.add_node(node_name, node_config)

    def add_node(self, node_name, node_config):
        from node import Node
        if not node_config.get('address'):
            raise NodeManagerException("IP address missing from node_config:"
                                       " {}".format(node_config))
        node = Node(node_name, dict=node_config,
                    ssh_key_file=self.ssh_key_file)
        self.env_nodes.append(node)
        self.env_node_dict[node_name] = node
        return node

    def get_nodes(self):
        return self.env_nodes

    def get_node(self, name):
        return self.env_node_dict[name]

    @classmethod
    def gen_ssh_config(cls, node):
        if node not in cls.env_nodes:
            cls.env_nodes.append(node)
        SshUtil.gen_ssh_config(cls.env_nodes)


class NodeManagerException(Exception):
    def __init__(self, value):
        self.value = value
