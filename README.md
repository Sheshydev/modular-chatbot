# Modular Chatbot Concept
This is a chatbot that I have written in Python for my University project.
The chatbot is modular, which means that you can expand on its dialogue flow in the `skills.py` file. An advantage of this is that it separates the core functionalities of the chatbot (e.g., intent matching, conversation management, fallback behaviour) from behavioural add-ons (e.g., order me a pizza, book a movie ticket etc...)

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