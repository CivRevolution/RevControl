from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

def send_message():
    while True:
        time.sleep(5)
        socketio.emit('message', {'data': 'Hello, client!'})

if __name__ == '__main__':
    thread = threading.Thread(target=send_message)
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5000)
