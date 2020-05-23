from os.path import dirname, realpath, join

resource_dir = dirname(realpath(__file__))

def get_resource(name):
    return join(resource_dir, name)
