import customtkinter as ctk
from tkinter import filedialog, messagebox, scrolledtext, Tk, Canvas
import subprocess
import threading

import queue
import time

import os
import glob

import yaml
import webbrowser
from req import *

# from tooltip import create_tooltip
from CTkToolTip import *
from config import *

import json
"""

Todo
### -- 1. 웹서버 오픈하는거 열기
###2. cov-... 버튼 성공 유무 판단해서 다음꺼 실행할 수 있게
    2.1. cov-... 명령어 만족못할 경우 실패 메시지 및 처리
    2.2 반쪽 짜리 기능은 완성... 
3. GUI 좀 더 버튼처럼 고치기... 맞추기 크기도 맞추기.
### 4. 스크롤바 GUI 고치기 
[보류] 5. commit 끝났을 때 페이지 열까? 버튼 만들기 
6. get으로 request .-> stream 목록 만들기 (확인필요)
    -> basic auth 사용
    --> config 에서 가져오는 걸로 id pw 설정하기
7. hew, cs+ 자동인식. (완)
    cs : Cubesuite+.exe (완)
        -> mtpj 파일 그대로 (완)
    hew : hew2.exe (완)
        -> mtpj 파일이 아니라 hws 파일 (완)
        -> cov-build 명령어가 조금 다름 (완)
8. 이번에 설정한 파일들을 저장하기 
    8.1 파일명은 {YYMMDD_HHMM}_{프로젝트이름} --> 수동 파일명으로 구현
    8.1 config 파일 골라서 불러오기 (모든 것들 다 불러옴) (완)
    
9. GUI 좀 뜯어고치기
10. 
"""

ctk.set_appearance_mode("dark")

theme_json_dir = os.path.dirname(__file__)
theme_json_path = os.path.join(theme_json_dir, "ezcov_theme.json")
ctk.set_default_color_theme(theme_json_path)

app = ctk.CTk()
app.title("EZ Coverity")
app.geometry("800x760")

### Globla Variable ###
excute_step = 0
output_queue = queue.Queue()
optionmenu_devenv =ctk.StringVar(app, value="CubeSuite+")

# 경로를 저장할 StringVar 객체 생성
file_path_vars = {
    "coverity": ctk.StringVar(app),
    "project_file": ctk.StringVar(app),
    "save_dir": ctk.StringVar(app),
    "csplus_hew": ctk.StringVar(app)
}

input_vars = {
    "dir": ctk.StringVar(app),
}

analyze_vars = {
    "url": ctk.StringVar(app),
    "stream": ctk.StringVar(app),
    "id": ctk.StringVar(app),
    "password": ctk.StringVar(app)
}

radio_var = ctk.StringVar(value="clean and build")  # Default selection
command_arg = "/bcb"

### ### ### ### ### ###

def read_output(process, queue):
    for line in iter(process.stdout.readline, ''):
        queue.put(line)
    process.stdout.close()
    process.wait()

def update_output(output_widget, output_queue):
    def update():
        try:
            # 큐에서 여러 항목을 한 번에 가져옵니다.
            while True:
                line = output_queue.get_nowait()
                output_widget.insert(ctk.END, line)
                output_widget.see(ctk.END)
        except queue.Empty:
            pass  # 큐가 비었으면 무시합니다.

        # 다음 업데이트를 위해 함수를 다시 스케줄링합니다. 여기서는 500ms 후에 업데이트합니다.
        app.after(500, update)

    # 최초의 업데이트를 스케줄링합니다.
    app.after(500, update)

# 경로 찾기 함수 (재사용 가능)
def find_path(key, is_file=False, is_project=False):
    if is_file:
        if is_project :
            file_types = [('Project File', '*.mtpj *.hws')]
            path = filedialog.askopenfilename(filetypes=file_types)
        else :  
            path = filedialog.askopenfilename()
    else:
        path = filedialog.askdirectory()
    if path:
        file_path_vars[key].set(path)

def check_process(process, callback, step):
    global excute_step
    
    if process.poll() is not None:  # 프로세스가 종료된 경우
        excute_step = step
        callback()  # 콜백 함수 호출
    else:
        app.after(500, lambda: check_process(process, callback, step))  # 500ms 후 다시 확인

def on_process_complete(com):
    messagebox.showinfo("Info", f'{com} 수행 완료')

def execute_configure_command():
    try:
        commands = [
            "cov-configure --comptype renesascc:rx --compiler ccrx --template",
            "cov-configure --comptype renesascc:r32c --compiler nc100 --template"
        ]
        command = " && ".join(commands)

        # 명령어 실행
        # subprocess.run(command, shell=True, check=True)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        # messagebox.showinfo("Success", command + "\nCommand executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def execute_command():

    try:
        csplus_hew_path = file_path_vars["csplus_hew"].get()
        project_file_path = file_path_vars["project_file"].get()
        dir_path = file_path_vars["save_dir"].get()
        
        if "mtpj" in project_file_path[-4:] :
            command = f"cov-build --dir \"{dir_path}\" \"{csplus_hew_path}\" {command_arg} \"{project_file_path}\""
        elif "hws" in project_file_path[-4:] :
            # HEW의 경우, 프로젝트에서 직접 빌드를 수행하고 프로젝트를 종료해야 함.
            messagebox.showinfo("INFO", "HEW의 경우, 프로젝트에서 직접 빌드를 수행하고 프로젝트를 종료해야합니다.")
            command = f"cov-build --dir \"{dir_path}\" \"{csplus_hew_path}\" \"ow {project_file_path}\""
        # 명령어 실행
        # subprocess.run(command, shell=True, check=True)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        check_process(process, on_process_complete(command), 1)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def execute_analyze_command():

    try:
        dir_path = file_path_vars["save_dir"].get()

        command = f"cov-analyze --dir \"{dir_path}\""

        # 명령어 실행
        # subprocess.run(command, shell=True, check=True)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        check_process(process, on_process_complete(command), 2)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def excute_commit_defects_command() :

    try :
        dir_path = file_path_vars["save_dir"].get()
        id = analyze_vars["id"].get()
        stream = analyze_vars["stream"].get()
        password = analyze_vars["password"].get()
        url = analyze_vars["url"].get()

        command = f"cov-commit-defects --dir \"{dir_path}\" --stream {stream} --url {url} --user {id} --password {password}"

        # 명령어 실행
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        check_process(process, on_process_complete(command), 3)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def excute_coverity_commit_local() :
    """ 
    coverit commit --local
    ==========
    서버에 업로드하지 않고 로컬에 결과를 분석하고 싶을 때 사용.(서버 사용못하는 경우)
    1. 저장할 경로 선택
    2. 선택 후, 명령어 실행
    3. 취소 할 경우, 아무 명령어를 실행하지 않음
    """
    # 저장할 곳을 지정.
    save_path = ""
    try :
        messagebox.showinfo("저장 폴더 설정", f"분석 결과를 저장할 폴더를 지정해주세요.")
        save_path = filedialog.askdirectory()
        if save_path == "" : return
        dir_path = file_path_vars["save_dir"].get()
        command = f"coverity commit --dir \"{dir_path}\" --local \"{save_path}\""

        # 명령어 실행
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        check_process(process, on_process_complete(command), 0)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def tooltip_mapper(key) :
    if key == "csplus_hew" :
        return "Select CubeSuite+ or HEW"
    
    if key == "coverity" :
        return "Select Coverity installed Directory \"bin\" path"
    
    if key == "project_file" :
        return "CubeSuite+ : [*.mtpj]\nHEW : [*.hws]"
    
    if key == "save_dir" : 
        return "Set a specific folder to save a result."

# 버튼과 레이블 생성 함수
def create_path_selector(parent, key, text, is_file=False, is_project=False):
    frame = ctk.CTkFrame(parent)
    frame.pack(side="top", fill="x", padx=10, pady=5)

    button = ctk.CTkButton(
        master=frame, 
        text=text, 
        command=lambda: find_path(key, is_file, is_project),
        width=200
    )
    button.pack(side="left", padx=10)
    
    button_tooltip = CTkToolTip(button, delay=0.05, message=f'{tooltip_mapper(key)}', justify="left")

    label = ctk.CTkLabel(
        frame, 
        textvariable=file_path_vars[key], 
        fg_color="transparent"
    )
    label.pack(side="right", padx=10)

# 사용자 입력 처리 함수
def process_input_dir(event=None):
    input_value = input_vars["dir"].get()
    print("key-in:", input_value)

def on_radio_select():
    global command_arg
    selected_option = radio_var.get()
    if selected_option == "build":
        command_arg = "/bb"
    elif selected_option == "clean and build":
        command_arg = "/bcb"
    else:  # rebuild
        command_arg = "/br"

def auto_set_devtool_path(choice) :
    print("DevTool : ", choice)
    if choice == "CubeSuite+" :
        csplus_path = "C:\\Program Files (x86)\\Renesas Electronics\\CS+\\CC\\CubeSuite+.exe"
        # cs+ 실제로 있는지 확인
        if os.path.exists(csplus_path):
        # 경로 변수에 Windows 경로 설정
            file_path_vars["csplus_hew"].set(csplus_path)  # cubesuite 로 설정
            messagebox.showinfo("Path Found", f"CubeSuite+ path set to {csplus_path}")
        else:
            messagebox.showerror("Path Not Found",\
                "C:\\Program Files (x86)\\Renesas Electronics\\CS+\\CC\\CubeSuite+.exe\
                    \n찾기에 실패하였습니다. \n직접 폴더 경로를 지정해주세요.")
        
    elif choice == "HEW" :
        hew_path = "C:\\Program Files (x86)\\Renesas\\Hew\\hew2.exe"
        # cs+ 실제로 있는지 확인
        if os.path.exists(hew_path):
            # 경로 변수에 Windows 경로 설정
            file_path_vars["csplus_hew"].set(hew_path)  # cubesuite 로 설정
            
            messagebox.showinfo("Path Found", f"hew2 path set to {hew_path}")
        else:
            messagebox.showerror("Path Not Found", \
                    "C:\\Program Files (x86)\\Renesas\\Hew\\hew2.exe\
                    \n찾기에 실패하였습니다. \n직접 폴더 경로를 지정해주세요.")

def open_config():
    py_dir = os.path.dirname(__file__)
    config_dir = os.path.join(py_dir, "ezcov_config.yaml")
    try : 
        with open(config_dir,'r') as yaml_file: 
            config = yaml.safe_load(yaml_file)
            formatted_config = format_config(config)
            config_button_tooltip = CTkToolTip(get_config_button, delay=0.05, message=f'{formatted_config}', justify="left")            
            # messagebox.showinfo("Get Config", f"설정을 정상적으로 가져왔습니다.")
    except FileNotFoundError :
        messagebox.showerror("Config File Not Found", f'{config_dir}\n설정 파일 찾기 실패. \n같은 경로에 설정 파일이 없습니다.')
        return None
    return config

def save_config_yaml() :
    config_dir = filedialog.asksaveasfilename(defaultextension=".yaml", 
                                            filetypes=[("YAML files", "*.yaml"),("All files", "*.*")])
    if not config_dir:  # If the user cancels the dialog, do nothing
        return
    
    config = {
        'path': {
            'csplus_hew': file_path_vars["csplus_hew"].get(),
            'project_file': file_path_vars["project_file"].get(),
            'coverity': file_path_vars["coverity"].get(),
            'save_dir': file_path_vars["save_dir"].get()
        },
        'analyze': {
            'stream': analyze_vars["stream"].get(),
            'id': analyze_vars["id"].get(),
            'password': analyze_vars["password"].get(),
            'url': analyze_vars["url"].get()
        }
    }
        
    with open(config_dir,'w') as yaml_file: 
        yaml.dump(config, yaml_file, default_flow_style=False)

def load_saved_config_yaml():
    config_dir = filedialog.askopenfilename(filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")])
    if not config_dir:  # If the user cancels the dialog, do nothing
        return

    with open(config_dir, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)
        formatted_config = format_config(config)
        load_button_tooltip = CTkToolTip(load_config_button, delay=0.05, 
                                            message=f'{formatted_config}', justify="left") 
        for key, value in config['path'].items() :
            if key in file_path_vars :
                file_path_vars[key].set(value)

        for key, value in config['analyze'].items() :
            if key in file_path_vars :
                file_path_vars[key].set(value)
                

            
                
def get_config_analyze():
    config = open_config()

    analyze_vars["id"].set(config['analyze']['id'])
    analyze_vars["stream"].set(config['analyze']['stream'])
    analyze_vars["password"].set(config['analyze']['password'])
    analyze_vars["url"].set(config['analyze']['url'])
    # print(analyze_vars)

def open_website():
    # when Click this button, open the server website
    open_url = analyze_vars["url"].get()
    webbrowser.open(open_url)

def refresh_server_status(app, url):
    status = check_server_status(url)
    # print(status, "url : " , url)
    if status :
        server_status_label.configure(text="Connected", fg_color=("white", "#11ffaa"))
    else :
        server_status_label.configure(text="Disconnected", fg_color=("white", "#dd1111"))
    app.after(10000, refresh_server_status, app,  analyze_vars["url"].get())


def get_stream_list() :
    print("get_stream_list")
    url = analyze_vars["url"].get()
    api = f'{url}/api/v2/streams?excludeRoles=false&locale=en_us&offset=0&rowCount=200'
    print("api ", api)
    streams = []
    
    response = requests.get(api, auth=HTTPBasicAuth(analyze_vars["id"].get(), analyze_vars["password"].get()))
    if response.status_code == 200 : 
        data = response.json()

        for n in data["streams"] :
            str_name = n["name"]
            streams.append(str_name)   
    else :
        print("can not get response")
        
    print(streams)
    return streams

def set_stream_list(event) :
    """
    콤보박스에서 선택한 stream 설정
    """
    stream = stream_combo_box.get()
    analyze_vars["stream"].set(stream)

def set_stream_combobox_list() :
    s = get_stream_list()
    # s = ["test", "test2", "TEST3", "우치치"]
    s.append(analyze_vars["stream"].get())
    stream_combo_box.configure(values=s)


# Frame for buttons
buttons_frame = ctk.CTkFrame(app)
buttons_frame.pack(side="top", fill="x", padx=10, pady=10)

# Option Menu로 개발환경 구분하기
auto_find_button = ctk.CTkOptionMenu(buttons_frame, values=["CubeSuite+", "HEW"],
                                    command=auto_set_devtool_path,
                                    variable=optionmenu_devenv, width=100)
auto_find_button.pack(side="left", padx=10)

# Create and place the command execution button in the buttons frame
execute_configure_button = ctk.CTkButton(buttons_frame, text="cov-configure : RX, r32c", command=execute_configure_command)
execute_configure_button.pack(side="left", padx=10)

# 현 설정 값 yaml로 저장
save_config_button = ctk.CTkButton(buttons_frame, text="Save config", command=save_config_yaml, width=80)
save_config_button.pack(side="left", padx=10)

# 저장한 yaml 파일 불러오기
load_config_button = ctk.CTkButton(buttons_frame, text="Load config", command=load_saved_config_yaml, width=80)
load_config_button.pack(side="left", padx=10)

# 설정
get_config_button = ctk.CTkButton(buttons_frame, text="get config", command=get_config_analyze, width=80)
get_config_button.pack(side="left", padx=10)
### init ###
get_config_analyze()

# Coverity Open
get_open_url_button = ctk.CTkButton(buttons_frame, text="Web", command=open_website, width=50)
get_open_url_button.pack(side="left", padx=10)

# 서버 상태 확인
server_status_label = ctk.CTkLabel(buttons_frame, text="Checking...", fg_color=("white", "gray"), width=50)
server_status_label.pack(side="left", padx=10)

## 서버 상태 확인
refresh_server_status(app, analyze_vars["url"].get())

# 버튼과 레이블 생성
create_path_selector(app, "csplus_hew", "Development Env", is_file=True)
create_path_selector(app, "coverity", "Coverity dir Path /bin")
create_path_selector(app, "project_file", "Project File", is_file=True, is_project=True)
create_path_selector(app, "save_dir", "Set save folder")

# stream 프레임
stream_frame = ctk.CTkFrame(app)
stream_frame.pack(side="top", fill="x", padx=10, pady=5)

# stream 가져오기 버튼
get_stream_list_button = ctk.CTkButton(stream_frame, text="Refresh Stream list", command=set_stream_combobox_list)
get_stream_list_button.pack(side="left", padx=10)

# stream 콤보박스
stream_combo_box = ctk.CTkComboBox(stream_frame, values=['test', 'test2'], command=set_stream_list,
                                    variable=analyze_vars["stream"])
stream_combo_box.pack(side="left", padx=10)

# stream Label
label = ctk.CTkLabel(stream_frame, textvariable=analyze_vars["stream"], fg_color="transparent")
label.pack(side="right", padx=10)

# 입력 필드 프레임
input_frame = ctk.CTkFrame(app)
input_frame.pack(side="top", fill="x", padx=10, pady=5)

input_entry = ctk.CTkEntry(input_frame, textvariable=input_vars["dir"], placeholder_text="cov-build 결과 저장할 디렉토리 이름 지정")
input_entry.pack(side="left", padx=10)

input_entry.bind("<KeyRelease>", process_input_dir)

# Frame for radio buttons
radio_frame = ctk.CTkFrame(app)
radio_frame.pack(pady=20)

# Radio buttons
radio_build = ctk.CTkRadioButton(radio_frame, text="Build", variable=radio_var, value="build", command=on_radio_select)
radio_build.grid(row=0, column=0, padx=10)

radio_clean_build = ctk.CTkRadioButton(radio_frame, text="Clean and Build", variable=radio_var, value="clean and build", command=on_radio_select)
radio_clean_build.grid(row=0, column=1, padx=10)

radio_rebuild = ctk.CTkRadioButton(radio_frame, text="Rebuild", variable=radio_var, value="rebuild", command=on_radio_select)
radio_rebuild.grid(row=0, column=2, padx=10)

cov_frame = ctk.CTkFrame(app)
cov_frame.pack(side="top", pady=20, fill="x")
cov_frame.grid_columnconfigure(0, weight= 1)
cov_frame.grid_columnconfigure(1, weight= 1)
cov_frame.grid_columnconfigure(2, weight= 1)
cov_frame.grid_columnconfigure(3, weight= 1)


# cov-build 명령어 실행 버튼
execute_button = ctk.CTkButton(cov_frame, text="cov-build", command=execute_command)
# execute_button.pack(side="left", padx=10, pady=10)
execute_button.grid(row=0, column=0, padx=10, pady=10)

# cov-analyze 명령어 실행 버튼
execute_analyze_button = ctk.CTkButton(cov_frame, text="cov-analyze", command=execute_analyze_command)
# execute_analyze_button.pack(side="mid", padx=10, pady=10)
execute_analyze_button.grid(row=0, column=1, padx=10, pady=10)

# cov-commit-defects 명령어 실행 버튼
execute_commit_button = ctk.CTkButton(cov_frame, text="cov-commit-defects", command=excute_commit_defects_command)
# execute_commit_button.pack(side="right", padx=10, pady=10)
execute_commit_button.grid(row=0, column=2, padx=10, pady=10)

# coverity commit --local 명령어 실행 버튼
execute_commit_button = ctk.CTkButton(cov_frame, text="coverity commit --local", command=excute_coverity_commit_local)
execute_commit_button.grid(row=0, column=3, padx=10, pady=10)

output_text = ctk.CTkTextbox(app, height=15, activate_scrollbars=True)
output_text.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

app.mainloop()
