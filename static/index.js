const { createApp } = Vue

let ws = new WebSocket('ws://localhost:5001')
ws.onopen = () => {
	send('new', 'client')
}
ws.onmessage = e => {
	msg = JSON.parse(e.data)
	if ('name' in msg) {
		if (msg['name'] !== app.name) return
	}
	if ('cmd' in msg) {
		const cmd = msg['cmd']
		const name = msg['name']
		if (cmd === 'new_trial') {
			app.newTrial(msg['data'])
		} else if (cmd === 'best_trial') {
			app.bestTrial = msg['data']
		}
	}
}
function send(cmd, name, data) {
	ws.send(JSON.stringify({ cmd: cmd, name: name, data: data }))
}

async function loadConfig(file) {
	let text = await file.text()
	app.loadConfig(JSON.parse(text))
}

const app = createApp({
	data() {
		return {
			name: '',
			params: [],
			output_num: 0,
			loss: '',
			started: false,
			bestTrial: {},
			trials: []
		}
	},
	methods: {
		addParam() {
			const emptyParam = {
				name: '',
				type: '',
				values: [],
				low: null,
				high: null,
				enabled_step: false,
				step: null,
				enabled_log: false
			}
			this.params.push(emptyParam)
		},
		removeParam(param_id) {
			this.params.splice(param_id, 1)
		},
		addCategory(values) {
			values.push({value: ''})
		},
		removeCategory(values, value_id) {
			values.splice(value_id, 1)
		},
		removeCategories(param) {
			param.values = []
		},
		async saveConfig() {
			const filename = (this.name? this.name: 'config') + '.json'
			filename.replace(/\s/g, '_')
			const config = {
				name: this.name,
				params: this.params,
				output_num: this.output_num,
				loss: this.loss
			}
			saveTextAs(JSON.stringify(config), filename)
		},
		loadConfig(config) {
			this.name = config.name
			this.params = config.params
			this.output_num = config.output_num
			this.loss = config.loss
		},
		async start() {
			send('set_study', this.name, {
				name: this.name,
				params: this.params,
				loss: this.loss
			})
			this.started = !this.started
		},
		openDashboard() {
			window.open('http://localhost:5002', '_blank')
		},
		addTrial() {
			send('add_trial', this.name)
		},
		newTrial(trial) {
			const trialObj = {
				id: trial['id'],
				params: trial['params'],
				outputs: [],
				showOutputBtn: true
			}
			this.trials.push(trialObj)
		},
		cancelTrial(trial, trial_id) {
			send('set_outputs', this.name, {
				id: trial.id,
				cancel: true
			})
			this.trials.splice(trial_id, 1)
		},
		cancelTrials() {
			if (!confirm('Are you sure you want to cancel all the trials?')) return
			for (let trial of this.trials) {
				send('set_outputs', this.name, {
					id: trial.id,
					cancel: true
				})
			}
			this.trials = []
		},
		showOutputs(trial) {
			for (let i = 0; i < this.output_num; i++) trial.outputs.push({ value: '' })
			trial.showOutputBtn = false
		},
		sendOutputs(trial, trial_id) {
			send('set_outputs', this.name, {
				id: trial.id,
				outputs: trial.outputs.map(v => v.value)
			})
			this.trials.splice(trial_id, 1)
		}
	}
}).mount('#app')