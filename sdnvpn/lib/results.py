#!/usr/bin/python
#
# Copyright (c) 2017 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
import logging
import time

import functest.utils.functest_utils as ft_utils

logger = logging.getLogger('sdnvpn-results')


class Results(object):

    def __init__(self, line_length):
        self.line_length = line_length
        self.test_result = "PASS"
        self.summary = ""
        self.details = []
        self.num_tests = 0
        self.num_tests_failed = 0

    def get_ping_status(self,
                        vm_source,
                        vm_target,
                        expected="PASS", timeout=30):
        ip_target = vm_target.networks.itervalues().next()[0]
        self.get_ping_status_target_ip(vm_source, vm_target.name,
                                       ip_target, expected, timeout)

    def get_ping_status_target_ip(self,
                                  vm_source,
                                  target_name,
                                  ip_target,
                                  expected="PASS", timeout=30):
        console_log = vm_source.get_console_output()
        ip_source = vm_source.networks.itervalues().next()[0]
        if "request failed" in console_log:
            # Normally, cirros displays this message when userdata fails
            logger.debug("It seems userdata is not supported in "
                         "nova boot...")
            return False
        else:
            tab = ("%s" % (" " * 53))
            expected_result = 'can ping' if expected == 'PASS' \
                              else 'cannot ping'
            test_case_name = ("'%s' %s '%s'" %
                              (vm_source.name,
                               expected_result,
                               target_name))
            logger.debug("%sPing\n%sfrom '%s' (%s)\n%sto '%s' (%s).\n"
                         "%s-->Expected result: %s.\n"
                         % (tab, tab, vm_source.name, ip_source,
                            tab, target_name, ip_target,
                            tab, expected_result))
            while True:
                console_log = vm_source.get_console_output()
                # the console_log is a long string, we want to take
                # the last 4 lines (for example)
                lines = console_log.split('\n')
                last_n_lines = lines[-5:]
                if ("ping %s OK" % ip_target) in last_n_lines:
                    msg = ("'%s' can ping '%s'"
                           % (vm_source.name, target_name))
                    if expected == "PASS":
                        logger.debug("[PASS] %s" % msg)
                        self.add_success(test_case_name)
                    else:
                        logger.debug("[FAIL] %s" % msg)
                        self.add_failure(test_case_name)
                        logger.debug("\n%s" % last_n_lines)
                    break
                elif ("ping %s KO" % ip_target) in last_n_lines:
                    msg = ("'%s' cannot ping '%s'" %
                           (vm_source.name, target_name))
                    if expected == "FAIL":
                        logger.debug("[PASS] %s" % msg)
                        self.add_success(test_case_name)
                    else:
                        logger.debug("[FAIL] %s" % msg)
                        self.add_failure(test_case_name)
                    break
                time.sleep(1)
                timeout -= 1
                if timeout == 0:
                    logger.debug("[FAIL] Timeout reached for '%s'. "
                                 "No ping output captured in the console log"
                                 % vm_source.name)
                    self.add_failure(test_case_name)
                    break

    def add_to_summary(self, num_cols, col1, col2=""):
        if num_cols == 0:
            self.summary += ("+%s+\n" % (col1 * (self.line_length - 2)))
        elif num_cols == 1:
            self.summary += ("| " + col1.ljust(self.line_length - 3) + "|\n")
        elif num_cols == 2:
            self.summary += ("| %s" % col1.ljust(7) + "| ")
            self.summary += (col2.ljust(self.line_length - 12) + "|\n")
            if col1 in ("FAIL", "PASS"):
                self.details.append({col2: col1})
                self.num_tests += 1
                if col1 == "FAIL":
                    self.num_tests_failed += 1

    def record_action(self, msg):
        """Record and log an action and display it in the summary."""
        logger.info(msg)
        self.add_to_summary(1, msg)

    def add_failure(self, test):
        self.add_to_summary(2, "FAIL", test)
        self.test_result = "FAIL"

    def add_success(self, test):
        self.add_to_summary(2, "PASS", test)

    def add_subtest(self, test, successful):
        if successful:
            self.add_success(test)
        else:
            self.add_failure(test)

    def check_ssh_output(self, vm_source, vm_target,
                         expected, timeout=30):
        console_log = vm_source.get_console_output()
        ip_source = vm_source.networks.itervalues().next()[0]
        ip_target = vm_target.networks.itervalues().next()[0]

        if "request failed" in console_log:
            # Normally, cirros displays this message when userdata fails
            logger.debug("It seems userdata is not supported in "
                         "nova boot...")
            return False
        else:
            tab = ("%s" % (" " * 53))
            test_case_name = ("[%s] returns 'I am %s' to '%s'[%s]" %
                              (ip_target, expected,
                               vm_source.name, ip_source))
            logger.debug("%sSSH\n%sfrom '%s' (%s)\n%sto '%s' (%s).\n"
                         "%s-->Expected result: %s.\n"
                         % (tab, tab, vm_source.name, ip_source,
                            tab, vm_target.name, ip_target,
                            tab, expected))
            while True:
                console_log = vm_source.get_console_output()
                # the console_log is a long string, we want to take
                # the last 4 lines (for example)
                lines = console_log.split('\n')
                last_n_lines = lines[-5:]
                if ("%s %s" % (ip_target, expected)) in last_n_lines:
                    logger.debug("[PASS] %s" % test_case_name)
                    self.add_success(test_case_name)
                    break
                elif ("%s not reachable" % ip_target) in last_n_lines:
                    logger.debug("[FAIL] %s" % test_case_name)
                    self.add_failure(test_case_name)
                    break
                time.sleep(1)
                timeout -= 1
                if timeout == 0:
                    logger.debug("[FAIL] Timeout reached for '%s'."
                                 " No ping output captured in the console log"
                                 % vm_source.name)
                    self.add_failure(test_case_name)
                    break

    def ping_ip_test(self, address):
        ping = "ping %s -c 10" % address
        testcase_name = "Ping IP %s" % address
        logger.debug(testcase_name)
        exit_code = ft_utils.execute_command(ping)

        if exit_code != 0:
            self.add_failure(testcase_name)
        else:
            self.add_success(testcase_name)

    def compile_summary(self):
        success_message = "All the subtests have passed."
        failure_message = "One or more subtests have failed."

        self.add_to_summary(0, "=")
        logger.info("\n%s" % self.summary)
        if self.test_result == "PASS":
            logger.info(success_message)
        else:
            logger.info(failure_message)

        return {"status": self.test_result, "details": self.details}
