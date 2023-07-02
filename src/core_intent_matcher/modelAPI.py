# standard imports
import json
from typing import List
# third party imports

# local imports
from src.db_client import DB_Client
from src.core_intent_matcher.model_pool import ModelPool
from src.core_intent_matcher.model_data_man import ModelDataManager
import src.common as common

class ModelAPI:
    """an interface to the subsystem that handles all
    classifier models of the chatbot.
    """
    def __init__(self):
        self.model_pool = ModelPool()
        self.data_man = ModelDataManager()
        self.db_client = DB_Client()

    def predict(self, user_input:str, context:str)->common.Prediction:
        with self.model_pool.GetModel(context, True) as model:
            possible_intents = model.predict(user_input)
            predicted_intent = possible_intents[0][0]
            confidence = possible_intents[0][1]
            intent_row = self.db_client.get_intent_by_idx(predicted_intent)
        
        return common.Prediction(intent_row[0], intent_row[3], intent_row[5], intent_row[6], confidence, possible_intents)

    def learn_intents(self, intents:dict, context:str):
        self.data_man.add_intents(intents, context)

    def forget_intent(self, intent:str, context:str):
        self.data_man.remove_intent(intent, context)

    def add_intent_matches(self, intentID:int, matches:List[str]):
        self.data_man.add_intent_matches(intentID, matches)