import optuna
import asyncio
import websockets
import queue
import json
import re
import sys
import nest_asyncio
nest_asyncio.apply()

ws = None
msg_queue = queue.Queue()
mailbox = dict()
studies = dict()

async def start_ws_client():
    global ws
    ws = await websockets.connect('ws://localhost:5001')
    await send(cmd='new', name='study')
    asyncio.run(receive())

async def close_ws_client():
    if ws is not None:
        await ws.close()

async def send(cmd=None, name=None, data=None):
    global ws
    msg_queue.put((cmd, name, data))
    if ws is not None:
        while not msg_queue.empty():
            pair = msg_queue.get()
            msg_json = json.dumps({ 'cmd': pair[0], 'name': pair[1] , 'data': pair[2] })
            await ws.send(msg_json)

async def receive():
    global ws
    while True:
        if ws is not None:
            msg_json = await ws.recv()
            msg = json.loads(msg_json)
            if 'cmd' in msg:
                if msg['cmd'] == 'set_outputs':
                    if msg['name'] not in mailbox:
                        mailbox[msg['name']] = dict()
                    mailbox[msg['name']][msg['data']['id']] = msg['data']


async def recv(name, id):
    while name not in mailbox or id not in mailbox[name]:
        await asyncio.sleep(0.1)
    msg = mailbox[name][id]
    del mailbox[name][id]
    return msg

async def set_study(data):
    global studies
    studies[data['name']] = data # {name, params, loss}
    sampler = optuna.samplers.TPESampler(multivariate=True)
    study = optuna.create_study(
        sampler=sampler,
        study_name=data['name'],
        storage='sqlite:///optuna.db',
        load_if_exists=True
    )
    try:
        if len(study.trials) > 0:
            await send(cmd='best_trial', name=data['name'], data={
                'id': study.best_trial.number,
                'params': study.best_params,
                'value': study.best_value
            })
    except:
        pass

def objective_wrapper(name):
    def suggest_params(trial):
        global studies
        params = []
        param_config = studies[name]['params']
        for p in param_config: # {name, type, values, low, high, enabled_step, step, enabled_log}
            if p['type'] == 'c':
                params.append(trial.suggest_categorical(p['name'], [c['value'] for c in p['values']]))
            elif p['type'] == 'i':
                low = int(p['low'])
                high = int(p['high'])
                step = int(step) if p['enabled_step'] else 1
                enabled_log = p['enabled_log']
                if enabled_log and low < 1:
                    low = 1
                params.append(trial.suggest_int(p['name'], low, high, step=step, log=enabled_log))
            elif p['type'] == 'f':
                low = float(p['low'])
                high = float(p['high'])
                step = float(step) if p['enabled_step'] else None
                enabled_log = p['enabled_log']
                if enabled_log and low < sys.float_info.min:
                    low = sys.float_info.min
                params.append(trial.suggest_float(p['name'], low, high, step=step, log=enabled_log))
        return params

    async def wait_outputs(trial_id, params):
        await send(cmd='new_trial', name=name, data={
            'id': trial_id,
            'params': params
        })
        msg = await recv(name, trial_id)
        if 'cancel' in msg and msg['cancel'] == True:
            raise optuna.exceptions.TrialPruned()
        return msg['outputs']
    
    def loss_func(outputs):
        global studies
        expr = studies[name]['loss']
        expr = re.sub('\^', '**', expr) # The exponential symbol
        expr = re.sub(r'y(\d*)', r'float(outputs[\1])', expr)
        return eval(expr)
    
    def objective(trial):
        params = suggest_params(trial)
        loop = asyncio.get_event_loop()
        outputs = loop.run_until_complete(asyncio.gather(wait_outputs(trial.number, params)))[0]
        return loss_func(outputs)
    
    return objective

async def start_trial(study_name):
    sampler = optuna.samplers.TPESampler(multivariate=True)
    study = optuna.create_study(
        sampler=sampler,
        study_name=study_name,
        storage='sqlite:///optuna.db',
        load_if_exists=True
    )
    study.optimize(objective_wrapper(name=study_name), n_trials=1)
    await send(cmd='best_trial', name=study_name, data={
        'id': study.best_trial.number,
        'params': study.best_params,
        'value': study.best_value
    })