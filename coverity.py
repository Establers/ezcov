import sys
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox, Tk, Menu, PhotoImage
import subprocess
import threading
import queue
import os
import yaml
import webbrowser
from req import *
# teddst 123
# from tooltip import create_tooltip
from CTkToolTip import *
from config import *

# drag and drop
from tkinterdnd2 import DND_FILES, TkinterDnD

# ctk setting
ctk.set_appearance_mode("dark") 
theme_json_dir = os.path.dirname(__file__)
theme_json_path = os.path.join(theme_json_dir, "ezcov_theme.json")
ctk.set_default_color_theme(theme_json_path)

# drag and drop
class Tk(ctk.CTk, TkinterDnD.DnDWrapper):
    """Drag and Drop 구현을 위한 CTK 클래스 재정의

    Args:
        ctk (_type_): CustomTkinter
        TkinterDnD (_type_): Drag and Drop 구현 클래스
    """
    def __init__(self, *args, **kwargs):
        # super().__init__(*args, **kwargs)
        ctk.CTk.__init__(self, *args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)
        self.init_ui()
        
    def init_ui(self):
        self.title("EZCov")
        self.geometry("630x720")
        self.resizable(width=False, height=False)
        
class CustomTooltip(CTkToolTip):
    """CTkTooltip을 상속받아 테두리 및 색깔을 지정한 클래스

    Args:
        CTkToolTip (_type_): 외부 툴팁 클래스
    """
    def __init__(self, *args, **kwargs):
        # Set custom border settings in the kwargs before initializing the superclass
        kwargs['border_width'] = 1
        kwargs['border_color'] = "#363B42"
        # Now, pass all the original and updated kwargs to the superclass initializer
        super().__init__(*args, **kwargs)

app = Tk()

### Globla Variable ###
execute_step = 0
output_queue = queue.Queue()
optionmenu_devenv =ctk.StringVar(app, value="CubeSuite+")
command_arg = "/br"
radio_var = ctk.StringVar(value="rebuild")  # Default selection
radio_frame_hidden = 0
excute_running = False

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

    return path

def check_process(process, callback, step):
    global execute_step, excute_running
    print("check_process", process)
    excute_running = True
    
    if process.poll() is None:  # 프로세스가 진행중
        app.after(500, lambda: check_process(process, callback, step))  # 500ms 후 다시 확인
    else:
        print("프로세스 종료")
        excute_running = False
        if process.poll() == 0 :
            execute_step = step
            
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
    messagebox.showinfo("Info", f'{com[:10]} ... 완료!\n다음 과정을 진행해주세요.')

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


def ask_execute_command() :
    if excute_running :
            if messagebox.askyesno("명령어 실행 중","명령어가 실행 중입니다.\n다시 명령어를 수행하시겠습니까?\n") :
                return True
            else :
                return False
    else :
        return True

def execute_command():    
    if not ask_execute_command() : 
        return
    
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
        
        # 버튼 비활성화
        # disable_button(execute_button)

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        check_process(process, lambda:on_process_complete(command), 1)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def execute_analyze_command():
    if not ask_execute_command() : 
        return
    try:
        dir_path = file_path_vars["save_dir"].get()
        command = f"cov-analyze --dir \"{dir_path}\""

        if not is_valid_dir_path(dir_path) : return
        # 명령어 실행
        # subprocess.run(command, shell=True, check=True)
        
        # 버튼 비활성화
        # disable_button(execute_analyze_button)

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        check_process(process, lambda:on_process_complete(command), 2)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def is_valid_stream(user_stream):
    url = analyze_vars["url"].get().rstrip("/")
    api = f'{url}/api/v2/streams/{user_stream}?locale=en_us'
    
    response = requests.get(api, auth=HTTPBasicAuth(analyze_vars["id"].get(), analyze_vars["password"].get()))

    if response.status_code == 200 : 
        return True

    else :
        messagebox.showerror("Commit Error","Commit 에러 발생\n1. Stream 확인\n2. 서버 상태(id, pw, ip)가 올바른지 확인해주세요.")
        print("can not get response")
        return False

def is_valid_dir_path(user_path):
    if user_path == "" : 
        messagebox.showerror("저장 경로 에러","결과 저장 및 분석 자료 폴더가 선택되지 않았습니다.\n폴더를 선택해주세요.")
        return False
    return True
    
    

def execute_commit_defects_command() :
    if not ask_execute_command() : 
        return
    try :
        dir_path = file_path_vars["save_dir"].get()
        id = analyze_vars["id"].get()
        stream = analyze_vars["stream"].get()
        password = analyze_vars["password"].get()
        url = analyze_vars["url"].get().rstrip("/")

        if not is_valid_dir_path(dir_path) : return
        if not is_valid_stream(stream) : return

        command = f"cov-commit-defects --dir \"{dir_path}\" --stream {stream} --url {url} --user {id} --password {password}"

        # 명령어 실행
        # 버튼 비활성화
        # disable_button(execute_commit_button)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        check_process(process, lambda:on_process_complete(command), 3)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def execute_coverity_commit_local() :
    if not ask_execute_command() : 
        return    
    """ 서버에 업로드하지 않고 로컬에 결과를 분석하고 싶을 때 사용.(서버 사용못하는 경우)
    1. 저장할 경로 선택
    2. 선택 후, 명령어 실행
    3. 취소 할 경우, 아무 명령어를 실행하지 않음
    """
    # 저장할 곳을 지정.
    save_path = ""
    try :
        messagebox.showinfo("저장 폴더 설정", f"로컬 분석 결과를 저장할 폴더를 지정해주세요.")
        save_path = filedialog.askdirectory()
        if save_path == "" : return
        dir_path = file_path_vars["save_dir"].get()
        command = f"coverity commit --dir \"{dir_path}\" --local \"{save_path}\""
        
        if not is_valid_dir_path(dir_path) : return

        # 명령어 실행
        # 버튼 비활성화
        # disable_button(execute_commit_local_button)

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        check_process(process, lambda:on_process_complete(command), 3)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def get_valid_filelist(event):
    if len(app.tk.splitlist(event.data)) >= 2 :
        print(app.tk.splitlist(event.data))
        messagebox.showerror("여러개의 폴더 및 파일 감지","하나의 파일 및 폴더만 지원가능합니다.")
        return False
    
    else :
        return app.tk.splitlist(event.data)[0]

def dnd_path_set_save_dir(event):
    dnd_file_path = get_valid_filelist(event)
    if dnd_file_path == False : return

    # if " " in event.data : 
    #     dnd_file_path = event.data[1:-1] # 공백이 있으면 { ... } 로 랩핑된다.
    # else :
    #     dnd_file_path = event.data

    print("dnd 폴더 : ", dnd_file_path)
    if dnd_file_path == "" or not os.path.isdir(dnd_file_path): 
        messagebox.showerror("폴더를 드래그앤 드랍","파일이 아닌 폴더를 드래그앤 드랍해주세요.")
        return False
        
    file_path_vars["save_dir"].set(dnd_file_path)


def set_auto_find_tools(tool):
    if tool == "CubeSuite+":
        auto_find_button.set("CubeSuite+")
    
    elif tool == "HEW" :
        auto_find_button.set("HEW")


def dnd_path_set_project_file(event):
    dnd_file_path = get_valid_filelist(event)
    if dnd_file_path == False : return

    # if " " in event.data : 
    #     dnd_file_path = event.data[1:-1] # 공백이 있으면 {...} 로 랩핑된다.
    # else :
    #     dnd_file_path = event.data
    # print("dnd file : ", dnd_file_path)

    if not os.path.isfile(dnd_file_path) :
        messagebox.showerror("유효하지 않은 파일","폴더는 불가합니다.\n프로젝트 파일[*.mtpj, *.hws]만 드래그앤 드랍이 가능합니다.")
        return
    _, file_extension = os.path.splitext(dnd_file_path)
    print(f'파일 확장자 : {file_extension}')

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
        font=button_font,
        width=150
    )
    button.grid(row=0, column=0, padx=(0,10), sticky="w")
    button_tooltip = CustomTooltip(button, delay=0.05, message=f'{tooltip_mapper(key)}', justify="left",  fg_color="transparent")
    
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
    radio_button_label.configure(text="Hew : 개발환경에서 직접 빌드")
    radio_button_disable_all()
    radio_build.deselect()
    radio_clean_build.deselect()
    radio_rebuild.deselect()

def radio_button_csplus():
    radio_button_label.configure(text="CubeSuite+ : 빌드 방법 선택")
    radio_button_able_all()
    radio_build.deselect()
    radio_clean_build.deselect()
    radio_rebuild.select()

def auto_set_devtool_path(choice) :
    print("DevTool : ", choice)

    if choice == "CubeSuite+" or choice == "HEW" : 
        print("set auto find tools")
        set_auto_find_tools(choice)
    else :
        return
    
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
            csplus_hew_directory_modal()
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
            csplus_hew_directory_modal()
        radio_button_hew()
    
def set_iconimg():
    py_dir = os.path.dirname(__file__)
    icon_dir = os.path.join(py_dir, "ezcov_icon.gif")
    icon = PhotoImage(file=icon_dir)
    app.wm_iconbitmap()
    app.iconphoto(True, icon)
        
set_iconimg()

def get_config_analyze():
    config = open_config()

    analyze_vars["id"].set(config['analyze']['id'])
    analyze_vars["stream"].set(config['analyze']['stream'])
    analyze_vars["password"].set(config['analyze']['password'])
    analyze_vars["url"].set(config['analyze']['url'])


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
        
    output_text.insert(ctk.END, f'> 설정 저장 완료 [ 경로 : {config_dir} ]\n\n');

def load_saved_config_yaml():
    config_dir = filedialog.askopenfilename(filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")])
    if not config_dir:  # If the user cancels the dialog, do nothing
        return

    with open(config_dir, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)
        formatted_config = format_config(config)
        load_button_tooltip = CustomTooltip(load_config_button, delay=0.05, 
                                            message=f'{formatted_config}', justify="left",  fg_color="transparent") 
        for key, value in config['path'].items() :
            if key in file_path_vars :
                file_path_vars[key].set(value)

        for key, value in config['analyze'].items() :
            if key in analyze_vars :
                analyze_vars[key].set(value)
        
        output_text.insert(ctk.END, "> Config Load 완료\n\n");
        init_radiobutton()
        # login_check_func()
        set_stream_combobox_list()
        

def open_website():
    # when Click this button, open the server website
    open_url = analyze_vars["url"].get().rstrip("/")
    webbrowser.open(open_url)

def refresh_server_status(app, url):
    status = check_server_status(url)
    # print(status, "url : " , url)
    if status :
        server_status_button.configure(text="서버", text_color="#001100", fg_color=("#55ee55", "#55ee55"), width=30, hover_color="#33ff33")
    else :
        server_status_button.configure(text="서버", text_color="#001100", fg_color=("#ee5555", "#ee5555"), width=30, hover_color="#ff3333")
    app.after(10000, refresh_server_status, app,  analyze_vars["url"].get().rstrip("/"))

def get_stream_list() :
    print("get_stream_list")
    url = analyze_vars["url"].get().rstrip("/")
    api = f'{url}/api/v2/streams?excludeRoles=false&locale=en_us&offset=0&rowCount=200'
    print("api ", api)
    streams = []
    response = None
    try :
        response = requests.get(api, auth=HTTPBasicAuth(analyze_vars["id"].get(), analyze_vars["password"].get()), timeout=1)
    except requests.exceptions.Timeout as e :
        print(e)
        messagebox.showerror("서버 주소 설정 에러","IP 주소를 다시 확인해주세요.\n해당 서버는 존재하지 않습니다.")
    except requests.exceptions.RequestException as e :
        messagebox.showerror("서버 주소 설정 에러","IP 주소를 다시 확인해주세요.\n해당 서버는 존재하지 않습니다.")
    except requests.exceptions.ConnectionError as e :
        messagebox.showerror("서버 주소 설정 에러","IP 주소를 다시 확인해주세요.\n해당 서버는 존재하지 않습니다.")
    except requests.exceptions.MissingSchema as e :
        messagebox.showerror("서버 주소 설정 에러","IP 주소를 다시 확인해주세요.\n해당 서버는 존재하지 않습니다.")
    print("response: ", response)
    
    if response == None : return streams
    
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
    messagebox.showinfo("Info", f'Coverity Simple GUI Tool\n\nSAC사이클로직Projet 박재환 연구원 개발')        

def help_menu_bar():
    if messagebox.askyesno("Help", f'1. 개발환경 설정\n\n2. cov-configure 클릭(최초)\n\n3. 분석할 프로젝트 파일(mtpj, hws) 설정\n\n4. 결과 저장 폴더 선택\n\n5. 커밋할 스트림 새로고침 후 선택\n\n더 보시려면 yes') :
        messagebox.showinfo("Help2", f'현재 설정 저장 : 현재 ID, PW, 경로를 저장합니다.\n설정 불러오기 : 저장한 설정을 불러옵니다.\nWeb : Coverity 사이트를 오픈합니다.')
    
def disable_button(bt:ctk.CTkButton):
    bt.configure(state="disabled")

def able_button(bt:ctk.CTkButton):
    bt.configure(state="normal")

def init_command_button():
    able_button(execute_button)
    disable_button(execute_analyze_button)
    disable_button(execute_commit_button)
    disable_button(execute_commit_local_button)

def restart_program():
    py = sys.executable
    os.execl(py, py, *sys.argv)

def system_path_check():
    """
    coverity \\bin path가 등록되어 있는지 체크함.
    """
    if os.environ.get("Path") == None : 
            messagebox.showerror("시스템 환경 변수 에러","Path 환경 변수 없음!")
            return False

    path_list = os.environ['Path']
    path_list = path_list.split(";")
    for path in path_list : 
        print(path)
        if "cov-analysis" in path and "bin" in path[-5:] :
            # cov-analyze가 있긴 있는지 보는 것
            # bin이 제대로 되어 있다면
            return True
    
    return False

def open_system_Env_var():
    """
    coverity\bin 경로를 Path 에 추가하기
    """
    if messagebox.askyesno("Coverity 설치 폴더 시스템 환경 변수 등록", "Coverity 설치 폴더 시스템 환경 변수에 등록해야합니다.\n\n \
                            \nCoverity 파일 압축 해제한 곳에서 \n...\\cov-analysis-win64-2023.12.0\\bin 폴더를 선택해주세요.\n자세한 사항은 메뉴얼을 참고해주세요.\n\n환경 변수창을 여시겠습니까?") :
        os.system('rundll32.exe sysdm.cpl,EditEnvironmentVariables')
        messagebox.showinfo("재시작 필요","프로그램을 종료합니다.\n시스템 환경 변수 적용을 위해 프로그램을 다시 시작해주세요")
        time.sleep(3)
        sys.exit()
    else :
        return
    
        
def set_system_path() :
    if not system_path_check() : 
        open_system_Env_var()

def help_button():
    help_menu_bar()
    pass


class ServerSettingWindow():
    def __init__(self, master):
        self.top_window = ctk.CTkToplevel(app)
        self.top_window.geometry("260x200")
        self.top_window.grab_set()
        self.top_window.title("로그인 및 서버 세팅")
        self.top_window.resizable(False, False)
        self.setup_ui()

    def login_check_func(self):
        url = analyze_vars["url"].get().rstrip("/")
        # api = f'{url}/api/v2/signInConfigurations?locale=en_us'
        api = f'{url}/api/v2/users/{analyze_vars["id"].get()}?locale=en_us'
        print("api : ", api)
        try :
            response = requests.get(api, auth=HTTPBasicAuth(analyze_vars["id"].get(), analyze_vars["password"].get()), timeout=1)
        except requests.exceptions.Timeout as e :
            print(e)
            self.login_check_label.configure(text="▲", text_color="#ee5555", fg_color="transparent")
            messagebox.showerror("서버 주소 설정 에러","IP 주소를 다시 확인해주세요.\n해당 서버는 존재하지 않습니다.")

        if response.status_code == 200 : 
            self.login_check_label.configure(text="●", text_color="#55ee55", fg_color="transparent")
            return True

        elif response.status_code == 401 :
            self.login_check_label.configure(text="▲", text_color="#ee5555", fg_color="transparent")
            messagebox.showerror("ID, PW 에러","PassWord가 올바르지 않습니다.")
            return False

        elif response.status_code == 404 :
            self.login_check_label.configure(text="▲", text_color="#ee5555", fg_color="transparent")
            messagebox.showerror("ID, PW 에러","해당 ID는 존재하지 않습니다.")
            return False
        
        else :
            print(response)
            self.login_check_label.configure(text="▲", text_color="#ee5555", fg_color="transparent")
            messagebox.showerror("ID, PW 에러","ID와 PW를 다시 확인해주세요.")
            print("can not get response, id pw error")
            return False
        
    def setup_ui(self):
        print("setup_ui")
        # Left Frame 
        left_frame = ctk.CTkFrame(self.top_window)
        left_frame.grid(row=0, column=0, sticky="ew",padx=20, pady=20, ipadx=0)

        for i in range(4) :
            left_frame.grid_columnconfigure(i, weight=1)
            
        label_id = ctk.CTkLabel(left_frame, text="ID", fg_color="transparent", width=20)
        label_id.grid(row=0, column=0, padx=0,pady=5)
        input_entry_id = ctk.CTkEntry(left_frame, textvariable=analyze_vars["id"], placeholder_text="id")
        input_entry_id.grid(row=0, column=1, padx=10, pady=5)

        # PW
        label_pw = ctk.CTkLabel(left_frame, text="PW", fg_color="transparent", width=20)
        label_pw.grid(row=1, column=0, padx=0 , pady=5)
        input_entry_password = ctk.CTkEntry(left_frame, textvariable=analyze_vars["password"], placeholder_text="password", show="*")
        input_entry_password.grid(row=1, column=1, padx=10, pady=5)
        
        # server
        label_ip = ctk.CTkLabel(left_frame, text="IP", fg_color="transparent", width=20)
        label_ip.grid(row=2, column=0, padx=0 , pady=5)
        input_entry_ip = ctk.CTkEntry(left_frame, textvariable=analyze_vars["url"], placeholder_text="server")
        input_entry_ip.grid(row=2, column=1, padx=10, pady=5)
        
        # submit
        # Login Check button
        login_check_button = ctk.CTkButton(left_frame, text="Check", command=self.login_check_func, width=70, font=button_font)
        login_check_button.grid(row=3, column=0, pady=5, columnspan=3, sticky="ew",padx=5)  
        login_check_button_tooltip = CustomTooltip(login_check_button, delay=0.05, message=f'ID와 Password가 유효한지 검사합니다.', justify="left",  fg_color="transparent")

        self.login_check_label = ctk.CTkLabel(left_frame, text="◀", fg_color="transparent", width=15)
        self.login_check_label.grid(row=3, column=4, pady=5, padx=5)  
        
def open_server_setting_window():
    server_setting_window = ServerSettingWindow(app)
    
def csplus_hew_directory_modal():
    dev_window = ctk.CTkToplevel(app)
    dev_window.geometry("500x100")
    dev_window.grab_set()
    dev_window.resizable(False, False)
    dev_window.title("개발환경 경로 설정")
    label_dev = ctk.CTkLabel(dev_window, text="아래 버튼을 눌러 개발환경 경로를 설정해주세요.", fg_color="transparent", width=20)
    label_dev.pack(pady=10,padx=(10, 0))
    create_path_selector(dev_window, "csplus_hew", "개발환경", is_file=True)
    
def init_fast_guide():
    bar = "==============================================================\n"
    output_text.insert(ctk.END, bar);
    output_text.see(ctk.END)
    manual = [
        "CubeSuite+ 드랍 다운 메뉴를 통해 개발환경 세팅. ",
        "[RX, R32C 컴파일러 세팅] 버튼 클릭. 초기 한번만 필요",
        "[프로젝트 파일] 버튼 클릭 --> Coverity 분석을 할 프로젝트를 등록.",
        "[결과 저장 및 분석 폴더] 버튼 클릭 --> Coverity 빌드 결과 저장 폴더경로를 등록",
        "[Stream 선택 (새로고침)] 버튼 클릭 --> 분석 결과를 업로드할 Stream 선택.",
        " ㄴ 따로 Stream 을 만들지 않았을 경우, 서버에서 Project와 Stream을 생성해주세요.",
        " ㄴ [Project] : 모델",
        " ㄴ [Stream] : 해당 모델의 Branch, tag 개념으로 이해하시면 됩니다.",
        "CubeSuite+ 의 경우 빌드 방법 선택, HEW의 경우 IDE가 켜질 때 빌드를 따로 해주세요.",
        "[프로젝트 빌드] 버튼 클릭, 이후 버튼을 눌러주시면 Coverity 분석 종료.",
    ]
    for idx, m in enumerate(manual) : 
        message = f'{idx + 1}. {m}\n'
        output_text.insert(ctk.END, message);
    
    bar = "==============================================================\n"
    output_text.insert(ctk.END, bar);
    output_text.see(ctk.END)

def is_exist_license_dat():
    path_list = os.environ['Path']
    path_list = path_list.split(";")
    target_path = ""
    for path in path_list : 
        if "cov-analysis" in path and "bin" in path[-5:] :
            target_path = os.path.join(path, "license.dat")
            print("license_path : ", target_path)
            break
    
    if os.path.exists(target_path) :
        return True
    else :
        return False
    
def alert_add_license_dat() :
    if not is_exist_license_dat() :
        messagebox.showerror("라이센스 파일 등록 필요", "coverity 폴더 내 `license.dat` 파일이 없습니다.\n메뉴얼을 참고하여 등록해주세요.") 
        return False
    return True

def radio_button_able_all() :
    radio_build.configure(state="normal")
    radio_rebuild.configure(state="normal")
    radio_clean_build.configure(state="normal")

def radio_button_disable_all() :
    radio_build.configure(state="disabled")
    radio_rebuild.configure(state="disabled")
    radio_clean_build.configure(state="disabled")


toplevel_window = None
 
# menubar = Menu(app)
# app.config(menu=menubar)
# menu = Menu(menubar, tearoff=0)
# menu.add_command(label="Help", command=help_menu_bar)
# menu.add_command(label="About", command=about_menu_bar)
# menubar.add_cascade(labe="Menu", menu=menu)

# 설정 폰트
button_font = ctk.CTkFont(size=12, weight="bold")

# Frame for buttons
buttons_frame = ctk.CTkFrame(app)
buttons_frame.pack(side="top", fill="x", padx=20, pady=10)
buttons_frame.grid_columnconfigure(0, weight=1)
buttons_frame.grid_columnconfigure(1, weight=1)

    
# Left Frame 
left_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
left_frame.grid(row=0, column=0, sticky="ew")

for i in range(4) :
    left_frame.grid_columnconfigure(i, weight=1) 

login_server_button = ctk.CTkButton(left_frame, text="로그인 / 서버 세팅", command=open_server_setting_window)
login_server_button.grid(row=0, column=6, padx=5)

server_status_button = ctk.CTkButton(left_frame, text="...", width=40, command=open_website, font=button_font )
server_status_button.grid(row=0, column=7, padx=5)
server_status_button_tooltip = CustomTooltip(server_status_button, delay=0.05, message=f'서버 상태 확인\nCoverity 사이트를 엽니다.', justify="left",  fg_color="transparent")

# help button
help_button = ctk.CTkButton(left_frame, text="？", width=5, command=help_button, font=button_font)
help_button.grid(row=0, column=8, padx=(5,0))

# Right Frame
right_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
right_frame.grid(row=1, column=0, sticky="ew", pady=(20,0)) 

for i in range(5) :
    right_frame.grid_columnconfigure(i, weight=1)

# 현 설정 값 yaml로 저장
save_config_button = ctk.CTkButton(right_frame, text="현재 설정 저장", command=save_config_yaml, font=button_font)
save_config_button.grid(row=0, column=0, padx=(0,5), pady=5)
save_config_button_tooltip = CustomTooltip(save_config_button, delay=0.05, message=f'지금 설정되어있는 ID,PW, 폴더 및 파일경로를 저장합니다.', justify="left",  fg_color="transparent", border_width=1, border_color="#363B42")

# 저장한 yaml 파일 불러오기
load_config_button = ctk.CTkButton(right_frame, text="설정 불러오기", command=load_saved_config_yaml, font=button_font)
load_config_button.grid(row=0, column=1, padx=5, pady=5)

# Option Menu로 개발환경 구분하기
auto_find_button = ctk.CTkComboBox(right_frame, values=["CubeSuite+", "HEW"],
                                    command=auto_set_devtool_path,
                                    variable=optionmenu_devenv, font=button_font)
auto_find_button.grid(row=0, column=2, padx=5, pady=5)
auto_find_button_tooltip = CustomTooltip(auto_find_button, delay=0.05, message=f'Coverity 검사를 진행할 프로젝트의 개발환경을 선택해주세요.', justify="left",  fg_color="transparent")

# Create and place the command execution button in the buttons frame
execute_configure_button = ctk.CTkButton(right_frame, text="RX, R32C 컴파일러 세팅", command=execute_configure_command, font=button_font)
execute_configure_button.grid(row=0, column=3, padx=(5,0), pady=5)
execute_configure_button_tooltip = CustomTooltip(execute_configure_button, delay=0.05, message=f'RX 시리즈와 r32c 시리즈 컴파일러 Coverity 설정을 합니다.', justify="left",  fg_color="transparent")


# 버튼과 레이블 생성
# create_path_selector(app, "csplus_hew", "개발환경", is_file=True)
# create_path_selector(app, "coverity", "Coverity dir Path /bin")
create_path_selector(app, "project_file", "프로젝트 파일", is_file=True, is_project=True)
create_path_selector(app, "save_dir", "결과 저장 및 분석할 폴더")

# stream 프레임
stream_frame = ctk.CTkFrame(app)
stream_frame.pack(side="top", fill="x", padx=20, pady=10)

# stream 가져오기 버튼
get_stream_list_button = ctk.CTkButton(stream_frame, text="Stream 선택 (새로고침)", command=set_stream_combobox_list, width=150, font=button_font)
get_stream_list_button.grid(row=0, column=0, padx=(0, 10), sticky="w")
stream_list_tooltip = CustomTooltip(get_stream_list_button, delay=0.05, message=f'스트림 항목을 다시 불러옵니다.', justify="left",  fg_color="transparent")

stream_label_frame = ctk.CTkFrame(stream_frame)  
stream_label_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0))
stream_frame.columnconfigure(1, weight=1)

# stream 콤보박스
stream_combo_box = ctk.CTkComboBox(stream_frame, values=['please Refresh'], command=set_stream_list,
                                    variable=analyze_vars["stream"])
stream_combo_box.grid(row=0, column=1, sticky="ew", padx=(10,0))

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
radio_button_label = ctk.CTkLabel(radio_frame, text="CubeSuite+ : 빌드 방법 선택", fg_color="transparent", width=80)
radio_button_label.grid(row=0, column=0, padx=10, pady=10)
radio_build = ctk.CTkRadioButton(radio_frame, text="Build", variable=radio_var, value="build", command=on_radio_select)
# radio_build.grid(row=0, column=1, padx=10, pady=10)
radio_build_tooltip = CustomTooltip(radio_build, delay=0.05, message=f'[Only CubeSuite+] cov-build 명령어 수행 시, build를 합니다.', justify="left",  fg_color="transparent")

radio_clean_build = ctk.CTkRadioButton(radio_frame, text="Clean and Build", variable=radio_var, value="clean and build", command=on_radio_select)
radio_clean_build.grid(row=0, column=1, padx=10, pady=10)
radio_clean_build_tooltip = CustomTooltip(radio_clean_build, delay=0.05, message=f'[Only CubeSuite+] cov-build 명령어 수행 시, clean 후 build를 합니다.', justify="left",  fg_color="transparent")

radio_rebuild = ctk.CTkRadioButton(radio_frame, text="Rebuild", variable=radio_var, value="rebuild", command=on_radio_select)
radio_rebuild.grid(row=0, column=2, padx=10, pady=10)
radio_rebuild_tooltip = CustomTooltip(radio_rebuild, delay=0.05, message=f'[Only CubeSuite+] cov-build 명령어 수행 시, rebuild를 합니다.', justify="left",  fg_color="transparent")

cov_frame = ctk.CTkFrame(app)
cov_frame.pack(side="top",fill="x", padx=20)
cov_frame.grid_columnconfigure(0, weight= 1)
cov_frame.grid_columnconfigure(1, weight= 1)
cov_frame.grid_columnconfigure(2, weight= 1)
cov_frame.grid_columnconfigure(3, weight= 1)
cov_frame.grid_columnconfigure(4, weight= 1)

# cov-build 명령어 실행 버튼
execute_button = ctk.CTkButton(cov_frame, text="프로젝트 빌드", command=execute_command, font=button_font)
# execute_button.pack(side="left", padx=10, pady=10)
execute_button.grid(row=0, column=0, padx=(0,10), pady=10)
execute_button_tooltip = CustomTooltip(execute_button, delay=0.05, message=f'cov-build\n설정한 프로젝트를 빌드합니다.', justify="left",  fg_color="transparent")

# cov-analyze 명령어 실행 버튼
execute_analyze_button = ctk.CTkButton(cov_frame, text="결과 분석", command=execute_analyze_command, font=button_font)
# execute_analyze_button.pack(side="mid", padx=10, pady=10)
execute_analyze_button.grid(row=0, column=1, padx=10, pady=10)
execute_analyze_button_tooltip = CustomTooltip(execute_analyze_button, delay=0.05, \
    message=f'cov-analyze\n설정한 결과 저장 폴더에 있는 빌드 결과를 분석합니다.', justify="left",  fg_color="transparent")

# cov-commit-defects 명령어 실행 버튼
execute_commit_button = ctk.CTkButton(cov_frame, text="서버 전송", command=execute_commit_defects_command, font=button_font)
# execute_commit_button.pack(side="right", padx=10, pady=10)
execute_commit_button.grid(row=0, column=2, padx=10, pady=10)
execute_commit_button_tooltip = CustomTooltip(execute_commit_button, delay=0.05, \
    message=f'cov-commit-defects\ncov-analyze를 통해서 분석한 결과를 서버로 전송합니다.', justify="left",  fg_color="transparent")

# coverity commit --local 명령어 실행 버튼
execute_commit_local_button = ctk.CTkButton(cov_frame, text="로컬 분석", command=execute_coverity_commit_local, font=button_font)
execute_commit_local_button.grid(row=0, column=3, padx=(10,0), pady=10)
execute_commit_local_button_tooltip = CustomTooltip(execute_commit_local_button, delay=0.05, \
    message=f'coverity commit --local\n서버가 닫혀있을 때 사용하며, 로컬로 분석 결과를 저장합니다.\
    \n결과를 저장할 폴더 지정이 필요합니다.', justify="left",  fg_color="transparent")

output_text = ctk.CTkTextbox(app, activate_scrollbars=True)
output_text.pack(fill=ctk.BOTH, expand=True, padx=20, pady=(10,0))

last_frame = ctk.CTkFrame(app)
last_frame.pack(side="bottom",expand="yes",pady=0)
pjh_label = ctk.CTkLabel(last_frame, text="개발자 : SAC사이클로직Project 박재환 연구원", fg_color="transparent", width=80, font=("Noto Sans KR", 10))
pjh_label.pack(side="left")

def light_dark_mode() :
    if ctk.get_appearance_mode() == "Light" :
        ctk.set_appearance_mode("Dark")
    elif ctk.get_appearance_mode() == "Dark" :
        ctk.set_appearance_mode("Light")

light_dark_mode_btn = ctk.CTkButton(last_frame, text="Mode", command=light_dark_mode,width=40, font=button_font)
# light_dark_mode_btn.pack(side="right", anchor="e") # 원인 미상 에러 있을지모르니 에러처리


### coverity 환경 변수 설정 확인
set_system_path()
### license.dat 파일 확인
alert_add_license_dat()
### init : 기본 설정 
get_config_analyze()
### init : 서버 상태 확인
refresh_server_status(app, analyze_vars["url"].get().rstrip("/"))
### init : 스트림 불러오기
set_stream_combobox_list()
### init : cov 명령어 비활/활성화
init_command_button()
### 개발환경 초기 설정
auto_set_devtool_path("CubeSuite+")
### 간단 가이드 출력
init_fast_guide()

app.mainloop()

# END
