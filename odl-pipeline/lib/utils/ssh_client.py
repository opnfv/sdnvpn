#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#
from processutils import execute
from ssh_util import SshUtil
from node_manager import NodeManager
import os
from utils_log import LOG
import glob


class SSHClient(object):

    def __init__(self, node):
        self.node = node

    def execute(self, cmd, **kwargs):
        if 'log_true' in kwargs:
            if kwargs['log_true']:
                LOG.info('Node: %s Executing: %s' % (self.node.name, cmd))
            kwargs.pop('log_true')
        NodeManager.gen_ssh_config(self.node)
        if not isinstance(cmd, str):
            cmd = ' '.join(cmd)
        cmd_addition = ['ssh', '-i', SshUtil.get_id_rsa(), '-F',
                        SshUtil.get_config_file_path(),
                        self.node.name]
        if self.node.password:
            cmd_addition = ['sshpass', '-p', self.node.password] + cmd_addition
        if 'as_root' in kwargs:
            kwargs.pop('as_root')
            cmd = 'sudo ' + cmd
        cmd_addition.append(cmd)
        return execute(cmd_addition, **kwargs)

    def copy(self, direction, local_path, remote_path, **kwargs):
        all_files = None
        if direction is 'to':
            msg = ('Copying file %s to %s:%s' % (local_path, self.node.name,
                                                 remote_path))
            if self.node.is_dir(remote_path):
                pass
            elif remote_path[-1:] == '/':
                self.node.create_path_if_not_exsist(remote_path)
            else:
                # Remove the file
                self.execute('rm -f %s' % remote_path, as_root=True)
                self.node.create_path_if_not_exsist(
                    os.path.dirname(remote_path))
            if '*' in local_path:
                all_files = glob.glob(local_path)
        else:
            if local_path[-1:] == '/':
                execute('mkdir -p %s' % local_path)
            msg = ('Copying file from %s:%s to %s' % (self.node.name,
                                                      remote_path,
                                                      local_path))
        LOG.info(msg)
        if all_files:
            for one_file in all_files:
                return self._copy(direction, one_file, remote_path, **kwargs)
        else:
            return self._copy(direction, local_path, remote_path, **kwargs)

    def _copy(self, direction, local_path, remote_path, **kwargs):
        # TODO create dir is not existing
        NodeManager.gen_ssh_config(self.node)
        cmd = ['scp', '-i', SshUtil.get_id_rsa(), '-F',
               SshUtil.get_config_file_path()]
        if direction == 'to':
            if os.path.isdir(local_path):
                cmd.append('-r')
            cmd = cmd + [local_path,
                         ('%s:%s') % (self.node.name, remote_path)]
        if direction == 'from':
            if self.node.is_dir(remote_path):
                cmd.append('-r')
            cmd = cmd + [('%s:%s') % (self.node.name, remote_path),
                         local_path]
        if self.node.password:
            cmd = ['sshpass', '-p', self.node.password] + cmd
        return execute(cmd, **kwargs)
