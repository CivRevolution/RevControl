import requests
import os
import subprocess
import threading
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit, join_room
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Settings
JAVA_PATH = "java"
MEMORY = "1024M"
OTHER_OPTIONS = []
LOG_FILE = "minecraft_server.log"
SERVER_VERSION = "1.20.1"
PAPER_JAR_URL = "https://gist.githubusercontent.com/osipxd/6119732e30059241c2192c4a8d2218d9/raw/8999ab98f5779901780c3ef7a3f8b7b86a7e4281/paper-versions.json"

app = Flask(__name__)
socketio = SocketIO(app, logger=True, engineio_logger=True)
process = None

@socketio.on('connect')
def test_connect():
    join_room('minecraft_logs')
    socketio.emit('console_output', {'data': 'Connected to the server!'})

def download_paper_jar():
    print("Fetching PaperMC server download URL...")
    response = requests.get(PAPER_JAR_URL)
    data = response.json()
    download_url = data["versions"][SERVER_VERSION]
    print(f"Downloading PaperMC server from {download_url}...")
    with requests.get(download_url, stream=True) as r:
        with open("paper.jar", "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print("Download completed.")

def modify_eula_file():
    print("Modifying eula.txt...")
    with open("eula.txt", "r") as f:
        content = f.readlines()
    with open("eula.txt", "w") as f:
        for line in content:
            if "eula=false" in line:
                f.write("eula=true\n")
            else:
                f.write(line)
    print("eula.txt modified successfully.")

def initial_server_start():
    global process
    print("Starting Minecraft server for the first time...")
    cmd = [JAVA_PATH, f"-Xmx{MEMORY}", f"-Xms{MEMORY}", "-jar", "paper.jar", "nogui"] + OTHER_OPTIONS
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)

    # Wait for eula.txt to be created
    while not os.path.exists("eula.txt"):
        pass

    modify_eula_file()
    process.terminate()
    process.wait()

def emit_log_data(data):
    print("Emitting data:", data)  # Debug print
    socketio.emit('console_output', {'data': data})

class LogHandler(FileSystemEventHandler):
    def __init__(self, filename, callback):
        self.filename = filename
        self.callback = callback
        self.last_position = 0

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(self.filename):
            with open('./logs/' + self.filename, 'r') as f:
                f.seek(self.last_position)
                new_data = f.read()
                self.last_position = f.tell()
                if new_data:
                    print("Detected new data:", new_data)  # Debug print
                    self.callback(new_data)

def run_minecraft_server():
    global process
    print("Starting Minecraft server...")
    cmd = [JAVA_PATH, f"-Xmx{MEMORY}", f"-Xms{MEMORY}", "-jar", "paper.jar", "nogui"] + OTHER_OPTIONS
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=2, universal_newlines=True)

    # Wait a bit to ensure the server has started and is writing to the log file
    time.sleep(5)

    # Set up watchdog to monitor the latest.log file
    path = os.path.dirname(os.path.abspath('./logs/latest.log'))
    event_handler = LogHandler('latest.log', lambda data: socketio.emit('console_output', {'data': data.strip()}, callback=ack))
    observer = Observer()
    observer.schedule(event_handler, path=path)
    observer.start()

# Check if paper.jar exists
if not os.path.exists("paper.jar"):
    download_paper_jar()
    initial_server_start()

@app.route('/api/logs', methods=['GET'])
def get_logs():
    lines = int(request.args.get('lines', 10))
    since = float(request.args.get('since', 0))

    with open(LOG_FILE, 'r') as f:
        content = f.readlines()

    # Filter logs based on the 'since' timestamp
    filtered_content = [line for line in content if time.mktime(time.strptime(line.split()[0], "%Y-%m-%d %H:%M:%S")) > since]

    return jsonify(filtered_content[-lines:])

@app.route('/')
def index():
    return render_template('console.html')

@socketio.on('send_command')
def handle_command(command):
    process.stdin.write(command + '\n')
    process.stdin.flush()

if __name__ == '__main__':
    print("Initializing server...")
    thread = threading.Thread(target=run_minecraft_server)
    thread.start()
    print(f"Starting Flask app on http://0.0.0.0:5000/")
    socketio.run(app, host='0.0.0.0', port=5000)
