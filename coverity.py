import customtkinter as ctk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import threading
import queue
import time

import os
import glob

import yaml

"""

Todo
1. 웹서버 오픈하는거 열기
2. cov-... 버튼 성공 유무 판단해서 다음꺼 실행할 수 있게
    2.1. cov-... 명령어 만족못할 경우 실패 메시지 및 처리
3. GUI 좀 더 버튼처럼 고치기... 맞추기

"""

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("C:\\Users\\SAC\\Desktop\\ezcov_theme.json")

app = ctk.CTk()
app.title("EZ Coverity")
app.geometry("800x760")

output_queue = queue.Queue()

# 경로를 저장할 StringVar 객체 생성
file_path_vars = {
    "cubesuite": ctk.StringVar(app),
    "coverity": ctk.StringVar(app),
    "mtpj": ctk.StringVar(app),
    "cov_build": ctk.StringVar(app)
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
def find_path(key, is_file=False, is_mtpj=False):
    if is_file:
        if is_mtpj :
            file_types = [('MTPJ files', '*.mtpj')]
            path = filedialog.askopenfilename(filetypes=file_types)
        else :  
            path = filedialog.askopenfilename()
    else:
        path = filedialog.askdirectory()
    if path:
        file_path_vars[key].set(path)

def execute_command():
    try:
        cubesuite_path = file_path_vars["cubesuite"].get()
        mtpj_path = file_path_vars["mtpj"].get()
        dir_path = file_path_vars["cov_build"].get()

        command = f"cov-build --dir \"{dir_path}\" \"{cubesuite_path}\" {command_arg} \"{mtpj_path}\""

        # 명령어 실행
        # subprocess.run(command, shell=True, check=True)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        messagebox.showinfo("Success", command + "\nCommand executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def execute_configure_command():
    try:
        command = f"cov-configure --comptype renesascc:rx --compiler ccrx --template"

        # 명령어 실행
        # subprocess.run(command, shell=True, check=True)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        messagebox.showinfo("Success", command + "\nCommand executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def execute_analyze_command():
    try:
        dir_path = file_path_vars["cov_build"].get()

        command = f"cov-analyze --dir \"{dir_path}\""

        # 명령어 실행
        # subprocess.run(command, shell=True, check=True)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        messagebox.showinfo("Success", command + "\nCommand executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def excute_commit_defects_command() :
    try :
        dir_path = file_path_vars["cov_build"].get()
        id = analyze_vars["id"].get()
        stream = analyze_vars["stream"].get()
        password = analyze_vars["password"].get()
        url = analyze_vars["url"].get()

        command = f"cov-commit-defects --dir \"{dir_path}\" --stream {stream} --url {url} --user {id} --password {password}"

        # 명령어 실행
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        messagebox.showinfo("Success", command + "\nCommand executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

# 버튼과 레이블 생성 함수
def create_path_selector(parent, key, text, is_file=False, is_mtpj=False):
    frame = ctk.CTkFrame(parent)
    frame.pack(side="top", fill="x", padx=10, pady=5)

    button = ctk.CTkButton(
        master=frame, 
        text=text, 
        command=lambda: find_path(key, is_file, is_mtpj)
    )
    button.pack(side="left", padx=10)

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

def auto_set_csplus_path():
    # csplus_path = "C:\\Program Files (x86)\\Renesas Electronics\\CS+\\CC\\CubeSuite+.exe"
    csplus_path = "C:\\Program Files (x86)\\Renesas Electronics\\CS+\\CC\\CubeSuite+.exe"
    # cs+ 실제로 있는지 확인
    if os.path.exists(csplus_path):
        # 경로 변수에 Windows 경로 설정
        file_path_vars["cubesuite"].set(csplus_path)  # cubesuite 로 설정
        messagebox.showinfo("Path Found", f"CubeSuite+ path set to {csplus_path}")
    else:
        messagebox.showerror("Path Not Found", "Could not find the C:\\Program Files (x86)\\Renesas Electronics\\CS+\\CC\\CubeSuite+.exe \n찾기에 실패하였습니다. \n직접 폴더 경로를 지정해주세요.")

def open_config():
    py_dir = os.path.dirname(__file__)
    config_dir = os.path.join(py_dir, "ezcov_config.yaml")
    try : 
        with open(config_dir,'r') as yaml_file: 
            config = yaml.safe_load(yaml_file)
            messagebox.showinfo("Get Config", f"설정을 정상적으로 가져왔습니다.")
    except FileNotFoundError :
        messagebox.showerror("Config File Not Found", "설정 파일 찾기 실패. \n같은 경로에 설정 파일이 없습니다.")
        return None
    return config

def write_config() :
    py_dir = os.path.dirname(__file__)
    config_dir = os.path.join(py_dir, "ezcov_config.yaml")
    try : 
        with open(config_dir,'w') as yaml_file: 
            config = yaml.safe_load(yaml_file)
            messagebox.showinfo("Get Config", f"설정을 정상적으로 가져왔습니다.")
    except FileNotFoundError :
        messagebox.showerror("Config File Not Found", "설정 파일 찾기 실패. \n같은 경로에 설정 파일이 없습니다.")
        return None
    return config

def get_config_analyze():
    config = open_config()

    analyze_vars["id"].set(config['analyze']['id'])
    analyze_vars["stream"].set(config['analyze']['stream'])
    analyze_vars["password"].set(config['analyze']['password'])
    analyze_vars["url"].set(config['analyze']['url'])
    # print(analyze_vars)

def open_website():
    # when Click this button, open the server website
    pass

# Frame for buttons
buttons_frame = ctk.CTkFrame(app)
buttons_frame.pack(side="top", fill="x", padx=10, pady=10)

# Create and place the automatic route finder button in the buttons frame
auto_find_button = ctk.CTkButton(buttons_frame, text="Auto Find CubeSuite+ Path", command=auto_set_csplus_path)
auto_find_button.pack(side="left", padx=10)

# Create and place the command execution button in the buttons frame
execute_configure_button = ctk.CTkButton(buttons_frame, text="Execute Configure Command", command=execute_configure_command)
execute_configure_button.pack(side="left", padx=10)

# 
get_config_button = ctk.CTkButton(buttons_frame, text="get config", command=get_config_analyze)
get_config_button.pack(side="left", padx=10)

# 버튼과 레이블 생성
create_path_selector(app, "cubesuite", "Select CubeSuite file", is_file=True)
create_path_selector(app, "coverity", "Select Coverity Directory Path ../bin")
create_path_selector(app, "mtpj", "Select CS+ Project File *.mtpj", is_file=True, is_mtpj=True)
create_path_selector(app, "cov_build", "cov-build 결과를 저장할 디렉토리 지정해주세요.")

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

# cov-build 명령어 실행 버튼
execute_button = ctk.CTkButton(app, text="Execute cov-build Command", command=execute_command)
execute_button.pack(side="top", padx=10, pady=10)

# cov-analyze 명령어 실행 버튼
execute_analyze_button = ctk.CTkButton(app, text="Execute cov-analyze Command", command=execute_analyze_command)
execute_analyze_button.pack(side="top", padx=10, pady=10)

# cov-commit-defects 명령어 실행 버튼
execute_commit_button = ctk.CTkButton(app, text="Execute cov-commit-defects Command", command=excute_commit_defects_command)
execute_commit_button.pack(side="top", padx=10, pady=10)

output_text = scrolledtext.ScrolledText(app, height=15)
output_text.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

app.mainloop()


"""

def find_folder_path(root_dir, folder_name):
    for dirpath, dirnames in os.walk(root_dir):
        # dirnames는 현재 디렉토리의 하위 디렉토리 목록입니다.
        if folder_name in dirnames:
            return os.path.join(dirpath, folder_name)
    return None  # 폴더를 찾지 못한 경우 None 반환

# 사용 예:
folder_path = find_folder_path("C:/", "특정폴더이름")
if folder_path:
    print(f"Found folder at: {folder_path}")
else:
    print("Folder not found.")
"""
