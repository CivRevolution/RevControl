import requests
import os
import subprocess
import threading
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import time

# Settings
JAVA_PATH = "java"
MEMORY = "1024M"
OTHER_OPTIONS = []
LOG_FILE = "minecraft_server.log"
SERVER_VERSION = "1.20.1"
PAPER_JAR_URL = "https://gist.githubusercontent.com/osipxd/6119732e30059241c2192c4a8d2218d9/raw/8999ab98f5779901780c3ef7a3f8b7b86a7e4281/paper-versions.json"

app = Flask(__name__)
socketio = SocketIO(app)
process = None

@socketio.on('connect')
def test_connect():
    emit('console_output', {'data': 'Connected to the server!'})

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

def tail_log_file(filename):
    """
    Generator function that yields new lines from a file continuously.
    """
    with open(filename, 'r') as f:
        f.seek(0, 2)  # Go to the end of the file
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)  # Sleep briefly before trying again
                continue
            yield line

def run_minecraft_server():
    global process
    print("Starting Minecraft server...")
    cmd = [JAVA_PATH, f"-Xmx{MEMORY}", f"-Xms{MEMORY}", "-jar", "paper.jar", "nogui"] + OTHER_OPTIONS
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)

    # Wait a bit to ensure the server has started and is writing to the log file
    time.sleep(5)

    # Tail the latest.log file and emit new lines to the web console
    for line in tail_log_file('./logs/latest.log'):
        print("Sending to client:", line.strip())  # Debug print
        socketio.emit('console_output', {'data': line.strip()})

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
