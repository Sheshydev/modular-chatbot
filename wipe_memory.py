import os
from src.db_client import DB_Client

if __name__ == "__main__":
    dir_list = os.listdir("models")
    
    for filename in dir_list:
        if filename[-7:] == ".joblib":
            os.remove("models/" + filename)
    
    db_client =  DB_Client()

    tables = ["skills", "intents", "users", "global_vars"]
    for table in tables:
        db_client.drop_table(table)