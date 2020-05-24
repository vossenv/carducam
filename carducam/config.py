import logging
import logging.config
import os

import yaml


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
