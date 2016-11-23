import yaml
import os

import functest.utils.functest_constants as ft_constants
import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils

logger = ft_logger.Logger("sndvpn_test_config").getLogger()


class CommonConfig(object):
    """
    Common configuration parameters across testcases
    """

    def __init__(self):
        self.repo_path = os.path.join(ft_constants.SDNVPN_REPO_DIR)
        self.config_file = os.path.join(self.repo_path,
                                        'test/functest/config.yaml')
        self.keyfile_path = os.path.join(self.repo_path,
                                         'test/functest/id_rsa')
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


class TestcaseConfig(object):
    """
    Configuration for a testcase.
    Parse config.yaml into a dict and create an object out of it.
    """

    def __init__(self, testcase):
        common_config = CommonConfig()
        test_config = None
        with open(common_config.config_file) as f:
            testcases_yaml = yaml.safe_load(f)
            test_config = testcases_yaml['testcases'].get(testcase, None)
        if test_config is None:
            logger.error('Test {0} configuration is not present in {1}'
                         .format(testcase, common_config.config_file))
        # Update class fields with configuration variables dynamically
        self.__dict__.update(**test_config)
