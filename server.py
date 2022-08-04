import asyncio
import websockets
import json
import threading
from flask import Flask
from optuna_dashboard import run_server
from study import start_ws_client, close_ws_client, set_study, start_trial

app = Flask(__name__, static_url_path='', static_folder='static')

@app.route('/')
def index():
    with open('index.html', 'r') as fin:
        return fin.read()


ws_client = None
ws_study = None

async def ws_route(websocket):
    global ws_client, ws_study
    async for message in websocket:
        msg = json.loads(message)
        if 'cmd' in msg:
            cmd = msg['cmd']
            name = msg['name']
            if cmd == 'new':
                if msg['name'] == 'client':
                    ws_client = websocket
                    print('New websocket connection: client')
                elif msg['name'] == 'study':
                    ws_study = websocket
                    print('New websocket connection: study')
            elif cmd == 'set_study':
                await set_study(msg['data'])
            elif cmd == 'add_trial':
                thread_trial = threading.Thread(target=run_trial, args=(name,))
                thread_trial.start()
            elif cmd == 'new_trial':
                await ws_client.send(message)
            elif cmd == 'set_outputs':
                await ws_study.send(message)
            elif cmd == 'best_trial':
                await ws_client.send(message)

async def ws_server(port):
    async with websockets.serve(ws_route, "localhost", port):
        print(f'Websocket is running on ws://localhost:{port}/')
        await start_ws_client()
        await asyncio.Future()  # run forever

def run_ws_server(port):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(ws_server(port))

def run_trial(name):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(start_trial(name))

if __name__ == '__main__':
    base_port = 5000
    thread_http = threading.Thread(target=app.run, args=(None, base_port,))
    thread_ws = threading.Thread(target=run_ws_server, args=(base_port + 1,))
    thread_dashboard = threading.Thread(target=run_server, args=('sqlite:///optuna.db', 'localhost', base_port + 2,))
    thread_http.start()
    thread_ws.start()
    thread_dashboard.start()
    thread_http.join()
    thread_ws.join()
    thread_dashboard.join()
    close_ws_client()