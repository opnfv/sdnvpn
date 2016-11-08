import yaml
import os

import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils

logger = ft_logger.Logger("sndvpn_test_config").getLogger()


class CommonConfig(object):
    def __init__(self):
        self.repo_path = os.environ['repos_dir'] + '/sdnvpn/'
        self.config_file = self.repo_path + 'test/functest/config.yaml'
        self.keyfile_path = self.repo_path + 'test/functest/id_rsa'
        self.test_db = ft_utils.get_functest_config("results.test_db_url")
        self.line_length = 90  # length for the summary table
        self.vm_boot_timeout = 180
        self.default_flavor = ft_utils.get_parameter_from_yaml(
            "defaults.flavor", self.config_file)
        self.image_filename = ft_utils.get_functest_config(
            "general.openstack.image_file_name")
        self.image_format = ft_utils.get_functest_config(
            "general.openstack.image_disk_format")
        self.image_path = '{0}/{1}'.format(
            ft_utils.get_functest_config(
                "general.directories.dir_functest_data"),
            self.image_filename)


class ConfigFromDict(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)


def get_testcase_config(config_file, testcase):
    with open(config_file) as f:
        testcases_yaml = yaml.safe_load(f)
    test_config = testcases_yaml['testcases'].get(testcase, None)
    if test_config is None:
        logger.error('Test {0} configuration is not present in {1}'
                     .format(testcase, config_file))
    return ConfigFromDict(**test_config)
