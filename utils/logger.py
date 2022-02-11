import logging
import sys

import watchtower as watchtower


class Logger:
    def __init__(self):
        try:
            self.root = logging.getLogger()
            self.root.setLevel(logging.INFO)

            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)

            handler2 = watchtower.CloudWatchLogHandler(log_group_name="big-data")

            self.root.addHandler(handler)
            self.root.addHandler(handler2)
            self.root.info('Application is starting')

        except Exception as e:
            print(e)
