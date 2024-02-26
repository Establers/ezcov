import os
from tkinter import filedialog, messagebox

import yaml

def format_config (config, indent=0) :
    """
    yaml 파일을 예쁘게 출력하기 위한 함수
    """
    lines = []
    for key, value in config.items() :
        prefix = " " * indent
        if isinstance(value, dict) : 
            lines.append(f"{prefix}{key}")
            lines.append(format_config(value, indent + 1))

        else : 
            lines.append(f"{prefix}{key} : {value}")
    
    return "\n".join(lines)

def open_config():
    py_dir = os.path.dirname(__file__)
    config_dir = os.path.join(py_dir, "ezcov_config.yaml")
    try : 
        with open(config_dir,'r') as yaml_file: 
            config = yaml.safe_load(yaml_file)
            # formatted_config = format_config(config)
            # config_button_tooltip = CTkToolTip(get_config_button, delay=0.05, message=f'{formatted_config}', justify="left",  fg_color="transparent")            
            # messagebox.showinfo("Get Config", f"설정을 정상적으로 가져왔습니다.")
    except FileNotFoundError :
        messagebox.showerror("Config File Not Found", f'{config_dir}\n설정 파일 찾기 실패. \n같은 경로에 설정 파일이 없습니다.')
        return None
    return config



