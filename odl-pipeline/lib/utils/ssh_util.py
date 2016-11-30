'''
Created on Mar 14, 2016

@author: enikher
'''
import os
home = os.getenv("HOME")
SSH_CONFIG={'TMP_SSH_CONFIG': "./tmp/ssh_config",
            'ID_RSA_PATH': "%s/.ssh/id_rsa" % home}

class SshUtil(object):

    @staticmethod
    def gen_ssh_config(node_list):
        config = ["UserKnownHostsFile=/dev/null",
                  "StrictHostKeyChecking=no",
                  "ForwardAgent yes",
                  "GSSAPIAuthentication=no",
                  "LogLevel ERROR"]
        for node in node_list:
            config.append(node.to_ssh_config())
        with open(SSH_CONFIG['TMP_SSH_CONFIG'], 'w') as f:
            f.write('\n'.join(config))

    @staticmethod
    def get_config_file_path():
        return SSH_CONFIG['TMP_SSH_CONFIG']

    @staticmethod
    def get_id_rsa():
        return (SSH_CONFIG['ID_RSA_PATH'])
