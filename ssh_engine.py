import select

import paramiko
import threading
import time
import os

from utils import deprecated
from error_codes import *


class FolderSFTPClient(paramiko.SFTPClient):
    def put_dir(self, source, target):
        if os.path.isdir(source):
            self.mkdir('%s' % target, ignore_existing=True)
        for item in os.listdir(source):
            if os.path.isfile(os.path.join(source, item)):
                self.put(os.path.join(source, item), '%s/%s' % (target, item))
            else:
                self.mkdir('%s/%s' % (target, item), ignore_existing=True)
                self.put_dir(os.path.join(source, item), '%s/%s' % (target, item))

    def mkdir(self, path, mode=511, ignore_existing=False):
        try:
            super(FolderSFTPClient, self).mkdir(path, mode)
        except IOError:
            if ignore_existing:
                pass
            else:
                raise


class SSHEngine(object):
    def __init__(self, hosts, username, password, auto_close=True):
        super().__init__()
        with open(hosts) as f:
            self.hosts = list(map(lambda x: x.strip(), f.readlines()))
        self.username = username
        self.password = password
        self.auto_close = auto_close
        self._ssh = {}

    def _get_ssh(self, host_url):
        if host_url in self._ssh and not self.auto_close:
            return self._ssh[host_url]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        host, port = tuple(host_url.split(':'))
        ssh.connect(host, port=port, username=self.username, password=self.password)
        if not self.auto_close:
            self._ssh[host_url] = ssh
        return ssh

    def _check_server_status(self, host_url, res=None):
        ssh = self._get_ssh(host_url)
        try:
            if res is not None:
                res[host_url] = True
            if self.auto_close:
                ssh.close()
        except paramiko.ssh_exception.NoValidConnectionsError:
            res[host_url] = False
        except paramiko.ssh_exception.SSHException:
            res[host_url] = False

    def _execute_commands(self, host_url, commands, handler):
        if not commands or not handler:
            return
        if not isinstance(commands, list):
            commands = [commands]
        current_i = None
        try:
            ssh = self._get_ssh(host_url)
            for i, command in enumerate(commands):
                if isinstance(command, dict):
                    command = command[host_url]
                current_i = i
                stdin, stdout, stderr = ssh.exec_command(command)
                stdin.close()

                while not stdout.channel.exit_status_ready():
                    time.sleep(0.1)
                    if stdout.channel.recv_ready():
                        # Only print data if there is data to read in the channel
                        rl, wl, xl = select.select([stdout.channel], [], [], 0.0)
                        if len(rl) > 0:
                            # Print data from stdout
                            r = stdout.channel.recv(1024)
                            handler((host_url, current_i, r, OK))

                error = stderr.read().decode('utf-8')
                if error:
                    handler((host_url, current_i, error, StdErr))

            if self.auto_close:
                ssh.close()
        except paramiko.ssh_exception.NoValidConnectionsError:
            handler((host_url, current_i, 'NoValidConnectionsError', NoValidConnectionsError))
        except paramiko.ssh_exception.SSHException:
            handler((host_url, current_i, 'SSHException', SSHException))

    def _upload_dir(self, host_url, local_path, remote_path):
        host, port = tuple(host_url.split(':'))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(host, port=port, username=self.username, password=self.password)
            sftp = FolderSFTPClient.from_transport(ssh.get_transport())
            sftp.put_dir(local_path, remote_path)
            sftp.close()
            ssh.close()
        except paramiko.ssh_exception.NoValidConnectionsError:
            pass

    def check_server_status(self):
        threads = []
        server_status = {}
        for h in self.hosts:
            t = threading.Thread(target=self._check_server_status, args=(h, server_status))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        return server_status

    def execute_commands(self, commands, handler):
        threads = []
        for h in self.hosts:
            t = threading.Thread(target=self._execute_commands, args=(h, commands, handler))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

    def close_all(self):
        if self.auto_close:
            self.auto_close = False
            for v in self._ssh.values():
                try:
                    v.close()
                except paramiko.ssh_exception.NoValidConnectionsError:
                    pass

    @deprecated
    def upload_dir(self, local_path, remote_path):
        threads = []
        for h in self.hosts:
            t = threading.Thread(target=self._upload_dir, args=(h, local_path, remote_path))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
