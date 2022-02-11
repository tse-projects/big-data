import logging
import os
import time

import paramiko


class ShellHandler:

    def __init__(self, host: str, pem_path: str):
        self.pem_path = pem_path
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_connect_with_retry(host, 0)

        channel = self.ssh.invoke_shell()
        self.stdin = channel.makefile('wb')
        self.stdout = channel.makefile('r')
        self.sftp_client = self.ssh.open_sftp()

    def __del__(self):
        self.ssh.close()

    def ssh_connect_with_retry(self, ip_address, retries):
        if retries > 3:
            return False
        private_key = paramiko.RSAKey.from_private_key_file(self.pem_path)
        interval = 5
        try:
            retries += 1
            logging.info('SSH into the instance: {}'.format(ip_address))
            self.ssh.connect(hostname=ip_address,
                             username='ec2-user', pkey=private_key)
            return True
        except Exception as e:
            logging.error(e)
            time.sleep(interval)
            logging.warning('Retrying SSH connection to {}'.format(ip_address))
            self.ssh_connect_with_retry(ip_address, retries)

    def execute(self, cmd: str):
        """
        :param cmd: the command to be executed on the remote computer
        :examples:  execute('ls')
                    execute('finger')
                    execute('cd folder_name')
        """
        logging.info('Executing command {}'.format(cmd))

        cmd = cmd.strip('\n')
        self.stdin.write(cmd + '\n')
        finish = 'end of stdOUT buffer. finished with exit status'
        echo_cmd = 'echo {} $?'.format(finish)
        self.stdin.write(echo_cmd + '\n')
        shin = self.stdin
        self.stdin.flush()
        shout = []
        sherr = []

        # Read output
        for line in self.stdout:
            if str(line).startswith(finish):
                # our finish command ends with the exit status
                exit_status = int(str(line).rsplit(maxsplit=1)[1])
                if exit_status:
                    # stderr is combined with stdout.
                    # thus, swap sherr with shout in a case of failure.
                    sherr = shout
                    shout = []
                break
            elif 'echo' not in line:
                shout.append(line.replace('\n', ''))

        for line in sherr:
            logging.error(line)
        for line in shout:
            logging.info(line)

        return shin, shout, sherr

    def copy_directory(self, path_from: str, path_to: str = ''):
        files_to_copy = os.listdir(path_from)
        for f in files_to_copy:
            self.copy_file(f, path_from, path_to)

    def copy_file(self, f, path_from, path_to):
        from_filepath = os.path.join(path_from, f)
        to_filepath = os.path.join(path_to, f)
        try:
            self.sftp_client.put(from_filepath, to_filepath)
        except IOError as e:
            logging.error(e)
