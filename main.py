# standard imports
from datetime import datetime

# third party imports

# local imports
from src.convo_flow_man import ConvoFlowMan
import src.common as common

CONFIG = common.CONFIG["chat_interface"]

def log(text):
    with open(CONFIG['chat_log_file'], 'a') as f:
        f.write(text)

if __name__ == "__main__":
    bot = ConvoFlowMan()

    with open("intro.txt", "r") as f:
        intro_txt = f.readlines()

    for line in intro_txt:
        print(line, end="")
    print("\n")

    bot_response = bot.greet()
    print("BOT:", bot_response)
    if CONFIG['logging']:
        log(str(datetime.utcnow())[:-7] + "- BOT: " + bot_response + "\n")

    while True:
        u_input = input("YOU: ")

        if CONFIG['logging']:
            log(str(datetime.utcnow())[:-7] + "- YOU: " + u_input + "\n")

        if u_input in CONFIG["exit_words"]:
            break

        bot_response = bot.respond_to(u_input)
        print("BOT:", bot_response)
        if CONFIG['logging']:
            log(str(datetime.utcnow())[:-7] + "- BOT: " + bot_response + "\n")
