# standard imports
from cgi import test
import unittest
# third party imports

# local imports
from src.model.model_pool import ModelNotFoundError, \
    PriorityQueue, QueueItem, ModelPool

class TempObj(object):
    pass

class TestPriorityQueue(unittest.TestCase):

    OBJ_AMOUNT = 100

    def test_getitem(self):
        test_key = "to_get"
        test_val = "test_return"

        init_queue = []
        for i in range(self.OBJ_AMOUNT):
            init_queue.append([str(i), i])
        self.pq = PriorityQueue(init_queue=init_queue)

        self.pq.setitem(test_key, test_val)

        self.assertEqual(self.pq[test_key], QueueItem(test_key, test_val))
        self.assertEqual(self.pq.getitem(test_key), QueueItem(test_key, test_val))

    def test_pop(self):
        test_key = "to_pop"
        test_val = "test_return"
        self.pq = PriorityQueue(init_queue=[])

        self.pq.setitem(test_key, test_val)
        for i in range(self.OBJ_AMOUNT):
            self.pq.setitem(str(i), i)
        
        for i in range(self.OBJ_AMOUNT):
            for _ in range(i):
                self.pq.getitem(str(i))
        
        self.assertEqual(self.pq.pop_worst(), QueueItem(test_key, test_val))

    def test_limited_pop(self):
        test_key = "to_pop"
        test_val = "test_return"
        
        pq = PriorityQueue(init_queue=[], capacity=self.OBJ_AMOUNT)
        pq.setitem(test_key, test_val)
        model_popped = None
        for i in range(self.OBJ_AMOUNT):
            model_popped = pq.setitem(str(i), i)

        self.assertEqual(model_popped, QueueItem(test_key, test_val))

        with self.assertRaises(KeyError):
            pq[test_key]
        
        with self.assertRaises(KeyError):
            pq.getitem(test_key)

    def test_keys(self):
        init_queue = []

        for i in range(self.OBJ_AMOUNT):
            init_queue.append([str(i), i])
        pq = PriorityQueue(init_queue=init_queue)

        expected_keys = [item[0] for item in init_queue]

        self.assertEqual(pq.keys(), expected_keys)

    def test_setitem_key_exists(self):
        key_to_set = str(self.OBJ_AMOUNT // 2)
        val_to_set = "set_value"
        init_queue = []

        for i in range(self.OBJ_AMOUNT):
            init_queue.append([str(i), i])
        pq = PriorityQueue(init_queue=init_queue)

        pq.setitem(key_to_set, val_to_set)

        self.assertEqual(pq.getitem(key_to_set), QueueItem(key_to_set, val_to_set))

    def test_peek_best(self):
        init_queue = []
        key_to_get = str(self.OBJ_AMOUNT//2 - 1)

        for i in range(self.OBJ_AMOUNT):
            init_queue.append([str(i), i])
        pq = PriorityQueue(init_queue=init_queue)

        for _ in range(self.OBJ_AMOUNT//2 - 1):
            pq.getitem(key_to_get)

        self.assertEqual(pq.peek_best(), QueueItem(key_to_get, int(key_to_get)))
        
class TestModelStateManager(unittest.TestCase):

    OBJ_AMOUNT = 100

    def test_getitem_model_not_exist(self):
        key_to_get = "key not exist"

        init_queue = []
        for i in range(self.OBJ_AMOUNT):
            init_queue.append([str(i), i])

        init_pq = PriorityQueue(init_queue)
        model_manager = ModelPool(init_pq)

        with self.assertRaises(ModelNotFoundError):
            model_manager[key_to_get]