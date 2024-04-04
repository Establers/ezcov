import os
from tkinter import filedialog, messagebox

import yaml


def format_config(config, indent=0):
    """
    Formats the configuration dictionary in a pretty way for printing.

    Args:
        config (dict): The configuration dictionary to be formatted.
        indent (int, optional): The number of spaces to indent each level of the configuration. Defaults to 0.

    Returns:
        str: The formatted configuration as a string.

    """
    lines = []
    for key, value in config.items():
        prefix = " " * indent
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}")
            lines.append(format_config(value, indent + 1))
        else:
            lines.append(f"{prefix}{key} : {value}")

    return "\n".join(lines)

def open_config():
    """
    Opens and loads the configuration file.

    Returns:
        dict: The loaded configuration as a dictionary.

    Raises:
        FileNotFoundError: If the configuration file is not found.
    """
    py_dir = os.path.dirname(__file__)
    config_dir = os.path.join(py_dir, "ezcov_config.yaml")
    try : 
        with open(config_dir,'r') as yaml_file: 
            config = yaml.safe_load(yaml_file)
    except FileNotFoundError :
        messagebox.showerror("Config File Not Found", f'{config_dir}\n설정 파일 찾기 실패. \n같은 경로에 설정 파일이 없습니다.')
        return None
    return config



