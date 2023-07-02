# standard imports 
from abc import ABC, abstractmethod, abstractproperty
from typing import List, Tuple
import random

# third party imports
import nltk

# local imports
import src.common as common

# this module contains all essential components for making a skill

CONFIG = common.CONFIG["skill_interface"]

class Skill(ABC):
    """abstract base class for child skill classes.
    It standardises the writing of any skill classes
    by enforcing a respond_to() method and 'name' property.
    Skills are classes instead of single functions in order to
    store any skill-specific variables or resources.
    """

    @abstractmethod
    def respond_to(self, u_input:str, stage:int, intentID:int, **kwargs)->tuple[str,int,str]:
        """the primary method for responding to user inputs. Child
        classes can be written to respond or process user input
        in any way but must follow this abstract method's signature
        for standardization.

        :param u_input: user input
        :type u_input: str
        :param stage: number that describes how far the user
        has interacted with the skill
        :type stage: int
        :return: must return the skill's response and then the next
        stage number in a tuple. i.e. (response, stage)
        :rtype: tuple[str,int]
        """
        pass

    @abstractproperty
    def name(self):
        pass

skills_register = {}

repeats = 0
prev_respond_func = None
prev_stage = None
def repeat_with_chances(respond_func):
    """decorator that repeats any skill response. The number of repeats depends on the configuration settings."""

    def inner(*args, **kwargs):
        global repeats, prev_respond_func, prev_stage

        response, next_stage, context = respond_func(*args,**kwargs)
        if respond_func is prev_respond_func and args[2] == prev_stage:
            repeats += 1
            if CONFIG["max_repeats"] != -1 and repeats >= CONFIG["max_repeats"]:
                response = random.choice(common.GIVE_UP_RESPONSES)
                next_stage = -1
        else:
            repeats = 0
        prev_respond_func, prev_stage = respond_func, args[2]
        return response, next_stage, context
    return inner