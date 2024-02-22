import customtkinter as ctk
from tkinter import filedialog, messagebox, scrolledtext, Tk, Canvas, Menu
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

# drag and drop
from tkinterdnd2 import DND_FILES, TkinterDnD
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

ctk.set_appearance_mode("light")

theme_json_dir = os.path.dirname(__file__)
theme_json_path = os.path.join(theme_json_dir, "ezcov_theme.json")
ctk.set_default_color_theme(theme_json_path)

# drag and drop
class Tk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


# app = ctk.CTk()
app = Tk()
app.title("EZ Coverity")
app.geometry("680x750")

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

radio_frame_hidden = 0
radio_var = ctk.StringVar(value="rebuild")  # Default selection
command_arg = "/br"

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
            if path != "" and path[-3:] != "exe" :
                messagebox.showerror("File Select Error", "CubeSuite+.exe 또는 hew2.exe를 선택해주세요.")
                return
    else:
        path = filedialog.askdirectory()
    if path:
        file_path_vars[key].set(path)

def check_process(process, callback, step):
    print("check_process", process)
    global excute_step
    
    if process.poll() is None:  # 프로세스가 진행중
        app.after(500, lambda: check_process(process, callback, step))  # 500ms 후 다시 확인
    else:

        print("프로세스 종료")
        if process.poll() == 0 :
            excute_step = step
            if callback is not None:
                callback()  # 콜백 함수 호출
                if step == 1 :
                    # build 완료 - analyze 버튼 활성화
                    able_button(execute_analyze_button)
                    pass
                elif step == 2 :
                    # analyze 완료 - commit 버튼 활성화(2개)
                    able_button(execute_commit_button)
                    able_button(execute_commit_local_button)
                    pass
                if step == 3 :
                    # commit 완료
                    init_command_button() # 버튼 다시 초기화
                    open_website()
        else :
            print("프로세스 에러")

def on_process_complete(com):
    print("call back 함수 호출됨")
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

def init_radiobutton() :
    project_file_path = file_path_vars["project_file"].get()
    
    if "mtpj" in project_file_path[-4:] :
        radio_clean_build.select()
        radio_button_csplus()
    elif "hws" in project_file_path[-4:] :
        radio_button_hew()
    
    else :
        radio_build.deselect()
        radio_clean_build.deselect()
        radio_rebuild.deselect()
    return 

def is_valid_path(path:list):
    not_valid_path_list = []
    path_info = ["개발환경", "프로젝트 파일", "결과 저장 및 분석할 폴더"]
    for p,pi in zip(path, path_info) :
        if p == "" : 
            not_valid_path_list.append(pi)        
            
    if not_valid_path_list == [] : return True
    
    error_msg = '\n'.join(not_valid_path_list)
    messagebox.showerror("경로 설정 필요",f'아래 파일 및 폴더에 대해 경로 설정이 필요합니다.\n{error_msg}')
    return False


def execute_command():
    command =""
    try:
        csplus_hew_path = file_path_vars["csplus_hew"].get()
        project_file_path = file_path_vars["project_file"].get()
        dir_path = file_path_vars["save_dir"].get()
        
        # 경로 지정 유무 확인하기
        if not is_valid_path([csplus_hew_path, project_file_path, dir_path]) :
            return
        
        if "mtpj" in project_file_path[-4:] :
            command = f"cov-build --dir \"{dir_path}\" \"{csplus_hew_path}\" {command_arg} \"{project_file_path}\""
        elif "hws" in project_file_path[-4:] :
            # HEW의 경우, 프로젝트에서 직접 빌드를 수행하고 프로젝트를 종료해야 함.
            messagebox.showinfo("INFO", "HEW의 경우, 프로젝트에서 직접 빌드를 수행하고 프로젝트를 종료해야합니다.")
            command = f"cov-build --dir \"{dir_path}\" \"{csplus_hew_path}\" \"ow {project_file_path}\""
        # 명령어 실행
        # subprocess.run(command, shell=True, check=True)
        if command == "" :
            messagebox.showerror("Error", f"CubeSuite+ 또는 Hew2가 정상적으로 설정되지 않았습니다.\nDevelopment Env를 통해 설정해주세요.")
            return
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        check_process(process, lambda:on_process_complete(command), 1)
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
        
        check_process(process, lambda:on_process_complete(command), 2)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def is_valid_to_commit():
    # 서버가 살아있는지?
    # id, pw --> check
    # 결과 저장 폴더 지정 했는지
    # stream
    
    pass


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
        
        check_process(process, lambda:on_process_complete(command), 3)
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
        
        check_process(process, lambda:on_process_complete(command), 0)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def dnd_path_set_save_dir(event):
    dnd_file_path = event.data
    if dnd_file_path == "" or not os.path.isdir(dnd_file_path): 
        messagebox.showerror("폴더를 드래그앤 드랍","파일이 아닌 폴더를 드래그앤 드랍해주세요.")
        return
        
    file_path_vars["save_dir"].set(dnd_file_path)


def dnd_path_set_project_file(event):
    dnd_file_path = event.data
    if not os.path.isfile(dnd_file_path) :
        messagebox.showerror("유효하지 않은 파일","폴더는 불가합니다.\n프로젝트 파일[*.mtpj, *.hws]만 드래그앤 드랍이 가능합니다.")
        return
    
    if "mtpj" in dnd_file_path[-4:] :
        auto_set_devtool_path("CubeSuite+")
        file_path_vars["project_file"].set(dnd_file_path)
    elif "hws" in dnd_file_path[-4:] :
        auto_set_devtool_path("HEW")
        file_path_vars["project_file"].set(dnd_file_path)
    else :
        messagebox.showerror("유효하지 않은 파일","프로젝트 파일[*.mtpj, *.hws]만 드래그앤 드랍이 가능합니다.")
        return
    

def tooltip_mapper(key) :
    if key == "csplus_hew" :
        return "CubeSuite+.exe 의 경로 혹은 Hew2.exe 경로를 지정해주세요."
    
    if key == "coverity" :
        return "[기능 없음] 추후 추가 예정."
    
    if key == "project_file" :
        return "개발환경에 맞는 프로젝트 파일을 지정해주세요.\nCubeSuite+ : [*.mtpj]\nHEW : [*.hws]"
    
    if key == "save_dir" : 
        return "cov-build, cov-analyze 수행 결과 및 작업할 폴더를 지정해주세요."

# 버튼과 레이블 생성 함수
def create_path_selector(parent, key, text, is_file=False, is_project=False):
    container_frame = ctk.CTkFrame(parent)
    container_frame.pack(side="top", fill="x", padx=20, pady=10)

    button = ctk.CTkButton(
        master=container_frame, 
        text=text, 
        command=lambda: find_path(key, is_file, is_project),
        width=180
    )
    button.grid(row=0, column=0, padx=(0,10), sticky="w")
    button_tooltip = CTkToolTip(button, delay=0.05, message=f'{tooltip_mapper(key)}', justify="left",  fg_color="transparent")
    
    entry_frame = ctk.CTkFrame(container_frame)  # This is now a child of the container_frame
    entry_frame.grid(row=0, column=1, sticky="ew", padx=(10,0))
    container_frame.columnconfigure(1, weight=1)  # Allow the label frame to expand
    
    # entry_frame drag and drop
    if key == "project_file" :
        entry_frame.drop_target_register(DND_FILES)
        entry_frame.dnd_bind('<<Drop>>', dnd_path_set_project_file)
    elif key == "save_dir" :
        entry_frame.drop_target_register(DND_FILES)
        entry_frame.dnd_bind('<<Drop>>', dnd_path_set_save_dir)
    
    entry = ctk.CTkEntry(
        entry_frame, 
        textvariable=file_path_vars[key], 
        fg_color="transparent",
    )
    entry.pack(side="left", fill='x', expand=True)

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

def radio_button_hew():
    radio_button_label.configure(text="Hew 프로젝트 → 개발환경에서 직접 빌드")
    radio_build.deselect()
    radio_clean_build.deselect()
    radio_rebuild.deselect()

def radio_button_csplus():
    radio_button_label.configure(text="CubeSuite+ 빌드 방법 선택")
    radio_build.deselect()
    radio_clean_build.deselect()
    radio_rebuild.select()

def auto_set_devtool_path(choice) :
    print("DevTool : ", choice)
    if choice == "CubeSuite+" :
        csplus_path = "C:\\Program Files (x86)\\Renesas Electronics\\CS+\\CC\\CubeSuite+.exe"
        # cs+ 실제로 있는지 확인
        if os.path.exists(csplus_path):
        # 경로 변수에 Windows 경로 설정
            file_path_vars["csplus_hew"].set(csplus_path)  # cubesuite 로 설정
            # messagebox.showinfo("Path Found", f"CubeSuite+ path set to {csplus_path}")
            radio_rebuild.select()

        else:
            messagebox.showerror("Path Not Found",\
                "C:\\Program Files (x86)\\Renesas Electronics\\CS+\\CC\\CubeSuite+.exe\
                    \n찾기에 실패하였습니다. \n직접 폴더 경로를 지정해주세요.")
        radio_button_csplus()

    elif choice == "HEW" :
        hew_path = "C:\\Program Files (x86)\\Renesas\\Hew\\hew2.exe"
        if os.path.exists(hew_path):
            # 경로 변수에 Windows 경로 설정
            file_path_vars["csplus_hew"].set(hew_path)  # hew 로 설정
            
        else:
            messagebox.showerror("Path Not Found", \
                    "C:\\Program Files (x86)\\Renesas\\Hew\\hew2.exe\
                    \n찾기에 실패하였습니다. \n직접 폴더 경로를 지정해주세요.")
        radio_button_hew()
    
        
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
                                            message=f'{formatted_config}', justify="left",  fg_color="transparent") 
        for key, value in config['path'].items() :
            if key in file_path_vars :
                file_path_vars[key].set(value)

        for key, value in config['analyze'].items() :
            if key in analyze_vars :
                analyze_vars[key].set(value)
        
        output_text.insert(ctk.END, "> Config Load 완료하였습니다...\n");
        init_radiobutton()
        login_check_func()
        set_stream_combobox_list()
        
        
        
                
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

def login_check_func():
    url = analyze_vars["url"].get()
    api = f'{url}/api/v2/signInConfigurations?locale=en_us'
    response = requests.get(api, auth=HTTPBasicAuth(analyze_vars["id"].get(), analyze_vars["password"].get()))
    if response.status_code == 200 : 
        login_check_label.configure(text="●", text_color="#55ee55", fg_color="transparent")
        return True

    else :
        login_check_label.configure(text="X", text_color="#ee5555", fg_color="transparent")
        print("can not get response")
        return False


def refresh_server_status(app, url):
    status = check_server_status(url)
    # print(status, "url : " , url)
    if status :
        server_status_label.configure(text="서버 ON", text_color="#001100", fg_color=("#55ee55", "#55ee55"))
    else :
        server_status_label.configure(text="서버 OFF", text_color="#001100", fg_color=("#ee5555", "#ee5555"))
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
    stream = get_stream_list()
    output_text.insert(ctk.END, "> Refresh Stream List\n");
    if stream == [] : 
        output_text.insert(ctk.END, "Stream list 불러오기 실패하였습니다.ㅜ-ㅜ, 로그인 문제, 서버 문제 등 여러 문제가 있을 수 있어요.\n")
        return
    for st in stream : 
        st = f'[ {st:<40}\n'
        output_text.insert(ctk.END, st);
    output_text.see(ctk.END)
    stream_combo_box.configure(values=stream)

def create_radiobuttom_frame() :
    # Frame for radio buttons
    global radio_frame_hidden
    radio_frame_hidden = 0

    radio_frame = ctk.CTkFrame(app)
    radio_frame.pack(pady=10)

    # Radio buttons
    radio_build = ctk.CTkRadioButton(radio_frame, text="Build", variable=radio_var, value="build", command=on_radio_select)
    radio_build.grid(row=0, column=0, padx=10)

    radio_clean_build = ctk.CTkRadioButton(radio_frame, text="Clean and Build", variable=radio_var, value="clean and build", command=on_radio_select)
    radio_clean_build.grid(row=0, column=1, padx=10)

    radio_rebuild = ctk.CTkRadioButton(radio_frame, text="Rebuild", variable=radio_var, value="rebuild", command=on_radio_select)
    radio_rebuild.grid(row=0, column=2, padx=10)

def destroy_radiobutton_frame():
    global radio_frame_hidden
    radio_frame_hidden = 1
    radio_frame.destroy()

def about_menu_bar():
    if messagebox.askyesno("이스터에그", f'안녕하세요.\nCLI로 하기 귀찮으시죠...?\n잘쓰세요!..\n\n고칠 거 있으면 말씀해주세용.\nSAC사이클로직Projet 박재환 연구원 제작') :
        output_text.insert(ctk.END, "감사합니다...\n");

    else :
        output_text.insert(ctk.END, "앗...\n");

def help_menu_bar():
    if messagebox.askyesno("Help", f'개발환경 설정하시고...\n\ncov-configure 클릭해주시고..\n\nCoverity 설치된 폴더.. 프로젝트 파일..\n\n저장할 폴더..\n\n커밋할 스트림...\n\n설정해주세요\n\n더 보시려면 yes') :
        messagebox.showinfo("Help2", f'이렇게 설정하고 Save Config로 저장하구\n\nLoad Config로 설정을 불러올 수 있어요...ㅎㅎ\n\nWeb은 그냥 웹사이트 여는 버튼이에요..\n\n더 궁금한거 있음 팀즈주세요..~')
    else :
        output_text.insert(ctk.END, "앗...\n");


# def select_build_method(value):
#     global command_arg
#     selected_option = build_method_button_var.get()
#     if selected_option == "Build":
#         command_arg = "/bb"
#     elif selected_option == "Clean and Build":
#         command_arg = "/bcb"
#     elif selected_option == "Rebuild":  # rebuild
#         command_arg = "/br"

def disable_button(bt:ctk.CTkButton):
    bt.configure(state="disabled")

def able_button(bt:ctk.CTkButton):
    bt.configure(state="normal")

def init_command_button():
    able_button(execute_button)
    disable_button(execute_analyze_button)
    disable_button(execute_commit_button)
    disable_button(execute_commit_local_button)

menubar = Menu(app)
app.config(menu=menubar)
menu = Menu(menubar, tearoff=0)
menu.add_command(label="about", command=about_menu_bar)
menu.add_command(label="Help", command=help_menu_bar)
menubar.add_cascade(labe="About", menu=menu)

# 설정 폰트
button_font = ctk.CTkFont(family="Noto Sans KR", size=13)

# Frame for buttons
buttons_frame = ctk.CTkFrame(app)
buttons_frame.pack(side="top", fill="x", padx=20, pady=10)
buttons_frame.grid_columnconfigure(0, weight=1)

# Left Frame 
left_frame = ctk.CTkFrame(buttons_frame)
left_frame.grid(row=0, column=0, sticky="ew")

# ID
label_id = ctk.CTkLabel(left_frame, text="ID", fg_color="transparent", width=20)
label_id.grid(row=0, column=0, padx=0, sticky="w",pady=10)
input_entry_id = ctk.CTkEntry(left_frame, textvariable=analyze_vars["id"], placeholder_text="id")
input_entry_id.grid(row=0, column=1, padx=10,pady=10)

# PW
label_pw = ctk.CTkLabel(left_frame, text="PW", fg_color="transparent", width=30)
label_pw.grid(row=0, column=2, padx=(0, 5), sticky="w", pady=10)
input_entry_password = ctk.CTkEntry(left_frame, textvariable=analyze_vars["password"], placeholder_text="password")
input_entry_password.grid(row=0, column=3, padx=(0, 10), pady=10)
# input_entry_password.bind("<KeyRelease>", login_check_func) 

# Login Check button
login_check_button = ctk.CTkButton(left_frame, text="ID PW Check", command=login_check_func, width=50)
login_check_button.grid(row=0, column=4, pady=10)  
login_check_button_tooltip = CTkToolTip(login_check_button, delay=0.05, message=f'ID와 Password가 유효한지 검사합니다.', justify="left",  fg_color="transparent")

login_check_label = ctk.CTkLabel(left_frame, text="◀", text_color="#1A1E27", fg_color="transparent", width=15)
login_check_label.grid(row=0, column=5, pady=10, padx=5)  

# Coverity Open
get_open_url_button = ctk.CTkButton(left_frame, text="Web", command=open_website, width=50)
get_open_url_button.grid(row=0, column=6, padx=5, sticky="e")
get_open_url_button_tooltip = CTkToolTip(get_open_url_button, delay=0.05, message=f'Coverity 사이트를 엽니다.', justify="left",  fg_color="transparent")

# 서버 상태 확인
server_status_label = ctk.CTkLabel(left_frame, text="Checking...", fg_color=("white", "gray"), width=80)
server_status_label.grid(row=0, column=7, padx=5, sticky="e")


# Right Frame
right_frame = ctk.CTkFrame(buttons_frame)
right_frame.grid(row=1, column=0, sticky="ew", pady=10) 

for i in range(5) :
    right_frame.grid_columnconfigure(i, weight=1)

# 현 설정 값 yaml로 저장
save_config_button = ctk.CTkButton(right_frame, text="현재 설정 저장", command=save_config_yaml)
save_config_button.grid(row=0, column=0, padx=(0,5), pady=10)
save_config_button_tooltip = CTkToolTip(save_config_button, delay=0.05, message=f'지금 설정되어있는 ID,PW, 폴더 및 파일경로를 저장합니다.', justify="left",  fg_color="transparent")

# 저장한 yaml 파일 불러오기
load_config_button = ctk.CTkButton(right_frame, text="설정 불러오기", command=load_saved_config_yaml)
load_config_button.grid(row=0, column=1, padx=5, pady=10)

# Option Menu로 개발환경 구분하기
auto_find_button = ctk.CTkOptionMenu(right_frame, values=["CubeSuite+", "HEW"],
                                    command=auto_set_devtool_path,
                                    variable=optionmenu_devenv)
auto_find_button.grid(row=0, column=2, padx=5, pady=10)
auto_find_button_tooltip = CTkToolTip(auto_find_button, delay=0.05, message=f'Coverity 검사를 진행할 프로젝트의 개발환경을 선택해주세요.', justify="left",  fg_color="transparent")

# Create and place the command execution button in the buttons frame
execute_configure_button = ctk.CTkButton(right_frame, text="RX, R32C 컴파일러 세팅", command=execute_configure_command)
execute_configure_button.grid(row=0, column=3, padx=(5,0), pady=10, sticky="e")
execute_configure_button_tooltip = CTkToolTip(execute_configure_button, delay=0.05, message=f'RX 시리즈와 r32c 시리즈 컴파일러 Coverity 설정을 합니다.', justify="left",  fg_color="transparent")

### init : 기본 설정 
get_config_analyze()
### init : 서버 상태 확인
refresh_server_status(app, analyze_vars["url"].get())

# 버튼과 레이블 생성
create_path_selector(app, "csplus_hew", "개발환경", is_file=True)
# create_path_selector(app, "coverity", "Coverity dir Path /bin")
create_path_selector(app, "project_file", "프로젝트 파일", is_file=True, is_project=True)
create_path_selector(app, "save_dir", "결과 저장 및 분석할 폴더")



# stream 프레임
stream_frame = ctk.CTkFrame(app)
stream_frame.pack(side="top", fill="x", padx=10, pady=10)

# stream 가져오기 버튼
get_stream_list_button = ctk.CTkButton(stream_frame, text="Stream 선택 (새로고침)", command=set_stream_combobox_list, width=180)
get_stream_list_button.grid(row=0, column=0, padx=10, sticky="w")
stream_list_tooltip = CTkToolTip(get_stream_list_button, delay=0.05, message=f'스트림 항목을 다시 불러옵니다.', justify="left",  fg_color="transparent")

stream_label_frame = ctk.CTkFrame(stream_frame)  # This is now a child of the container_frame
stream_label_frame.grid(row=0, column=1, sticky="ew", padx=10)
stream_frame.columnconfigure(1, weight=1)

# stream 콤보박스
stream_combo_box = ctk.CTkComboBox(stream_frame, values=['please Refresh'], command=set_stream_list,
                                    variable=analyze_vars["stream"])
stream_combo_box.grid(row=0, column=1, sticky="ew", padx=10)

# stream Label
label = ctk.CTkLabel(stream_label_frame, textvariable=analyze_vars["stream"], fg_color="transparent")
label.grid(row=0, column=1, sticky="w")  

# Configure the columns inside stream_label_frame for proper layout
stream_label_frame.columnconfigure(0, weight=1)  # Allow the combobox to expand
stream_label_frame.columnconfigure(1, weight=1)  # Allow the label to have some space as well

# Frame for radio buttons
radio_frame = ctk.CTkFrame(app)
radio_frame.pack(pady=10)

# Radio buttons
radio_button_label = ctk.CTkLabel(radio_frame, text="CubeSuite+ 빌드 방법 선택", fg_color="transparent", width=80)
radio_button_label.grid(row=0, column=0, padx=10, pady=10)
radio_build = ctk.CTkRadioButton(radio_frame, text="Build", variable=radio_var, value="build", command=on_radio_select)
radio_build.grid(row=0, column=1, padx=10, pady=10)
radio_build_tooltip = CTkToolTip(radio_build, delay=0.05, message=f'[Only CubeSuite+] cov-build 명령어 수행 시, build를 합니다.', justify="left",  fg_color="transparent")

radio_clean_build = ctk.CTkRadioButton(radio_frame, text="Clean and Build", variable=radio_var, value="clean and build", command=on_radio_select)
radio_clean_build.grid(row=0, column=2, padx=10, pady=10)
radio_clean_build_tooltip = CTkToolTip(radio_clean_build, delay=0.05, message=f'[Only CubeSuite+] cov-build 명령어 수행 시, clean 후 build를 합니다.', justify="left",  fg_color="transparent")

radio_rebuild = ctk.CTkRadioButton(radio_frame, text="Rebuild", variable=radio_var, value="rebuild", command=on_radio_select)
radio_rebuild.grid(row=0, column=3, padx=10, pady=10)
radio_rebuild_tooltip = CTkToolTip(radio_rebuild, delay=0.05, message=f'[Only CubeSuite+] cov-build 명령어 수행 시, rebuild를 합니다.', justify="left",  fg_color="transparent")

# # build 방법 . segemented button
# build_method_frame = ctk.CTkFrame(app)
# build_method_frame.pack(side="top", pady=10, fill="x", padx=10)

# inner_frame = ctk.CTkFrame(build_method_frame)
# inner_frame.pack(fill="x", expand=True)

# build_method_label_text = "CubeSuite+ : "
# build_method_label = ctk.CTkLabel(inner_frame, text=build_method_label_text)
# build_method_label.pack(side="left", padx=(10)) 

# build_method_button_var = ctk.StringVar(value="Clean and Build")
# build_method_button = ctk.CTkSegmentedButton(inner_frame, values=["Build", "Clean and Build", "Rebuild"],
#                                                     variable=build_method_button_var, height=30)
# build_method_button_var.set("Clean and Build")
# build_method_button.pack(side="left", fill="x",)
# build_method_frame_tooltip = CTkToolTip(build_method_frame, delay=0.05, message=f'[Only CubeSuite+] 빌드 명령어 수행 시, 선택한 방법으로 빌드합니다.\nBuild 선택 시, Coverity에서 인식이 안될 수 있습니다.', justify="left",  fg_color="transparent")

cov_frame = ctk.CTkFrame(app)
cov_frame.pack(side="top", pady=10, fill="x", padx=10)
cov_frame.grid_columnconfigure(0, weight= 1)
cov_frame.grid_columnconfigure(1, weight= 1)
cov_frame.grid_columnconfigure(2, weight= 1)
cov_frame.grid_columnconfigure(3, weight= 1)
cov_frame.grid_columnconfigure(4, weight= 1)


# cov-build 명령어 실행 버튼
execute_button = ctk.CTkButton(cov_frame, text="프로젝트 빌드", command=execute_command)
# execute_button.pack(side="left", padx=10, pady=10)
execute_button.grid(row=0, column=0, padx=10, pady=10)
execute_button_tooltip = CTkToolTip(execute_button, delay=0.05, message=f'cov-build\n설정한 프로젝트를 빌드합니다.', justify="left",  fg_color="transparent")

# cov-analyze 명령어 실행 버튼
execute_analyze_button = ctk.CTkButton(cov_frame, text="결과 분석", command=execute_analyze_command)
# execute_analyze_button.pack(side="mid", padx=10, pady=10)
execute_analyze_button.grid(row=0, column=1, padx=10, pady=10)
execute_analyze_button_tooltip = CTkToolTip(execute_analyze_button, delay=0.05, \
    message=f'cov-analyze\n설정한 결과 저장 폴더에 있는 빌드 결과를 분석합니다.', justify="left",  fg_color="transparent")

# cov-commit-defects 명령어 실행 버튼
execute_commit_button = ctk.CTkButton(cov_frame, text="서버 전송", command=excute_commit_defects_command)
# execute_commit_button.pack(side="right", padx=10, pady=10)
execute_commit_button.grid(row=0, column=2, padx=10, pady=10)
execute_commit_button_tooltip = CTkToolTip(execute_commit_button, delay=0.05, \
    message=f'cov-commit-defects\ncov-analyze를 통해서 분석한 결과를 서버로 전송합니다.', justify="left",  fg_color="transparent")

# coverity commit --local 명령어 실행 버튼
execute_commit_local_button = ctk.CTkButton(cov_frame, text="로컬 분석", command=excute_coverity_commit_local)
execute_commit_local_button.grid(row=0, column=3, padx=10, pady=10)
execute_commit_local_button_tooltip = CTkToolTip(execute_commit_local_button, delay=0.05, \
    message=f'coverity commit --local\n서버가 닫혀있을 때 사용하며, 로컬로 분석 결과를 저장합니다.\
    \n결과를 저장할 폴더 지정이 필요합니다.', justify="left",  fg_color="transparent")

init_command_button()

output_text = ctk.CTkTextbox(app, height=15, activate_scrollbars=True)
output_text.pack(fill=ctk.BOTH, expand=True, padx=20, pady=10)

pjh_label = ctk.CTkLabel(app, text="원작자:박재환 ^~^ Copyright:박재환 (무단배포 금지)", fg_color="transparent", width=80, font=("Noto Sans KR", 12))
pjh_label.pack(side="top",pady=10)

app.resizable(width=True, height=False)
app.mainloop()
