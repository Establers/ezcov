import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("EZ Coverity")
app.geometry("800x760")

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
        command = f"{cubesuite_path} /cbr {mtpj_path}"

        # 명령어 실행
        subprocess.run(command, shell=True, check=True)

        messagebox.showinfo("Success", "Command executed successfully!")
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
    label.pack(side="left", padx=10)

# 사용자 입력 처리 함수
def process_input_dir(event=None):
    input_value = input_vars["dir"].get()
    print("key-in:", input_value)

# 버튼과 레이블 생성
create_path_selector(app, "cubesuite", "Select CubeSuite file", is_file=True)
create_path_selector(app, "coverity", "Select Coverity Directory Path ../bin")
create_path_selector(app, "mtpj", "Select CS+ Project File *.mtpj", is_file=True)
create_path_selector(app, "cov_build", "cov-build를 저장할 디렉토리 지정해주세요.")

# 입력 필드 프레임
input_frame = ctk.CTkFrame(app)
input_frame.pack(side="top", fill="x", padx=10, pady=5)

input_entry = ctk.CTkEntry(input_frame, textvariable=input_vars["dir"], placeholder_text="cov-build 결과 저장할 디렉토리 이름 지정")
input_entry.pack(side="left", padx=10)

input_entry.bind("<KeyRelease>", process_input_dir)


# cov-build 명령어 입력
cov_build = file_path_vars["cubesuite"].get() + " /cbr" + " " + file_path_vars["mtpj"].get(); 
print(cov_build)
app.mainloop()