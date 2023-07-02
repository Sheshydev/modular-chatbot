# standard imports
from typing import List

# third party imports

# local imports
import src.common as common
from src.core_intent_matcher.model_pool import ModelPool, ModelNotFoundError
from src.db_client import DB_Client
from src.core_intent_matcher.model import Model

@common.singleton
class ModelDataManager:
    """syncs the handling of model training data and database CRUD operations.
    It uses the ModelPool and database client as part of its implementation.
    """

    def __init__(self):
        self.model_pool = ModelPool()
        self.db_client = DB_Client()
            
    def add_intents(self, intents_json:dict, context:str):
        """add intents from a json dictionary

        :param intents_json: dictionary of intents, with intents
        as keys and its attributes as values
        :type intents_json: dict
        :param context: context under which to insert the intent
        :type context: str
        """
        intent_ids = []
        matches_list = []

        for intent, intent_attr in intents_json.items():
            intent_id = self.db_client.insert_intent(intent, intent_attr["matches"], \
                intent_attr["responses"], context, intent_attr["link"], intent_attr["type"])
            intent_ids.append(intent_id)
            
            matches_list.append(intent_attr["matches"])
        
        prepared_data = list(zip(intent_ids, matches_list))

        try:
            self.model_pool[context]
        except ModelNotFoundError:
            self.add_context(context)

        with self.model_pool.GetModel(context) as model:
            model.prepare_data(prepared_data)
            model.train_and_test()

    
    def remove_intent(self, intent:str, context:str):
        """remove an intent from a context. Removes
        the intent from the model as well as the database.

        :param intent: identifying name of the intent
        :type intent: str
        :param context: context/model name under which to
        insert intent
        :type context: str
        """
        rows_left = self.db_client.drop_intent(intent, context)

        if rows_left > 0:
            intents = self.db_client.get_intents(context)
            prepared_data = [(intent[0], intent[2]) for intent in intents]

            with self.model_pool.GetModel(context) as model:
                model.prepare_data(prepared_data)
                model.train_and_test()

        elif rows_left == 0:
            self.model_pool.pop_model(context)

    def add_context(self, context:str):
        """adds a model into the model pool as the one that
        corresponds to the conversational context

        :param context: context to be added, will be the name of the
        classifier model in the model pool
        :type context: str
        """
        self.model_pool.add_model(context, Model())

    def remove_context(self, context:str):
        """removes the context from both the database and the
        corresponding classifier model from the model pool.

        :param context: identifying name of context to remove
        :type context: str
        """
        self.model_pool.pop_model(context)
        self.db_client.drop_context(context)

    def add_intent_matches(self, intentID:int, matches:List[str]):
        self.db_client.update_intent_matches(intentID, matches)
        context = self.db_client.get_intent_by_idx(intentID)[4]
        intents = self.db_client.get_intents(context)

        prepared_data = [(intent[0], intent[2]) for intent in intents]
        
        with self.model_pool.GetModel(context) as model:
            model.prepare_data(prepared_data, True)
            model.train_and_test()
