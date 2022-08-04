# ParamExperiment - Manual Parameter Optimization Tool

This is a tool based on Optuna, a hyperparameter optimization tool.

Sometimes experiment have to be done manually, it is convenient to have a tool that can help you to optimize parameters of the experiment.

## Installation
Make sure you have Python 3

Install Python packages:
```
pip install -r requirements.txt
```

## Ussage
Run the following command:
```
python server.py
```

Then open http://localhost:5000/ on your browser.

## Dependencies
- Python 3
- Flask
- nest-asyncio
- optuna
- optuna-dashboard
- websockets