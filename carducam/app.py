from carducam.arducam import ArducamBuilder
from carducam.config import init_logger
from carducam.resources import get_resource


def main():
    init_logger(get_resource('logging_config.yaml'))
    a = ArducamBuilder.build_from_file(get_resource('app.yaml'))
    a.start()
    input("")
    a.stop()


if __name__ == '__main__':
    main()
