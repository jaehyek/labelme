import os.path as osp
# import shutil
# import yaml

from labelme.logger import logger
import codecs, json

here = osp.dirname(osp.abspath(__file__))

def save_dict_to_file(dict_save, filejson,mode='w'):
    with codecs.open(filejson, mode, encoding='utf-8') as f:
        json.dump(dict_save, f, ensure_ascii=False, indent=4)


def read_dict_from_file(filejson):
    with codecs.open(filejson, 'r', encoding='utf-8') as f:
        obj = json.load(f)
        return obj

def update_dict(target_dict, new_dict, validate_item=None):
    for key, value in new_dict.items():
        if validate_item:
            validate_item(key, value)
        if key not in target_dict:
            logger.warn("Skipping unexpected key in config: {}".format(key))
            continue
        if isinstance(target_dict[key], dict) and isinstance(value, dict):
            update_dict(target_dict[key], value, validate_item=validate_item)
        else:
            target_dict[key] = value


# -----------------------------------------------------------------------------


def get_default_config():
    # config_file = osp.join(here, "default_config.yaml")
    # with open(config_file) as f:
    #     config = yaml.safe_load(f)
    #
    # # save default config to ~/.labelmerc
    # save_dict_to_file(config, "default_config.json")
    # user_config_file = osp.join(osp.expanduser("~"), ".labelmerc")
    # if not osp.exists(user_config_file):
    #     try:
    #         shutil.copy(config_file, user_config_file)
    #     except Exception:
    #         logger.warn("Failed to save config: {}".format(user_config_file))

    config_file = osp.join(".", "default_config.json")
    config = read_dict_from_file(config_file)

    return config


def validate_config_item(key, value):
    if key == "validate_label" and value not in [None, "exact"]:
        raise ValueError( "Unexpected value for config key 'validate_label': {}".format( value ) )
    if key == "shape_color" and value not in [None, "auto", "manual"]:
        raise ValueError( "Unexpected value for config key 'shape_color': {}".format(value) )
    if key == "labels" and value is not None and len(value) != len(set(value)):
        raise ValueError( "Duplicates are detected for config key 'labels': {}".format(value) )


def get_config(config_file_or_json=None, dict_config_from_args=None):
    # 1. default dict_config
    dict_config = get_default_config()

    # 2. specified as file or yaml
    if config_file_or_json is not None:
        # config_from_yaml = yaml.safe_load(config_file_or_yaml)
        # if not isinstance(config_from_yaml, dict):
        #     with open(config_from_yaml) as f:
        #         logger.info( "Loading dict_config file from: {}".format(config_from_yaml) )
        #         config_from_yaml = yaml.safe_load(f)
        config_from_json = read_dict_from_file(config_file_or_json)
        update_dict( dict_config, config_from_json, validate_item=validate_config_item )

    # 3. command line argument or specified dict_config file
    if dict_config_from_args is not None:
        update_dict(dict_config, dict_config_from_args, validate_item=validate_config_item)

    return dict_config
