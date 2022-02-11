import json
import logging
import os
from pathlib import Path

from utils.logger import Logger
from utils.s3_handler import S3Handler
from utils.shell_handler import ShellHandler
from utils.sqs_handler import SQSHandler

PATH_TO_JUPYTER = './jupyter'
PATH_TO_GARGANTUA = './gargantua'
PATH_PEM = './aws_ssh_key.pem'
PATH_UTILS = './utils'
PATH_TO_CREDENTIALS = str(Path.home()) + '/.aws'


def main():
    # WARNING before executing do :
    # terraform apply
    # terraform output -json > ./infrastructure.json
    Logger()

    # Create queue for Nuxt
    SQSHandler(queue_name='ResultQueue')

    # Read config from file
    config = read_config_file('./infrastructure.json')

    prepare_ec2('jupyter', config, PATH_TO_JUPYTER)
    prepare_ec2('gargantua', config, PATH_TO_GARGANTUA)


def read_config_file(path: str):
    f = open(path)
    data = json.load(f)
    f.close()
    logging.info(f"Config read from {path}")
    return data


def copy_directory(shell_handler: ShellHandler, path_from: str):
    sftp_client = shell_handler.ssh.open_sftp()
    files_to_copy = os.listdir(path_from)
    for f in files_to_copy:
        filepath = os.path.join(path_from, f)
        try:
            sftp_client.put(filepath, filepath)
        except IOError as e:
            logging.error(e)


def prepare_ec2(server_name: str, config: dict, source_files_path: str) -> ShellHandler:
    # Connect to the instance with ssh
    logging.info(f"Connecting to {server_name} instance")
    shell_handler = ShellHandler(config[server_name]['value'], pem_path=PATH_PEM)

    # Copy file from local to AWS
    shell_handler.execute('mkdir .aws')
    shell_handler.execute(f'mkdir -p {server_name}/utils')
    shell_handler.copy_directory(source_files_path, f'./{server_name}')
    shell_handler.execute(f'cd {server_name}')
    # shell_handler.execute(f'cd {server_name} && ls -la')
    shell_handler.copy_directory(PATH_UTILS, f'./{server_name}/utils')
    shell_handler.copy_directory(PATH_TO_CREDENTIALS, '.aws')

    # Install python3.8
    shell_handler.execute('sudo yum install -y amazon-linux-extras')
    shell_handler.execute('sudo amazon-linux-extras enable python3.8')
    shell_handler.execute('sudo yum install -y python38')

    # Install pip
    shell_handler.execute('curl -O https://bootstrap.pypa.io/get-pip.py')
    shell_handler.execute('python3.8 get-pip.py --user')

    # Create venv and use it
    # https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/
    # shell_handler.execute('python3 -m pip install --user virtualenv')
    # shell_handler.execute('python3 -m venv env')
    # shell_handler.execute('source env/bin/activate')

    # Create file with needed dependencies
    shell_handler.execute('pip install pipreqs')
    shell_handler.execute('pipreqs . --force')

    # Install needed dependencies
    # shell_handler.execute('pip install "pandas==1.4"')
    shell_handler.execute('pip install xgboost')
    shell_handler.execute('pip install "pymongo[srv]"')  # not in requirements.txt
    shell_handler.execute('pip install -r requirements.txt --force')

    # Stop previous instances
    shell_handler.execute('sudo pkill python')

    return shell_handler


if __name__ == "__main__":
    main()
