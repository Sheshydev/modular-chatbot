# standard imports 
from atexit import register
import random
import datetime
import ast
import os

# third party imports
import joblib
import nltk
from nltk.stem.porter import PorterStemmer
from nltk import word_tokenize
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# local imports
import re
from src.skills.skill_interface import Skill, repeat_with_chances
from src.db_client import DB_Client
import src.common as common
from src.core_intent_matcher.modelAPI import ModelAPI

CONFIG = common.CONFIG["misc"]

class Greet(Skill):
    def __init__(self):
        self.db_client = DB_Client()

    @property
    def name(self):
        return "greet"

    def respond_to(self, u_input:str, stage:int, intentID:int, **kwargs)->tuple[str,int,str]:
        if stage == 0:
            current_uid = self.db_client.get_global_var("current_uid")
            current_uid = int(current_uid) if current_uid is not None else None
            if current_uid is None:
                return (f"Hi there, I don't think we've met. What Should I call you by?", 1, None)
            else:
                self.current_uid = current_uid
                cur_time = datetime.datetime.now()
                hour = cur_time.hour
                day_period = "evening"
                if hour < 18:
                    day_period = "afternoon"
                if hour < 12:
                    day_period = "morning"

                self.u_name = self.db_client.get_name_by_uid(int(self.current_uid))

                return (f"good {day_period} {self.u_name}!", -1, None)

        elif stage == 1: # bot processes user's name and then greets them
            self.u_name = common.get_name(u_input)

            if self.u_name:
                self.current_uid = self.db_client.insert_user(self.u_name)
                self.db_client.insert_global_var("current_uid", str(self.current_uid))

                botname = CONFIG["botname"]
                return (f"Nice to meet you {self.u_name}! You can call me {botname}. Can I also ask what your favourite movie is?", 2, None)
            else:
                return (random.choice(common.ERROR_RESPONSES), 1, None)

        elif stage == 2:
            fav_movie = common.get_favourite(u_input)

            if fav_movie is not None:
                self.db_client.insert_global_var('fav_movie', fav_movie, self.current_uid)
                return (f"You have good taste {self.u_name}! Who is your favourite director?", 3, None)
            else:
                return (random.choice(common.ERROR_RESPONSES), 2, None)

        elif stage == 3:
            fav_director = common.get_favourite(u_input)

            if fav_director is not None:
                self.db_client.insert_global_var('fav_director', fav_director, self.current_uid)
                return (f"I've heard about them, they make amazing movies! Now you should try asking me questions! Try asking me to book a movie ticket!", -1, None)
            else:
                return (random.choice(common.ERROR_RESPONSES), 3, None)

class TellTime(Skill):
    @property
    def name(self):
        return "time"

    @repeat_with_chances
    def respond_to(self, u_input:str, stage:int, intentID:int, **kwargs)->tuple[str,int,str]:
        if stage == 0:
            cur_time = datetime.datetime.now()
            return (f"It is currently {cur_time.hour}:{cur_time.minute}", -1, None)

class ChangeUser(Skill):

    def __init__(self):
        self.db_client = DB_Client()

    @property
    def name(self):
        return "change_user"

    @repeat_with_chances
    def respond_to(self, u_input:str, stage:int, intentID:int, **kwargs)->tuple[str,int,str]:
        cur_uid = self.db_client.get_global_var("current_uid")
        cur_name = self.db_client.get_name_by_uid(cur_uid)
        if stage == 0:
            return (f"Sorry, I thought you were {cur_name}. How can I call you?", 1, None)
        
        elif stage == 1:
            u_name = common.get_name(u_input)

            if u_name is not None:
                uid = self.db_client.get_uid_by_name(u_name)
                if uid is not None:
                    self.db_client.update_global_var("current_uid", str(uid))
                    return (f"Hi again {u_name}, how can I help you?", -1, None)
                else:
                    new_uid = self.db_client.insert_user(u_name)
                    self.db_client.update_global_var("current_uid", str(new_uid))
                    return (f"Nice to meet you {u_name}! May I ask you what your favourite movie is?", 2, None)
            else:
                return (random.choice(common.ERROR_RESPONSES), -1, None)

        elif stage == 2:
            fav_movie = common.get_favourite(u_input)

            if fav_movie is not None:
                self.db_client.insert_global_var('fav_movie', fav_movie, cur_uid)
                return (f"You have good taste {cur_name}! Can I also ask who your favourite director is?", 3, None)
            else:
                return (random.choice(common.ERROR_RESPONSES), -1, None)

        elif stage == 3:
            fav_director = common.get_favourite(u_input)

            if fav_director is not None:
                self.db_client.insert_global_var('fav_director', fav_director, cur_uid)
                return (f"I've heard about them, they make amazing movies! Now you should try asking me questions! Try asking me to book a movie ticket!", -1, None)
            else:
                return (random.choice(common.ERROR_RESPONSES), 3, None)

class ClarifyIntent(Skill):
    def __init__(self):
        self.db_client = DB_Client()
        self.model_api = ModelAPI()

    @property
    def name(self):
        return "clarify_intent"

    @repeat_with_chances
    def respond_to(self, u_input:str, stage:int, intentID: int, **kwargs)->tuple[str,int,str]:
        if stage==0:
            self.last_input = u_input
            choices = kwargs["choices"]
            choices = [intentID for intentID, _ in choices]
            self.choices = {('a', 'b', 'c')[i]: (choice, self.db_client.get_intent_by_idx(choice)[1]) \
                for i, choice in enumerate(choices[:3])}

            return (f"Sorry I couldn't understand. What do you want to talk about? (please enter A, B, C or D),\
                \n\nA) {self.choices['a'][1]}\nB) {self.choices['b'][1]}\nC) {self.choices['c'][1]}\nD) None of the above\n", 1, None)
        
        elif stage==1:
            if u_input in ['a', 'b', 'c', 'A', 'B', 'C']:
                intent_idx = self.choices[u_input.lower()][0]
                intent_row = self.db_client.get_intent_by_idx(intent_idx)
                intent, matches, intent_type = intent_row[1], intent_row[2], intent_row[6]
                matches.append(self.last_input)
                skill_stage = 0 if intent_type == 'skill' else -1
                
                self.model_api.add_intent_matches(intent_idx, matches)

                return (f"Sure! let's talk about it.", skill_stage, intent)
            elif u_input in ['d', 'D']:
                return (f"Sorry I couldn't help you, maybe we could talk about something else.", -1, None)
            else:
                return ("Sorry, I couldn't understand. Please enter a letter, either A, B, C or D", 1, None)

class Template(Skill):
    def __init__(self):
        self.db_client = DB_Client()

    @property
    def name(self):
        return "template"

    def respond_to(self, u_input:str, stage: int, intentID: int, **kwargs)->tuple[str,int,str]:
        if stage==0:
            uid = self.db_client.get_global_var("current_uid")
            template = random.choice(self.db_client.get_intent_by_idx(intentID)[3]) # responses have special characters so they can be used as templates

            var_keys = re.findall(r'\$\w+\$', template)
            var_keys = list(map(lambda x: re.sub(r'\$', '', x), var_keys))
            for var_key in var_keys:
                global_var = self.db_client.get_global_var(var_key, uid=uid)
                if global_var is not None:
                    template = template.replace('$'+var_key+'$', global_var)
                else:
                    return ("I'm sorry, I don't think I have enough information to answer that", -1, None)
            
            return (template, -1, None)

class Emotive(Skill):
    def __init__(self):
        SVM_PATH = 'src/skill_assets/emotive/linearsvm.joblib'
        self.db_client = DB_Client()
        self.classifier = joblib.load(SVM_PATH)['clf']
        self.vectorizer = joblib.load(SVM_PATH)['vectorizer']
        self.tfidf_transformer = joblib.load(SVM_PATH)['tfidf']
        self.current_uid = self.db_client.get_global_var("current_uid")
        self.pstemmer = PorterStemmer()

    @property
    def name(self):
        return "emotive"

    def respond_to(self, u_input: str, stage: int, intentID: int, **kwargs)->tuple[str, int, str]:
        if stage == 0:
            responses = self.db_client.get_intent_by_idx(intentID)[3]
            proba_interval = 1 / len(responses)

            u_input = u_input.lower()
            u_input_tokens = word_tokenize(u_input)
            u_input_tokens = [self.pstemmer.stem(token) for token in u_input_tokens if token not in ENGLISH_STOP_WORDS]
            u_input = ' '.join(u_input_tokens)

            count_vec = self.vectorizer.transform([u_input])
            tfidf_vec = self.tfidf_transformer.transform(count_vec)
            positive_pred = self.classifier.predict_proba(tfidf_vec)[0][1]
            
            response_idx = int(positive_pred / proba_interval)

            return (responses[response_idx], -1, None)
            
class BookMovie(Skill):

    def __init__(self):
        self.db_client = DB_Client()
        self.movie_sessions = {
            "The Dark Knight" : ("4:30pm", "Savoy Cinema"),
            "Pulp Fiction" : ("5:20pm", "Cineworld"),
            "Lord of the Rings" : ("7:10pm", "CinePlex"),
            "The Shawshank Redemption" : ("10:00pm", "GoodFilms Cinema")
        }
        self.movies = list(self.movie_sessions.keys())

    @property
    def name(self):
        return "book_movie"

    def respond_to(self, u_input: str, stage: int, intentID: int, **kwargs)->tuple[str, int, str]:
        match stage:
            case 0:
                self.current_uid = self.db_client.get_global_var("current_uid")
                movies_str = ', '.join(self.movies)
                return (f"Sure! What movie would you like to book for? Here are the available movies at the cinemas : {movies_str}", 1, None)
            case 1:
                reg_bef = r'(watch|see|view) '
                reg_aft = r'(\s|\w|\d)+'
                u_input_movie = common.extract_what_comes_after(u_input, reg_bef, reg_aft)
                distances = list(map(lambda x: common.levenshtein(x, u_input_movie), self.movies))
                movies_n_dist = list(zip(self.movies, distances))
                movies_n_dist.sort(key=lambda x: x[1])

                self.movie_to_book = movies_n_dist[0][0]
                
                return (f"Good shout! There is a session for {self.movie_to_book} at {self.movie_sessions[self.movie_to_book][0]}, at {self.movie_sessions[self.movie_to_book][1]}. Would you like to book it?", 2, None)
            case 2:
                if bool(re.search(r'(yes|yeah)', u_input)):
                    self.movie_to_book
                    time_to_book = self.movie_sessions[self.movie_to_book][0]
                    venue_to_book = self.movie_sessions[self.movie_to_book][1]

                    self.db_client.insert_global_var('book_movie_movie', self.movie_to_book, self.current_uid)
                    self.db_client.insert_global_var('book_movie_time', time_to_book, self.current_uid)
                    self.db_client.insert_global_var('book_movie_venue', venue_to_book, self.current_uid)
                
                    response = f"Okay, booking a session for {self.movie_to_book} at {time_to_book}, at {venue_to_book}"
                else:
                    response = "Okay, I didn't book any movie tickets"
                
                return (response, -1, None)

class AddToWatch(Skill):

    def __init__(self):
        self.db_client = DB_Client()

    @property
    def name(self):
        return "add_towatch"

    def respond_to(self, u_input: str, stage: int, intentID: int, **kwargs)->tuple[str, int, str]:
        match stage:
            case 0:
                self.current_uid = self.db_client.get_global_var("current_uid")
                reg_bef = r'^.*(add|put) '
                reg_aft = r' (to|onto|in|on) (my)? (watch list|to-watch list|watch-list).*'

                movie_no = self.db_client.get_global_var('movie_no',self.current_uid)
                if movie_no is None:
                    movie_no = 1
                    self.db_client.insert_global_var('movie_no', 1,self.current_uid)
                
                movie_no = int(movie_no)

                movie_to_watch = common.extract_between(u_input, reg_bef, reg_aft)
                self.db_client.insert_global_var(f'towatch_movie{movie_no}', movie_to_watch, self.current_uid)
                self.db_client.update_global_var('movie_no', movie_no + 1, self.current_uid)
                return (f"Sure! I added {movie_to_watch}", -1, None)

class ListToWatch(Skill):

    def __init__(self):
        self.db_client = DB_Client()

    @property
    def name(self):
        return "list_towatch"

    def respond_to(self, u_input: str, stage: int, intentID: int, **kwargs)->tuple[str, int, str]:
        uid = self.db_client.get_global_var('current_uid')
        match stage:
            case 0:
                u_name = self.db_client.get_name_by_uid(uid)
                response = f"Here are the movies you want to watch {u_name}!:" + os.linesep
                no_of_movies_in_list = self.db_client.get_global_var("movie_no", uid=uid)

                if no_of_movies_in_list is None:
                    response = "You don't have any movies in your watch list! You can add it by saying add X to my watch list."
                else:
                    for i in range(1,int(no_of_movies_in_list)):
                        movie_to_watch = self.db_client.get_global_var(f'towatch_movie{i}', uid=uid)
                        response += f"{i}. {movie_to_watch}{os.linesep}"
                return (response, -1, None)