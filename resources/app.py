import http.server
import os
import socketserver
import subprocess
import sys
import threading
import time
import platform
import json
import psutil
import signal
import multiprocessing
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView


MAX_HEAP_SIZE = 4096
MIN_HEAP_SIZE = 512
MAX_HEAP_THRESHOLD = 0.5
FRONTEND_PORT = 3000
BACKEND_PORT = 8080


def get_java_heap_sizes():
    total_ram_mb = psutil.virtual_memory().total // (1024 * 1024)
    
    xmx = max(512, total_ram_mb * MAX_HEAP_THRESHOLD)
    
    if xmx > MAX_HEAP_SIZE:
        xmx = MAX_HEAP_SIZE

    xms = xmx / 4
    
    if xms < MIN_HEAP_SIZE:
        xms = MIN_HEAP_SIZE
    
    return int(xms), int(xmx)

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
FRONTEND_PATH = os.path.join(BASE_DIR, "frontend")

print("JDK Path:", JDK_PATH)
print("Backend JAR Path:", BACKEND_JAR)
print("Frontend Path:", FRONTEND_PATH)

# Set JAVA_HOME dynamically for subprocess
env = os.environ.copy()
env["JAVA_HOME"] = JDK_PATH
path_separator = ";" if sys.platform.lower().startswith("win") else ":"
env["PATH"] = os.path.join(JDK_PATH, "bin") + path_separator + env.get("PATH", "")

# Start Spring Boot Backend
def run_backend():
    xms, xmx = get_java_heap_sizes()
    xms_arg = f"-Xms{xms}m"
    xmx_arg = f"-Xmx{xmx}m"
    print("Starting backend...")
    args = ["java", "-jar", BACKEND_JAR, xms_arg, xmx_arg]
    print(f"Backend arguments: {' '.join(args)}")
    backend_process = subprocess.Popen(
        args=args,
        cwd=BASE_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1 
    )
    for line in iter(backend_process.stdout.readline, ''):
        print(f"[BACKEND] {line}", end="")

    backend_process.stdout.close()
    backend_process.wait()


def start_local_httpserver():
    os.chdir(FRONTEND_PATH)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", FRONTEND_PORT), handler) as httpd:
        print(f"Frontend server running at http://127.0.0.1:{FRONTEND_PORT}/")
        httpd.serve_forever()

def run_frontend():
    """Start the frontend HTTP server and keep the thread alive."""
    server_thread = threading.Thread(target=start_local_httpserver, daemon=True)
    server_thread.start()

    while True:  # Keep the frontend process running
        time.sleep(1)

def kill_process_on_port(port):
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == port and conn.pid:
            try:
                print(f"Killing process {conn.pid} on port {port}...")
                if os.name == 'nt':  # Windows
                    os.system(f"taskkill /F /PID {conn.pid}")
                else:  # Linux/macOS
                    os.kill(conn.pid, signal.SIGKILL)
                print(f"Process {conn.pid} on port {port} killed.")
            except Exception as e:
                print(f"Error killing process on port {port}: {e}")


# Start PyQt WebView for Frontend
class MainWindow(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("solver-aplication-standalone - @Hơi đẹp trai")
        self.load(QUrl(f"http://127.0.0.1:{FRONTEND_PORT}/index.html"))
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

    backend_process = multiprocessing.Process(target=run_backend)
    frontend_process = multiprocessing.Process(target=run_frontend)
    backend_process.start()
    time.sleep(2)  # Give backend time to start
    frontend_process.start()
    
    # empty args [] for PyQt
    app = QApplication(sys.argv)
    web = MainWindow()

    # Wait for both processes
    # backend_process.join()
    # frontend_process.join()

    exit_code = app.exec()
    backend_process.terminate()
    frontend_process.terminate()
    
    # might not be necessary, but just in case
    try:
        kill_process_on_port(FRONTEND_PORT)
        kill_process_on_port(BACKEND_PORT)
    except Exception as e:
        print(f"Error killing processes: {e}")

    sys.exit(exit_code)
