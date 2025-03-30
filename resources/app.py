import os
import subprocess
import sys
import time
import platform
import json
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView

def check_library_installed(lib_name):
    try:
        output = subprocess.run(
            ["dpkg", "-l", lib_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return lib_name in output.stdout
    except FileNotFoundError:
        return False  # dpkg not found (probably not Debian-based)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

entries_path = os.path.join(BASE_DIR, "entries.json")

with open(entries_path, "r", encoding="utf-8") as f:
    data = json.load(f)

JDK_PATH = os.path.join(BASE_DIR, data["jdk"])
BACKEND_JAR = os.path.join(BASE_DIR, data["backend"])
FRONTEND_PATH = os.path.join(BASE_DIR, data["frontend"])

print("JDK Path:", JDK_PATH)
print("Backend JAR Path:", BACKEND_JAR)
print("Frontend Path:", FRONTEND_PATH)

# Set JAVA_HOME dynamically for subprocess
env = os.environ.copy()
env["JAVA_HOME"] = JDK_PATH
path_separator = ";" if sys.platform.lower().startswith("win") else ":"
env["PATH"] = os.path.join(JDK_PATH, "bin") + path_separator + env.get("PATH", "")

# Start Spring Boot Backend
def start_backend():
    print("Starting backend...")
    backend_process = subprocess.Popen(
        ["java", "-jar", BACKEND_JAR],
        cwd=BASE_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return backend_process

# Start PyQt WebView for Frontend
class WebApp(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.load(QUrl.fromLocalFile(FRONTEND_PATH))
        self.showMaximized()

# Launch App
if __name__ == "__main__":
    if platform.system() == "linux":
        libs = ["libxcb-xinerama0", "libxcb-cursor0"]
        missing_libs = [lib for lib in libs if not check_library_installed(lib)]
        if missing_libs:
            print("Missing libraries:", missing_libs)
        else:
            print("All required libraries are installed!")
    backend_proc = start_backend()
    time.sleep(3)  # Wait for backend to start

    app = QApplication(sys.argv)
    web = WebApp()
    web.show()
    
    exit_code = app.exec()
    backend_proc.terminate()
    sys.exit(exit_code)
