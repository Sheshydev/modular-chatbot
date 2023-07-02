# standard imports
import sqlite3
import ast
# third party imports

# local imports
import src.common as common

def literal_eval_row(row:tuple):
    return *row[:2], ast.literal_eval(row[2]), ast.literal_eval(row[3]), *row[4:]

CONFIG = common.CONFIG["db_client"]

@common.singleton
class DB_Client:
    """ a class for abstracting database queries
        that are common for storing data for the bag
        of words model 
    """

    def __init__(self):
        """create instance of DB_Client. 
        It creates a connection to the database and
        the database if it does not exist.

        :param db_name: name of the database to connect to or create
        """
        def connect_db():
            self.conn = sqlite3.connect(CONFIG["db_name"])
            self.cur = self.conn.cursor()

        if hasattr(self, "conn"):
            if not self.is_conn():
                connect_db()
        else:
            connect_db()

        self.create_global_vars_table()
        self.create_intents_table()
        self.create_skills_table()
        self.create_users_table()

    def is_conn(self):
        result = False
        try:
            self.conn.cursor()
            result = not result
        except sqlite3.ProgrammingError:
            pass

        return result
            

    def create_intents_table(self):
        """creates a table for storing intents

        :param context: name of context to create table for
        """
        
        self.cur.execute("CREATE TABLE IF NOT EXISTS intents( \
                intentID INTEGER PRIMARY KEY AUTOINCREMENT, \
                intent TEXT, \
                matches TEXT, \
                responses TEXT, \
                context TEXT, \
                link TEXT, \
                intent_type TEXT \
            )"
        )

    def drop_table(self, table_name:str):
        """drop a specified table

        :param table_name: the table's identifying name
        :type table_name: str
        """
        self.cur.execute(f"DROP TABLE {table_name}")
        self.conn.commit()
    
    def insert_intent(self, intent:str, matches:list, responses:list, context:str, link:str, intent_type:str)->int:
        """inserts an intent into the database

        :param context: name of context to insert intent into
        :param intent: name of intent
        :param matches: list of matches for the intent
        :param response: response to intent
        :param context: context associated with intent
        :param link: link to intent
        :param intent_type: type of intent
        """

        self.cur.execute("INSERT INTO intents (intent, matches, responses, context, link, intent_type) \
            VALUES (?, ?, ?, ?, ?, ?)", (intent, str(matches), str(responses), context, link, intent_type))
        self.conn.commit()
        self.cur.execute("SELECT last_insert_rowid()")
        return self.cur.fetchone()[0]


    def insert_intents_json(self, json_data:dict, context:str):
        """inserts intents from json file into database

        :param context: name of context to insert intents into
        :param json_data: json data to insert
        """
        row_ids = []

        for intent in json_data:
            intent_data = json_data[intent]

            row_id = self.insert_intent(intent, intent_data["matches"], intent_data["responses"], \
                context, intent_data["link"], intent_data["type"])
            row_ids.append(row_id)
        return row_ids

    def get_intents(self, context:str):
        """returns a list of intents from a specified context.
        The list contains tuples which correspond to the rows
        of the database:
        (intentID, intent, matches, responses, context, link, intent_type)

        :param context: name of context to get intents from
        """

        self.cur.execute(f"SELECT * FROM intents WHERE context='{context}'")
        return list(map(literal_eval_row, self.cur.fetchall()))

    def get_intent(self, intent:str, context:str):
        """returns a specific intent with specific context

        :param intent: intent to return
        :type intent: str
        :param context: context in which the intent is based
        :type context: str
        """

        self.cur.execute(f"SELECT * FROM intents WHERE intent='{intent}' AND context='{context}'")
        query_result = self.cur.fetchone()
        
        return [] if query_result is None\
            else list(map(literal_eval_row, [query_result]))

    def drop_intent(self, intent:str, context:str)->int:
        """drop an intent from the intents table

        :param intent: identifying name of the intent
        :type intent: str
        :param context: identifying name of the context
        :type context: str
        :return: number of rows with the context left after deletion. 
        If none were deleted, then -1 is returned
        :rtype: int
        """
        self.cur.execute(\
            f"SELECT COUNT(intentID) FROM intents WHERE context='{context}'")
        count_bef = self.cur.fetchone()[0]

        if count_bef:
            self.cur.execute(f"DELETE FROM intents WHERE intent='{intent}' AND context='{context}'")
            self.conn.commit()
        
            self.cur.execute(\
                f"SELECT COUNT(intentID) FROM intents WHERE context='{context}'")
            count_aft = self.cur.fetchone()[0]

            return count_aft if count_bef > count_aft else -1
        else:
            return -1

    def drop_context(self, context:str):
        self.cur.execute(\
            f"SELECT COUNT(intentID) FROM intents WHERE context='{context}'")
        count = self.cur.fetchone()[0]

        if count:
            self.cur.execute(f"DELETE FROM intents WHERE context='{context}'")
            return 0
        else:
            return -1

    def update_intent_matches(self, intentID:int, matches:list):
        """updates the matches column of the intents table for
        a specific intent

        :param intentID: identifying number of intent to update
        :type intent: str
        :param matches: new list of user dialogues used to match with intent
        :type matches: list
        """
        intentID = str(intentID)
        matches = str(matches)
        matches = matches.replace("'", "''")

        self.cur.execute(f"UPDATE intents SET matches='{matches}' WHERE intentID={intentID}")
        self.conn.commit()

    def update_intent_responses(self, intent:str, context:str, responses:list):
        """updates the 'context' column of the intents table 
        for a specific intent

        :param intent: intent to update
        :type intent: str
        :param context: context in which intent is based
        :type context: str
        :param responses: new list of machine dialogues used to match with intent
        :type responses: list
        """
        responses = str(responses)
        responses = responses.replace("'", "''")

        self.cur.execute(f"UPDATE intents SET responses='{responses}' WHERE intent='{intent}' AND context='{context}'")
        self.conn.commit()

    def get_intent_by_idx(self, intentID:int)->tuple:
        """fetches a row from the intents table via intentID

        :param idx: primary key of the row
        :type idx: int
        :return: row containing the intentID
        :rtype: tuple
        """
        self.cur.execute(f"SELECT * FROM intents WHERE intentID={intentID}")
        row = self.cur.fetchone()
        return *row[:2], ast.literal_eval(row[2]), ast.literal_eval(row[3]), *row[4:]

    def create_skills_table(self):
        """create a table for mapping skills with their
        identifying name.
        """
        self.cur.execute("CREATE TABLE IF NOT EXISTS skills( \
                skillID INTEGER PRIMARY KEY AUTOINCREMENT, \
                skill_name TEXT, \
                class TEXT \
            )"
        )
        self.conn.commit()

    def insert_skill(self, skill_name:str, _class):
        """inserts a mapping of a skill's class object name to its identifying
        name.

        :param skill_name: identifying name of the skill
        :type skill_name: str
        :param _class: skill's corresponding class
        :type _class: Callable
        """
        self.cur.execute(f"SELECT * FROM skills WHERE \
            skill_name = '{skill_name}'")

        if self.cur.fetchone() is not None:
            return -1

        self.cur.execute("INSERT INTO skills (skill_name, class) \
            VALUES (?, ?)", (skill_name, _class.__name__)
        )
        self.conn.commit()
        self.cur.execute("SELECT last_insert_rowid()")
        return self.cur.fetchone()[0]


    def get_skill(self, skill_name:str):
        """gets the class name of a skill via its identifying name

        :param skill_name: skill_name
        :type skill_name: str
        """
        self.cur.execute(f"SELECT class FROM skills WHERE skill_name='{skill_name}'")
        result = self.cur.fetchone()
        result = None if result is None else result[0]
        return result

    def drop_skill(self, skillID:int):
        """removes a skill from the skills table via skillID

        :param skillID: identifying number of the skill
        :type skillID: int
        """
        skillID = str(skillID)
        self.cur.execute(f"DELETE FROM skills WHERE \
            skillID='{skillID}'")
        self.conn.commit()

    def create_global_vars_table(self):
        """create a table of key-value pairs of global variables
        with their corresponding user id
        """
        self.cur.execute("CREATE TABLE IF NOT EXISTS global_vars( \
                varID INTEGER PRIMARY KEY AUTOINCREMENT, \
                key TEXT, \
                val TEXT, \
                uid TEXT \
            )"
        )

    def insert_global_var(self, key:str, val:str, uid=0):
        """insert a key-value pair into the global variables
        table

        :param key: key of the global variable
        :type key: str
        :param val: value of the global variable
        :type val: str
        :param uid: user id associated with the global variable
        :type uid: int
        """
        uid = str(uid)
        self.cur.execute("INSERT INTO global_vars (key, val, uid) \
            VALUES (?, ?, ?)", (key, val, uid)
        )
        self.conn.commit()
    
    def get_global_var(self, key:str, uid=0):
        """get the value of a global variable

        :param key: identifying key of the global variable
        :type key: str
        :param uid: user id associated with the global variable
        """
        uid = str(uid)
        self.cur.execute(f"SELECT val FROM global_vars WHERE key='{key}' AND uid='{uid}'"
        )
        result = self.cur.fetchone()
        result = None if result is None else result[0]
        return result

    def update_global_var(self, key:str, val:str, uid=0):
        """update a key-value pair from the global variables table

        :param key: key of the global variable
        :type key: str
        :param val: value of the global variable
        :type val: str
        :param uid: user id associated with the global variable
        :type uid: int
        """
        uid=str(uid)

        count_before = self.cur.execute(f"SELECT COUNT(*) FROM global_vars WHERE \
            key='{key}' AND uid='{uid}'").fetchone()[0]

        if count_before:
            self.cur.execute(f"UPDATE global_vars SET val='{val}' \
                WHERE key='{key}' AND uid='{uid}'"
            )
            self.conn.commit()
        else:
            self.insert_global_var(key, val, uid)
            self.update_global_var(key, val, uid)
    
    def drop_global_var(self, key:str, uid:int):
        """drop a key-value pair from the global variables table

        :param key: key of the global variable
        :type key: str
        :param val: value of the global variable
        :type val: str
        :param uid: user id associated with the the global variable
        :type uid: int
        """
        uid=str(uid)
        self.cur.execute(f"DELETE FROM global_vars WHERE \
            key='{key}' AND uid='{uid}'")
        self.conn.commit()

    def create_users_table(self):
        """create a table of users with uid and name columns
        """
        self.cur.execute("CREATE TABLE IF NOT EXISTS users( \
                uid INTEGER PRIMARY KEY AUTOINCREMENT, \
                name TEXT \
            )"
        )
        self.conn.commit()

    def insert_user(self, name:str)->int:
        """insert a user into the users table

        :param name: name of user
        :type name: str
        :return: database index of user
        :rtype: int
        """
        self.cur.execute(f"INSERT INTO users (name) \
            VALUES ('{name}')"
        )
        self.conn.commit()
        self.cur.execute("SELECT last_insert_rowid()")
        return self.cur.fetchone()[0]

    def update_user(self, uid:int, name:str):
        """update the users table

        :param uid: user's uid
        :type uid: int
        :param name: name of the user
        :type name: str
        """
        uid = str(uid)
        self.cur.execute(f"UPDATE users SET name='{name}' \
            WHERE uid='{uid}'"
        )
        self.conn.commit()

    def drop_user(self, uid:int):
        """remove a row from the users table

        :param uid: uid of the user in the database
        :type uid: int
        """
        uid = str(uid)
        self.cur.execute(f"DELETE FROM users WHERE \
            uid='{uid}'")
        self.conn.commit()
    
    def get_name_by_uid(self, uid:int)->str:
        """get the name of a user by uid

        :param uid: uid of the user in the database
        :type uid: int
        :return: name of user
        :rtype: str
        """
        uid = str(uid)
        self.cur.execute(f"SELECT name FROM users WHERE \
            uid='{uid}'")
        result = self.cur.fetchone()
        result = None if result is None else result[0]
        return result

    def get_uid_by_name(self, name:str)->int:
        """get the uid of a user by name

        :param uid: uid of the user in the database
        :type uid: int
        :return: name of user
        :rtype: str
        """
        self.cur.execute(f"SELECT uid FROM users WHERE \
            name='{name}'")
        result = self.cur.fetchone()
        result = None if result is None else int(result[0])
        return result
