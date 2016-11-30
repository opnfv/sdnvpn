#!/bin/python
import sys
import yaml
import argparse
import traceback
from utils.utils_log import LOG, for_all_methods, log_enter_exit, LOG_PATH
from abc import abstractmethod


class Service(object):

    def start(self):
        try:
            self._run()
        except Exception as ex:
            LOG.error(ex.message)
            LOG.error(traceback.format_exc())
            LOG.error("For more logs check: %(log_path)s"
                      % {'log_path': LOG_PATH})
            sys.exit(1)

    def _run(self):
        parser = self._create_cli_parser()
        sys_args = parser.parse_args()
        config = self.read_config(sys_args)
        self.run(sys_args, config)


    @abstractmethod
    def run(self, sys_args, config):
        # Do something
        return

    @abstractmethod
    def create_cli_parser(self, parser):
        # Read in own sys args
        return parser

    def _create_cli_parser(self):
        parser = argparse.ArgumentParser(description='OVS Debugger')
        # parser.add_argument('-c', '--config', help="Path to config.yaml",
        #                     required=False)
        # parser.add_argument('--boolean', help="",
        #                     required=False, action='store_true')
        return self.create_cli_parser(parser)

    def read_config(self, sys_args):
        if not hasattr(sys_args, 'config'):
            return None
        if not sys_args.config:
            config_path = './etc/config.yaml'
        else:
            config_path = sys_args.config
        try:
            with open(config_path) as f:
                return yaml.load(f)
        except yaml.scanner.ScannerError as ex:
            LOG.error("Yaml file corrupt. Try putting spaces after the "
                      "colons.")
            raise ex

