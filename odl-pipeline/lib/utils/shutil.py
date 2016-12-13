#
# Copyright (c) 2015 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#
import os
import glob
import processutils as putils


class shutil():
    '''
    classdocs
    '''
    @staticmethod
    def mkdir_if_not_exsist(path):
        if not path:
            raise Exception('Path should not be empty.')
        putils.execute(["mkdir", "-p", path])

    @staticmethod
    def copy(direction, src, dst, **kwargs):
        if direction == 'from':
            dst_tmp = dst
            dst = src
            src = dst_tmp
        if src[-1:] == '*':
            files = glob.glob(src)
            for file in files:
                shutil._copy(file, dst, **kwargs)
        else:
            shutil._copy(src, dst, **kwargs)

    @staticmethod
    def _copy(src, dst, **kwargs):
        if os.path.isfile(src):
            if dst[-1:] == '/':
                shutil.mkdir_if_not_exsist(dst)
            putils.execute(['cp', src, dst], **kwargs)
        else:
            putils.execute(['cp', '-R', src, dst], **kwargs)

    @staticmethod
    def rm(path, **kwargs):
        putils.execute(['rm', '-rf', path], **kwargs)

    @staticmethod
    def mv(src, dst):
        putils.execute(["mv", src, dst])

    @staticmethod
    def get_all_files_in_path(path):
        if os.path.exists(path):
            return putils.execute(['l', path])

    @staticmethod
    def replace_string_in_file(file, str, replace):
        with open(file, 'r') as f:
            string = f.read()
        string = string.replace(str, replace)
        with open(file, 'w+') as f:
            f.write(string)
