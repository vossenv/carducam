import yaml

from carducam.Arducam import Arducam
from carducam.resources import get_resource


def main():
    with open(get_resource('app.yaml')) as f:
        options = yaml.safe_load(f)

    a = Arducam.from_file(options['register_config'], options['device_id'])

    # ct = threading.Thread(target=captureImage_thread)
    # rt = threading.Thread(target=readImage_thread)
    # ct.start()
    # rt.start()

    print()


if __name__ == '__main__':
    main()
