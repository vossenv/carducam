import logging
import logging.config
import os
import time

import yaml

from carducam.Arducam import ArducamBuilder
from carducam.resources import get_resource


def main():

    init_logger(get_resource('logging_config.yaml'))
    with open(get_resource('app.yaml')) as f:
        options = yaml.safe_load(f)

    a = ArducamBuilder.build_from_file(options['register_config'], options['device_id'])

    a.capture.start()

    # ct = threading.Thread(target=captureImage_thread)
    # rt = threading.Thread(target=readImage_thread)
    # ct.start()
    # rt.start()
    # time.sleep(5)

    count = 0
    while True:
        time.sleep(1)

        if count == 5:
            a.stop()
            exit()

        count += 1


def init_logger(path):
    with open(path) as f:
        logging_config = yaml.safe_load(f)
    logs_root = logging_config.get('logs_root', 'logs')
    for k, h in logging_config['handlers'].items():
        filename = h.get('filename')
        if filename:
            if not filename == os.path.abspath(filename):
                filename = os.path.join(logs_root, filename)
            h['filename'] = filename
            log_dir = os.path.dirname(filename)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
    logging.config.dictConfig(logging_config)


if __name__ == '__main__':
    main()
