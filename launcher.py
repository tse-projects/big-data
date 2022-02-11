import json
import logging
import os
import threading
from pathlib import Path

from utils.logger import Logger
from utils.s3_handler import S3Handler
from utils.shell_handler import ShellHandler
from utils.sqs_handler import SQSHandler

PATH_TO_CSV = './33000-BORDEAUX.csv'
PATH_TO_JUPYTER = './jupyter'
PATH_TO_GARGANTUA = './gargantua'
PATH_PEM = './aws_ssh_key.pem'
PATH_UTILS = './utils'
PATH_TO_CREDENTIALS = str(Path.home()) + '/.aws'


def main():
    Logger()
    # Copy file from HDFS (you need to configure bat and you also need windows)
    # os.system('./hadoop/hadoop.bat')

    # Copy source data file to S3
    s3_handler = S3Handler()
    s3_handler.upload_file('predict_queue/', os.path.basename(PATH_TO_CSV))

    # Read config from file
    config = read_config_file('./infrastructure.json')

    jupyter_shell = prepare_ec2('jupyter', config, PATH_TO_JUPYTER)
    gargantua_shell = prepare_ec2('gargantua', config, PATH_TO_GARGANTUA)

    # Launch the 2 processes on each server
    jupyter_thread = threading.Thread(target=jupyter_shell.execute, args=('python3.8 predict.py',))
    gargantua_thread = threading.Thread(target=gargantua_shell.execute, args=('python3.8 parse_data.py',))

    jupyter_thread.start()
    gargantua_thread.start()

    sqs_handler_predict = SQSHandler(queue_name='PredictQueue')
    sqs_handler_predict.send_message(message_body="Prediction", message=PATH_TO_CSV)

    jupyter_thread.join()
    gargantua_thread.join()

    print("End!")


def read_config_file(path: str):
    f = open(path)
    data = json.load(f)
    f.close()
    logging.info(f"Config read from {path}")
    return data


def prepare_ec2(server_name: str, config: dict, source_files_path: str) -> ShellHandler:
    # Connect to the instance with ssh
    logging.info(f"Connecting to {server_name} instance")
    shell_handler = ShellHandler(config[server_name]['value'], pem_path=PATH_PEM)

    shell_handler.execute(f'cd {server_name}')

    # Stop previous instances
    shell_handler.execute('sudo pkill python')

    return shell_handler


if __name__ == "__main__":
    main()
