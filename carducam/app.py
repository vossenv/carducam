import yaml
from fretcam.resources import get_resource

def main():

    with open(get_resource('app.yaml')) as f:
        options = yaml.safe_load(f)


    print()

if __name__ == '__main__':
    main()
