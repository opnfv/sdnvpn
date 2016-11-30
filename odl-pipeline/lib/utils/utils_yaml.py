import yaml

def write_dict_to_yaml(config, path):
    with open(path, 'w+') as f:
        yaml.dump(config, f, default_flow_style=False)

def read_dict_from_yaml(path):
    with open(path, 'r') as f:
        return yaml.load(f)