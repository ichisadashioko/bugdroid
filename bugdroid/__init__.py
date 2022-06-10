import os
import posixpath
import stat
import io
import time
import traceback
import subprocess
import sys
import re

import psutil

AUTO_CREATE_ADB_SERVER = False


def find_running_adb_process():
    pid_list = psutil.pids()
    for pid in pid_list:
        try:
            process_info = psutil.Process(pid)

            executable_filepath = process_info.exe()
            executable_filename = os.path.basename(executable_filepath)
            executable_filename = executable_filename.lower()
            if executable_filename in ['adb', 'adb.exe']:
                return {
                    'pid': pid,
                    'exe': executable_filepath,
                }
        except:
            pass
    return None


def normalize_path_for_command_line_argument(inpath: str):
    inpath = inpath.strip('"')
    # if path has spaces, it must be quoted
    if ' ' in inpath:
        return f'"{inpath}"'
    else:
        return inpath


def normalize_unix_path_separator(inpath: str):
    inpath = inpath.replace('\\', '/')
    return re.sub(r'/+', '/', inpath)


def normalize_path_separator(inpath: str):
    if sys.platform == 'win32':
        inpath = inpath.replace('/', '\\')
        path_components = inpath.split('\\')
        # remove empty string
        path_components = [x for x in path_components if len(x) > 0]
        return '\\'.join(path_components)
    else:
        return normalize_unix_path_separator(inpath)


def execute_shell_command(
    command: str,
    cwd=None,
    timeout=5,
):
    retval = {
        'input': {
            'command': command,
            'cwd': cwd,
            'timeout': timeout,
        },
        'process': None,
        'stdout': None,
        'stderr': None,
        'returncode': None,
        'exception': None,
        'stacktrace': None,
    }

    try:
        ps = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        retval['process'] = ps

        stdout, stderr = ps.communicate(timeout=timeout)
        retval['stdout'] = stdout
        retval['stderr'] = stderr
        retval['returncode'] = ps.returncode
    except Exception as ex:
        stacktrace = traceback.format_exc()
        retval['exception'] = ex
        retval['stacktrace'] = stacktrace

    return retval


class VerboseException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return repr({
            'args': self.args,
            'kwargs': self.kwargs,
        })


class ShellCommandFailedException(VerboseException):
    pass


def assert_shell_success_status(shell_return_value: dict):
    ps: subprocess.Popen = shell_return_value['process']
    ex: Exception = shell_return_value['exception']
    stdout: bytes = shell_return_value['stdout']
    stderr: bytes = shell_return_value['stderr']

    if ps is None:
        raise ShellCommandFailedException(**shell_return_value)

    if ex is not None:
        raise ShellCommandFailedException(**shell_return_value)

    returncode = ps.returncode
    if returncode != 0:
        raise ShellCommandFailedException(**shell_return_value)

    if stderr is None:
        raise ShellCommandFailedException(**shell_return_value)

    if stderr is None:
        raise ShellCommandFailedException(**shell_return_value)

    if len(stderr) != 0:
        raise ShellCommandFailedException(**shell_return_value)


def adb_devices(
    adb_filepath=None,
    timeout=5,
):
    running_adb_process = find_running_adb_process()
    if running_adb_process is None:
        if not AUTO_CREATE_ADB_SERVER:
            raise Exception('No ADB server found. Please start one.')
        else:
            raise Exception('Unimplemented: auto-create ADB server')

    if adb_filepath is None:
        adb_filepath = running_adb_process['exe']

    adb_filepath = normalize_path_separator(adb_filepath)
    adb_filepath = normalize_path_for_command_line_argument(adb_filepath)
    real_command = f'{adb_filepath} devices'
    retval = execute_shell_command(
        real_command,
        timeout=timeout,
    )

    assert_shell_success_status(retval)

    stdout_bs = retval['stdout']
    stdout_str = stdout_bs.decode('utf-8')
    stdout_str = stdout_str.strip()
    stdout_line_list = stdout_str.split('\n')
    stdout_line_list = [line.strip() for line in stdout_line_list]
    stdout_line_list = [line for line in stdout_line_list if len(line) > 0]

    if len(stdout_line_list) == 0:
        raise VerboseException(f'malformed output: {stdout_bs}')

    device_info_list = []
    del stdout_line_list[0]
    for line in stdout_line_list:
        line_component_list = line.split()
        if len(line_component_list) == 0:
            continue

        if len(line_component_list) != 2:
            raise VerboseException(f'malformed output: {stdout_bs}')

        serial_str = line_component_list[0]
        status_str = line_component_list[1]

        device_info_list.append({
            'serial': serial_str,
            'status': status_str,
        })

    return device_info_list


class AndroidDevice:
    def __init__(self, serial: str):
        self.serial = serial
        self.adb_filepath = None
        self.command_prefix = None

    def __repr__(self):
        return f'{hex(id(self))} - {self.__dict__}'

    def auto_set_adb_filepath(self):
        running_adb_process = find_running_adb_process()
        if running_adb_process is None:
            if not AUTO_CREATE_ADB_SERVER:
                raise Exception('No ADB server found. Please start one.')
            else:
                raise Exception('Unimplemented: auto-create ADB server')

        self.adb_filepath = normalize_path_separator(running_adb_process['exe'])

    def get_command_prefix(self):
        if self.adb_filepath is None:
            self.auto_set_adb_filepath()

        return f'{normalize_path_for_command_line_argument(self.adb_filepath)} -s {self.serial}'

    @property
    def prefix(self):
        if self.command_prefix is None:
            self.command_prefix = self.get_command_prefix()

        return self.command_prefix

    def shell(
        self,
        command: str,
        cwd=None,
        timeout=30,
    ):
        real_command = f'{self.prefix} shell {command}'
        return execute_shell_command(
            real_command,
            cwd=cwd,
            timeout=timeout,
        )

    def pull(
        self,
        REMOTE: str,
        LOCAL=None,
        args=None,
        cwd=None,
        timeout=30,
    ):
        """
        pull [-a] [-z ALGORITHM] [-Z] REMOTE... LOCAL
            copy files/dirs from device
            -a: preserve file timestamp and mode
            -z: enable compression with a specified algorithm (any, none, brotli)
            -Z: disable compression
        """
        real_command = f'{self.prefix} pull'
        if args is not None:
            real_command += f' {args}'

        remote_path = normalize_unix_path_separator(REMOTE)
        remote_path = normalize_path_for_command_line_argument(remote_path)
        real_command += f' {remote_path}'

        if LOCAL is not None:
            local_path = normalize_path_separator(local_path)
            local_path = normalize_path_for_command_line_argument(local_path)
            real_command += f' {local_path}'

        return execute_shell_command(
            real_command,
            cwd=cwd,
            timeout=timeout,
        )
