# standard imports
from collections import namedtuple
from enum import Enum, auto
from msilib.schema import Class
from queue import Queue
import os

# third party imports
import joblib

# local imports
from src.core_intent_matcher.model import Model
import src.common as common

CONFIG = common.CONFIG['model']

QueueItem = namedtuple('QueueItem', ['key', 'val']) 

class PriorityQueue:
    """used for holding items with priority/relevancy taken into
    account. The most used item is least likely to be popped out
    during explicit pop operation or when queue surpasses its capacity.
    """

    def __init__(self, init_queue=[], capacity=None):
        """initiates priority queue instance

        :param init_queue: initial queue represented as a list, defaults to [].
        The order of the items in the initial queue determine their relevancy, i.e.
        first item is most relevant.
        :param capacity: limits number of items that can be
        set, the queue will kick out less relevant item
        if queue is beyond capacity, defaults to None
        """

        self.queue = [QueueItem(item[0], item[1]) for item in init_queue]
        self.capacity = capacity

    def setitem(self, key, value)->QueueItem:
        """set a key-value pair for the priority queue.
        The new pair will be set at the middle of the queue
        in terms of relevancy.

        :param key: sets key of key-value pair
        :param value: sets value of the key-value pair
        :return: return the item that has been popped if
        the queue was beyond capacity
        """
        popped_item = None

        if key in self.keys():
            item_idx = self.keys().index(key)
            self.queue[item_idx] = QueueItem(key, value)
        else:
            self.queue.insert(len(self) // 2, QueueItem(key, value))

            if self.capacity and len(self) > self.capacity:
                popped_item = self.pop_worst()

        return popped_item

    def getitem(self, key:str)->QueueItem:
        """gets the key-pair item of the corresponding key.
        The priority queue will shift the fetched item up
        a rank as a side effect.

        :param key: identifying key corresponding to desired value
        :return: Queueitem object which contains the key and value
        that corresponds to specified key
        :rtype: QueueItem
        """
        value = None
        for i, item in enumerate(self.queue):
            if key == item.key:
                value = item.val
                if i: # increase item relevancy
                    self.queue[i - 1], self.queue[i] = \
                        self.queue[i], self.queue[i - 1]
        if value is None:
            raise KeyError
        return QueueItem(key, value)

    def __getitem__(self, key:str):
        """purely gets the key-pair item of the corresponding key.
        The priority queue will NOT shift the fetched item up
        a rank as a side effect.

        :param key: key that corresponds to the desired value
        :return: value that corresponds to the specified key
        """
        value = None
        for i, item in enumerate(self.queue):
            if key == item.key:
                value = item.val
        if value is None:
            raise KeyError
        return QueueItem(key, value)

    def pop_worst(self)->QueueItem:
        """pops the least relevant item in queue

        :return: least relevant queue item
        """
        return self.queue.pop()

    def pop(self, key:str)->QueueItem:
        """pops an item in the queue given the key

        :param key: identifying key associated with item
        :type key: str
        :return: item of priority queue
        :rtype: QueueItem
        """
        value = None
        for i, item in enumerate(self.queue):
            if key == item.key:
                value = self.queue.pop(i)
        return QueueItem(key, value)
        

    def peek_best(self)->QueueItem:
        """peeks at the most relevant item in queue

        :return: most relevant item in queue
        """
        result = None
        try:
            result = self.queue[0]
        except IndexError:
            pass
        return result

    def __len__(self)->int:
        """returns length of the queue

        :return: queue length
        """
        return len(self.queue)

    def keys(self)->list:
        """returns all keys in PriorityQueue instance

        :return: all keys in the queue
        :rtype: list
        """
        return [item.key for item in self.queue]

class ModelNotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)

class ModelAlreadyQueuedError(Exception):
    def __init__(self, message):
        super().__init__(message)

class ModelNameExistsError(Exception):
    def __init__(self, message):
        super().__init__(message)    

class ModelNameExistsError(Exception):
    def __init__(self, message):
        super().__init__(message)

class PriorityQueueAlreadyExistsError(Exception):
    def __init__(self, message):
        super().__init__(message)

# class PriorityQueueDoesntExistError(Exception):
#     def __init__(self, message):
#         super().__init__(message)

class ModelState(Enum):
    CURRENT = auto()
    QUEUED = auto()
    STORED = auto()

@common.singleton
class ModelPool:
    """class for storing models. It optimizes this by
    shuffling classifier models in between three states:
    currently selected, queued and stored. The queued state
    indicates that the model is cached in memory, whereas stored
    means that it is stored on disk.
    """

    MODEL_DIR = "models"

    def __init__(self, init_queue=None):
        """instantiate the ModelStateManager class

        :param init_queue: for populating the priority queue.
        :type init_queue: PriorityQueue
        """
        self.model_states = {}
        if hasattr(self, 'queue'):
            if init_queue:
                raise PriorityQueueAlreadyExistsError("queue has already been initialized!")
        else:
            if init_queue:
                self.register_all_stored()
                self.set_queue(init_queue)
            else:
                self.register_all_stored()
                self.set_queue(PriorityQueue())
                self.queue_all_stored()

    def register_all_stored(self):
        models_list = os.listdir(CONFIG['storage_dir'])
        models_list = list(map(lambda x: x.replace(".joblib", ""), models_list))

        for model_name in models_list:
            self.model_states[model_name] = ModelState.STORED


    def queue_all_stored(self):
        models_list = os.listdir(CONFIG['storage_dir'])
        models_list = list(map(lambda x: x.replace(".joblib", ""), models_list))

        for model_name in models_list:
            self.queue_model(model_name)

    def set_queue(self, init_queue:PriorityQueue):
        self.queue = init_queue
        
        queued_states = {model_name: ModelState.QUEUED \
            for model_name in self.queue.keys()}
        self.model_states.update(queued_states)

        self.cur_model = self.queue.peek_best() # cur_model is a QueueItem instance
        if self.cur_model:
            self.model_states[self.cur_model.key] = ModelState.CURRENT

    def __getitem__(self, model_name:str)->Model:
        """purely gets the classifier model via its specified name 
        regardless of its state. It will not alter the state of the
        model as a side effect. It will, however, alter
        its relevancy in the priority queue.

        :param model_name: name of the model associated with the
        classifier object.
        :type model_name: str
        :raises ModelNotFoundError: for when model specified
        is not found as STORED, QUEUED or CURRENT
        :return: the classifier model associated with model_name
        parameter
        :rtype: Classifier
        """
        model = None
        state = None

        try:
            state = self.model_states[model_name]
        except KeyError:
            raise ModelNotFoundError(f"model '{model_name}' not found.")

        if state == ModelState.CURRENT:
            model = self.cur_model.val
        elif state == ModelState.QUEUED:
            model = self.queue[model_name].val
        elif state == ModelState.STORED:
            model = self.load_model(model_name)

        return model

    def select_model(self, model_name:str)->Model:
        """puts model as CURRENT state, returns model
        and alters their priority queue
        relevancy and state as side effects. 

        :param model_name: identifier associated with the model to be returned
        :type model_name: str
        :raises ModelNotFoundError: if model has not been found as
        STORED, QUEUED or CURRENT
        :return: classifier model that has been put in CURRENT state
        :rtype: Classifier
        """
        state = None
        model = None
        try:
            state = self.model_states[model_name]
        except KeyError:
            raise ModelNotFoundError(f"model '{model_name}' not found.")

        if state == ModelState.STORED:
            self.queue_model(model_name)
            self.cur_model = self.queue.getitem(model_name)
        elif state == ModelState.QUEUED:
            self.cur_model = self.queue.getitem(model_name)
            
        if self.cur_model.val:
            model = self.cur_model.val

        return model

    def queue_model(self, model_name):
        """transfers the model from just being stored on the disk
        to being cached and queued on the priority queue. It
        puts the model from STORED to QUEUED state.

        :param model_name: identifier name associated with the model
        :type model_name: str
        :raises ModelNotFoundError: if the model could not be found as
        STORED, QUEUED or CURRENT
        :raises ModelAlreadyQueuedError: if the model is already found
        to be QUEUED or CURRENT
        """

        state = None
        try:
            state = self.model_states[model_name]
        except KeyError:
            raise ModelNotFoundError(f"model '{model_name}' not found.")

        if state == ModelState.QUEUED or state == ModelState.CURRENT:
            raise ModelAlreadyQueuedError(f"model '{model_name}' already queued.")
            
        model = self.load_model(model_name)
        popped_model = self.queue.setitem(model_name, model)
        if popped_model:
            self.store_model(*popped_model)
            self.model_states[popped_model.key] = ModelState.STORED

        self.model_states[model_name] = ModelState.QUEUED

    def add_model(self, model_name:str, model:Model):
        """adds a new classifier model to the ModelStateManager class

        :param model_name: identifier name associated with the model
        :type model_name: str
        :param model: model classifier to be stored in ModelStateManager
        :type model: Classifier
        :raises ModelNameExistsError: if another model already exists with the 
        same identifier name
        """
        if model_name in self.queue.keys():
            raise ModelNameExistsError(f"model '{model_name}' already exists.")
            
        self.store_model(model_name, model)
        self.model_states[model_name] = ModelState.STORED


    def load_model(self, model_name:str)->Model:
        """wrapper method for joblib.load with
        ability to use the filename() method to
        format the model_name into the correct filepath
        to load model from

        :param model_name: identifier name associated with the model
        :type model_name: str
        :return: the classifier model loaded from storage
        :rtype: Classifier
        """
        return joblib.load(self.model_filename(model_name))

    def store_model(self, model_name:str, model:Model):
        """stores the model and puts it as STORED state

        :param model_name: identifying name of the model object
        :type model_name: str
        :param model: classifier model to store
        :type model: Classifier
        """
        joblib.dump(model, self.model_filename(model_name))

    def del_model(self, model_name):
        """deletes the model file
        """
        os.remove(self.model_filename(model_name))

    def pop_model(self, model_name:str)->Model:
        """pops a model out of the model pool

        :param model_name: identifying name of the model
        :type model_name: str
        :raises ModelNotFoundError: is raised if model is not found in pool
        :return: classifier model that has been popped
        :rtype: Classifier
        """
        model = None
        state = None

        try:
            state = self.model_states[model_name]
        except KeyError:
            raise ModelNotFoundError(f"model '{model_name}' not found.")

        if state == ModelState.CURRENT:
            model = self.queue.pop(model_name)
            self.cur_model = self.queue.peek_best()
            self.del_model(model_name)
        elif state == ModelState.QUEUED:
            model = self.queue.pop(model_name)
            self.del_model(model_name)
        elif state == ModelState.STORED:
            self.del_model(model_name)

        del self.model_states[model_name]

        return model

    class GetModel:
        """the ModelPool's context manager. It serves
        to automatically store models after use and
        emulates the 'release' of the models in the code,
        just like in an Object Pool pattern.
        """
        def __init__(self, model_name:str, change_priority=False):
            self.pool = ModelPool()
            self.model_name = model_name
            self.change_priority = change_priority
            if self.change_priority:
                self.model = self.pool.select_model(self.model_name)
            else:
                self.model = self.pool[self.model_name]

        def __enter__(self)->Model:
            return self.model

        def __exit__(self, exc_type, exc_value, exc_traceback):
            self.pool.store_model(self.model_name, self.model)

    def model_filename(self, name:str):
        """formats a specified model name into the filepath
        that it would typically be stored in. It uses
        MODEL_DIR and FILE_SUFFIX constants to format.

        :param name: name of the model
        :return: formatted corresponding filepath of the model
        """
        return CONFIG["storage_dir"] + "/" + name + CONFIG["file_suffix"]