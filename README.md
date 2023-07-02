# Modular Chatbot Concept
## Dependencies

The Python version used for this project is **Python 3.10.8**

All python packages for this project can be installed via:
```powershell
pip install requirements.txt
```

## How to run

You can run the chatbot from the root directory via:
```powershell
python main.py
```

## How to reset chatbot state

You can force the chatbot to delete all of its trained models and database via:
```powershell
python wipe_memory.py
```

## How to compile json intents together

You can compile separate json intent files (separated by context) and preprocess them via:
```powershell
python context_compiler.py
``` 
remember to set the json filepaths in *config.yaml* before running the script

There are examples of uncompiled intent files such as *./data/initial.json* or *./data/popcorn.json*

## Configuration

You can configure the global variables via *config.yaml*