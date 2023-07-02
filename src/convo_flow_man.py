# standard imports
import json
import random
from typing import List, Dict
import ast

# third party imports
from tqdm import tqdm

# local imports
from src.core_intent_matcher.modelAPI import ModelAPI
import src.common as common
from src.db_client import DB_Client
import src.skills.skills as skills
from src.skills.skill_interface import Skill
import src.nltk_downloads # to trigger nltk downloads

CONFIG = common.CONFIG["chatbot"]
DEBUG = common.CONFIG["debug"]

@common.singleton
class ConvoFlowMan:
    def __init__(self):
        self.model_api = ModelAPI()
        self.db_client = DB_Client()
        self.context = CONFIG["root_context"]
        self.confidence_treshold = CONFIG["confidence_treshold"]
        self.ambiguity_treshold = CONFIG["ambiguity_treshold"]
        self.skill_stage = -1
        self.not_root_context = None
        self.prev_possible_intents = None
        self.skill_instances = {}
        self.prev_input = None

        for obj in skills.__dict__.values():
            # inserts all skills into the database
            # Solution from Mike Muller: https://stackoverflow.com/questions/34554856/python-instantiate-all-classes-within-a-module
            if obj is not Skill and isinstance(obj, type) and issubclass(obj, Skill):
                inst = obj()
                self.db_client.insert_skill(inst.name, obj)

        response = None

        already_trained = self.db_client.get_global_var("already_trained")
        if already_trained is None:
            with open(CONFIG["root_intents_file"]) as f:
                dialogue = json.load(f)
            self.learn_intents(dialogue["data"])
            self.db_client.insert_global_var("already_trained", "True")

    def greet(self):
        self.parent_context = self.context
        self.context = CONFIG["greet_context"]
        self.skill_stage = 0

        return self.skill_response("", None)

    def respond_to(self, u_input:str)->str:
        """function for chatbot to respond to user input. This is meant to be called by a separate user
        interface module. It incorporates skills and repeatability of dialogue.

        :param u_input: user input
        :type u_input: str
        :return: chatbot response 
        :rtype: str
        """

        response = None

        if self.skill_stage == -1: # if bot uses classifier model
            self.prediction = self.model_api.predict(u_input, self.context)
            if len(self.prediction.possible_intents) > 1:
                second_similarity = self.prediction.possible_intents[1][1]

            if DEBUG:
                print(self.prediction)

            if self.prediction.confidence < self.confidence_treshold \
                or self.prediction.confidence - second_similarity < self.ambiguity_treshold:
                self.prev_input = u_input
                self.skill_stage = 0

                self.parent_context = self.not_root_context or self.context
                self.prev_possible_intents = self.prev_possible_intents or self.prediction.possible_intents

                self.context = CONFIG["clarify_context"]
                response = self.skill_response(u_input, None, choices=self.prev_possible_intents, context=self.parent_context)

                self.not_root_context = None
                self.prev_possible_intents = None

            else: # if bot is confident...
                if self.prediction.intent_type == "skill": # ... and intent is a skill
                    self.skill_stage = 0
                    self.parent_context = self.context
                    self.context = self.prediction.next_context
                    response = self.skill_response(u_input, intentID=self.prediction.intentID)
                
                else: # if intent is model-based
                    if self.prediction.next_context != "self": # no need to change context if next context is self
                        self.context = self.prediction.next_context
                    response = random.choice(self.prediction.responses)
                        
        else: # if bot needs to initiate a skill
            response = self.skill_response(u_input, None)

        return response

    def skill_response(self, u_input:str, intentID:int, **kwargs)->str:
        try:
            inst = self.skill_instances[self.context]
        except KeyError:
            skill_cls = self.db_client.get_skill(self.context)
            inst = getattr(skills, skill_cls)()
            self.skill_instances[self.context] = inst

        response, self.skill_stage, next_intent = inst.respond_to(u_input, self.skill_stage, intentID, **kwargs)
        
        if next_intent is not None:
            if self.context == CONFIG["clarify_context"]:
                response = self.respond_via_intent(self.prev_input, self.parent_context, next_intent)
            else:
                response = self.respond_via_intent(u_input, self.parent_context, next_intent)
        else:
            if self.skill_stage == -1:
                if self.context == CONFIG["clarify_context"]:
                    self.context = CONFIG["root_context"]
                else:
                    self.context = self.parent_context

        return response

    def respond_via_intent(self, u_input:str, context:str, intent:str)->str:
        response = None
        intent_row = self.db_client.get_intent(intent, context)[0]
        responses = intent_row[3]
        intent_type = intent_row[6]
        intentID = intent_row[0]
        next_context = intent_row[5]
        
        if intent_type == "skill":
            self.skill_stage = 0
            self.parent_context = context
            self.context = next_context # skill name will be the next_context in the database
            response = self.skill_response(u_input, intentID)  
        else:
            self.context = next_context if next_context != 'self' else self.parent_context
            response = random.choice(responses)

        return response

    def learn_intents(self, topics:List[Dict]):
        for topic in tqdm(topics, desc="learning intents"):
            self.model_api.learn_intents(\
                topic["intents"], topic["context"])
