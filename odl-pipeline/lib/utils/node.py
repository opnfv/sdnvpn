'''
Created on Mar 3, 2016

@author: enikher
'''
from ssh_client import SSHClient
from ssh_util import SshUtil
from utils_log import LOG, log_enter_exit, for_all_methods
import glob


@for_all_methods(log_enter_exit)
class Node(object):
    '''
    classdocs
    '''

    def __init__(self, name, address=None, port=None,
                 user=None, password=None, jump=None, dict=None):
        self.name = name
        self.address = address
        self.jump = jump
        self.user = user
        self.port = port
        self.password = password
        if dict:
            self.read_from_dic(dict)
        self.sshc = SSHClient(self)
        self.has_access = False
        self.config = dict

    def read_from_dic(self, dic):
        allowed_keys = ['address', 'user', 'jump', 'password', 'port']
        for (key, value) in dic.iteritems():
            if key in allowed_keys:
                setattr(self, key, value)

    def ping(self, ip):
        self.execute(['ping', '-c', '1', ip])

    def execute(self, cmd, **kwargs):
        return self.sshc.execute(cmd, **kwargs)

    def chown(self, user, path):
        self.execute('chown -R %(user)s:%(user)s %(path)s' % {'user': user,
                                                              'path': path},
                     as_root=True)

    def is_dir(self, path):
        rv, _ = self.execute('test -d %s && echo yes' % path, check_exit_code=[0, 1])
        if rv == 'yes\n':
            return True
        else:
            return False

    def is_file(self, path):
        rv, _ = self.execute('test -f %s && echo yes' % path, check_exit_code=[0, 1])
        if rv == 'yes\n':
            return True
        else:
            return False

    def reboot(self):
        self.execute('reboot', as_root=True, check_exit_code=[255])

    def create_path_if_not_exsist(self, path, **kwargs):
        return self.sshc.execute('mkdir -p %s' % path, **kwargs)

    def copy(self, direction, local_path, remote_path, **kwargs):
        return self.sshc.copy(direction, local_path, remote_path, **kwargs)

    def to_ssh_config(self):
        config = ["Host %s" % self.name,
                  "    Hostname %s" %
                  (self.address if self.address else self.name)]
        if self.jump:
            config.append("    ProxyCommand ssh -F %(config_path)s "
                          "-W %%h:%%p %(name)s"
                          % {'config_path': SshUtil.get_config_file_path(),
                             'name': self.jump.name})
        if self.user:
            config.append("    user %s" % self.user)
        if self.port:
            config.append("    port %s" % self.port)
        return '\n'.join(config)
