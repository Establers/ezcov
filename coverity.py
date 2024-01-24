import customtkinter as ctk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import threading
import queue
import time

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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
    "dir": ctk.StringVar(app)
}

radio_var = ctk.StringVar(value="clean and build")  # Default selection
command_arg = "/bcb"

def read_output(process, queue):
    for line in iter(process.stdout.readline, ''):
        queue.put(line)
    process.stdout.close()
    process.wait()

def update_output(output_widget, queue):
    while True:
        try:
            line = queue.get_nowait()
        except queue.Empty:
            break
        else:
            output_widget.insert(ctk.END, line)
            output_widget.see(ctk.END)

# 경로 찾기 함수 (재사용 가능)
def find_path(key, is_file=False):
    if is_file:
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

        command = f"cov-build --dir {dir_path} {cubesuite_path} {command_arg} {mtpj_path}"

        # 명령어 실행
        # subprocess.run(command, shell=True, check=True)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=read_output, args=(process, output_queue), daemon=True).start()
        threading.Thread(target=update_output, args=(output_text, output_queue), daemon=True).start()
        
        messagebox.showinfo("Success", command + "\nCommand executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

# 버튼과 레이블 생성 함수
def create_path_selector(parent, key, text, is_file=False):
    frame = ctk.CTkFrame(parent)
    frame.pack(side="top", fill="x", padx=10, pady=5)

    button = ctk.CTkButton(
        master=frame, 
        text=text, 
        command=lambda: find_path(key, is_file)
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

# 버튼과 레이블 생성
create_path_selector(app, "cubesuite", "Select CubeSuite file", is_file=True)
create_path_selector(app, "coverity", "Select Coverity Directory Path ../bin")
create_path_selector(app, "mtpj", "Select CS+ Project File *.mtpj", is_file=True)
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




# 명령어 실행 버튼
execute_button = ctk.CTkButton(app, text="Execute Command", command=execute_command)
execute_button.pack(side="top", padx=10, pady=10)


output_text = scrolledtext.ScrolledText(app, height=15)
output_text.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

app.mainloop()
