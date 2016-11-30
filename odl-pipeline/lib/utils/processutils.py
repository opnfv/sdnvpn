'''
Created on Jan 16, 2016
This file contains utils used by all other
@author: enikher
'''

import utils_log as log
import os
import shlex
import six
import re
import signal
import random
import subprocess
from time import sleep
from threading import Thread
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

LOG = log.LOG
LOG_LEVEL = log.LOG_LEVEL


def _subprocess_setup():
    # Python installs a SIGPIPE handler by default. This is usually not what
    # non-Python subprocesses expect.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# NOTE(flaper87): The following globals are used by `mask_password`
_SANITIZE_KEYS = ['adminPass', 'admin_pass', 'password', 'admin_password']

# NOTE(ldbragst): Let's build a list of regex objects using the list of
# _SANITIZE_KEYS we already have. This way, we only have to add the new key
# to the list of _SANITIZE_KEYS and we can generate regular expressions
# for XML and JSON automatically.
_SANITIZE_PATTERNS_2 = []
_SANITIZE_PATTERNS_1 = []


def mask_password(message, secret="***"):
    """Replace password with 'secret' in message.

    :param message: The string which includes security information.
    :param secret: value with which to replace passwords.
    :returns: The unicode value of message with the password fields masked.

    For example:

    >>> mask_password("'adminPass' : 'aaaaa'")
    "'adminPass' : '***'"
    >>> mask_password("'admin_pass' : 'aaaaa'")
    "'admin_pass' : '***'"
    >>> mask_password('"password" : "aaaaa"')
    '"password" : "***"'
    >>> mask_password("'original_password' : 'aaaaa'")
    "'original_password' : '***'"
    >>> mask_password("u'original_password' :   u'aaaaa'")
    "u'original_password' :   u'***'"
    """
    try:
        message = six.text_type(message)
    except UnicodeDecodeError:
        # NOTE(jecarey): Temporary fix to handle cases where message is a
        # byte string.   A better solution will be provided in Kilo.
        pass

    # NOTE(ldbragst): Check to see if anything in message contains any key
    # specified in _SANITIZE_KEYS, if not then just return the message since
    # we don't have to mask any passwords.
    if not any(key in message for key in _SANITIZE_KEYS):
        return message

    substitute = r'\g<1>' + secret + r'\g<2>'
    for pattern in _SANITIZE_PATTERNS_2:
        message = re.sub(pattern, substitute, message)

    substitute = r'\g<1>' + secret
    for pattern in _SANITIZE_PATTERNS_1:
        message = re.sub(pattern, substitute, message)

    return message


class ProcessExecutionError(Exception):
    def __init__(self, stdout=None, stderr=None, exit_code=None, cmd=None,
                 description=None):
        self.exit_code = exit_code
        self.stderr = stderr
        self.stdout = stdout
        self.cmd = cmd
        self.description = description

        if description is None:
            description = "Unexpected error while running command."
        if exit_code is None:
            exit_code = '-'
        message = ("%s\nCommand: %s\nExit code: %s\nStdout: %r\nStderr: %r"
                   % (description, cmd, exit_code, stdout, stderr))
        super(ProcessExecutionError, self).__init__(message)


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    queue.put("##Finished##")
    out.close()


def execute(cmd, **kwargs):
    """Helper method to shell out and execute a command through subprocess.

    Allows optional retry.

    :param cmd:             Passed to subprocess.Popen.
    :type cmd:              list - will be converted if needed
    :param process_input:   Send to opened process.
    :type proces_input:     string
    :param check_exit_code: Single bool, int, or list of allowed exit
                            codes.  Defaults to [0].  Raise
                            :class:`ProcessExecutionError` unless
                            program exits with one of these code.
    :type check_exit_code:  boolean, int, or [int]
    :param delay_on_retry:  True | False. Defaults to True. If set to True,
                            wait a short amount of time before retrying.
    :type delay_on_retry:   boolean
    :param attempts:        How many times to retry cmd.
    :type attempts:         int
    :param run_as_root:     True | False. Defaults to False. If set to True,
        or as_root          the command is prefixed by the command specified
                            in the root_helper kwarg.
                            execute this command. Defaults to false.
    :param shell:           whether or not there should be a shell used to
    :type shell:            boolean
    :param loglevel:        log level for execute commands.
    :type loglevel:         int.  (Should be logging.DEBUG or logging.INFO)
    :param non_blocking     Execute in background.
    :type non_blockig:      boolean
    :returns:               (stdout, (stderr, returncode)) from process execution
    :raises:                :class:`UnknownArgumentError` on
                            receiving unknown arguments
    :raises:                :class:`ProcessExecutionError`
    """
    process_input = kwargs.pop('process_input', None)
    check_exit_code = kwargs.pop('check_exit_code', [0])
    ignore_exit_code = False
    delay_on_retry = kwargs.pop('delay_on_retry', True)
    attempts = kwargs.pop('attempts', 1)
    run_as_root = kwargs.pop('run_as_root', False) or kwargs.pop('as_root', False)
    root_helper = kwargs.pop('root_helper', '')
    shell = kwargs.pop('shell', False)
    loglevel = kwargs.pop('loglevel', LOG_LEVEL)
    non_blocking = kwargs.pop('non_blocking', False)

    if not isinstance(cmd, list):
        cmd = cmd.split(' ')

    if run_as_root:
        cmd = ['sudo'] + cmd
    if shell:
        cmd = ' '.join(cmd)
    if isinstance(check_exit_code, bool):
        ignore_exit_code = not check_exit_code
        check_exit_code = [0]
    elif isinstance(check_exit_code, int):
        check_exit_code = [check_exit_code]

    if kwargs:
        raise Exception(('Got unknown keyword args '
                         'to utils.execute: %r') % kwargs)

    while attempts > 0:
        attempts -= 1
        try:
            LOG.log(loglevel, ('Running cmd (subprocess): %s'), cmd)
            _PIPE = subprocess.PIPE  # pylint: disable=E1101

            if os.name == 'nt':
                preexec_fn = None
                close_fds = False
            else:
                preexec_fn = _subprocess_setup
                close_fds = True

            obj = subprocess.Popen(cmd,
                                   stdin=_PIPE,
                                   stdout=_PIPE,
                                   stderr=_PIPE,
                                   close_fds=close_fds,
                                   preexec_fn=preexec_fn,
                                   shell=shell)
            result = None
            if process_input is not None:
                result = obj.communicate(process_input)
            else:
                if non_blocking:
                    queue = Queue()
                    thread = Thread(target=enqueue_output, args=(obj.stdout,
                                                                 queue))
                    thread.deamon = True
                    thread.start()
                    # If you want to read this output later:
                    # try:
                    #     from Queue import Queue, Empty
                    # except ImportError:
                    #     from queue import Queue, Empty  # python 3.x
                    # try:  line = q.get_nowait() # or q.get(timeout=.1)
                    # except Empty:
                    #     print('no output yet')
                    # else: # got line
                    # ... do something with line
                    return queue
                result = obj.communicate()
            obj.stdin.close()  # pylint: disable=E1101
            _returncode = obj.returncode  # pylint: disable=E1101
            LOG.log(loglevel, ('Result was %s') % _returncode)
            if not ignore_exit_code and _returncode not in check_exit_code:
                (stdout, stderr) = result
                sanitized_stdout = mask_password(stdout)
                sanitized_stderr = mask_password(stderr)
                raise ProcessExecutionError(exit_code=_returncode,
                                            stdout=sanitized_stdout,
                                            stderr=sanitized_stderr,
                                            cmd=(' '.join(cmd)) if isinstance(cmd, list) else cmd)
            (stdout, stderr) = result
            return (stdout, (stderr, _returncode))
        except ProcessExecutionError:
            raise
        finally:
            sleep(0)

