

# standard imports
from collections import namedtuple
import re
# third party imports
import yaml
import nltk
# local imports

GIVE_UP_RESPONSES = [
    "I'm sorry that still couldn't understand, maybe I can help you with something else.",
    "Apologies, perhaps I can try to help you with something else."
]

ERROR_RESPONSES = [
    "I'm sorry I didn't understand. Could you please repeat?",
    "I'm sorry, could you please repeat it in another way.",
    "Apologies, I don't think I understood what you said.",
    "I'm sorry I didn't quite catch what you said.",
    "Sorry, could you please repeat what you said."
]

Prediction = namedtuple('Prediction', \
    ['intentID', 'responses', 'next_context', 'intent_type', 'confidence', 'possible_intents'])

CONFIG_FILE = "config.yaml"
with open(CONFIG_FILE, "r") as f:
    CONFIG = yaml.safe_load(f)

def singleton(cls):
    """this decorator converts a class into a singleton.
    Derived from Kevin D. Smith's implementation:
    https://peps.python.org/pep-0318/#examples

    :return: instance of the class
    """
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

def tokenize_n_tag(text:str):
    """tokenizes and tags text with enumeration

    :param text: text to be tokenized and tagged
    :type text: str
    :return: tokenized and POS tagged text
    :rtype: List[Tuple[str,str]]
    """
    tokens = nltk.word_tokenize(text)
    tagged = nltk.pos_tag(tokens)
    tagged = [(i, *x) for i, x in enumerate(tagged)]
    return tagged

def get_name(text:str):
    """function to extract and return proper nouns of a person. It will not
    return any names if there are two or more proper nouns in the text.
    If there is a first name and surname, the first name will be returned.

    :param text: text to extract name from
    :type text: str
    :return: first name to return
    :rtype: str
    """
    tokens = nltk.word_tokenize(text)
    tokens = [token.capitalize() for token in tokens if not token in nltk.corpus.stopwords.words()] # must capitalize every token or else we get false negatives for names
    tagged = nltk.pos_tag(tokens)
    enum_tagged = [(i, *x) for i, x in enumerate(tagged)]
    names = list(filter(lambda x: x[2] == 'NNP', enum_tagged))

    # Decides whether there is just one name in the user input.
    # Part of it is to see if there are adjacent proper noun tokens
    is_one_name = True if len(names) > 0 else False
    if len(names) > 1:
        prev_idx = names[0][0]
        for idx, _, _ in names[1:]:
            if idx != prev_idx + 1:
                is_one_name = False
            prev_idx = idx

    if is_one_name:
        u_name = names[0][1]
        if len(names) > 1:
            u_name = " ".join([name[1] for name in names])
        return u_name
    else:
        return None

def extract_what_comes_after(text, regex_key_words, regex_post_key_words):
    """extract what comes after the first regex pattern. Will return the whole
    string if no pattern was matched. Useful for extracting utterances like 'I like X',
    where X is returned. It will return X if only 'X' is inputted and the pattern is 'I like'

    :param text: just text. Something like user input
    :type text: str
    :param regex_key_words: key words or pattern that come before the substring to be extracted (e.g., 'I like' in 'I like X')
    :type regex_key_words: str
    :param regex_post_key_words: match what comes after the key words/pattern
    :type regex_post_key_words: str
    :return: returns the substring after the key words or pattern
    :rtype: str
    """
    result = None
    text_match = re.search(regex_key_words + regex_post_key_words, text.lower())
    if text_match is not None:
        text_match = text_match.group(0)
        text_match = re.sub(regex_key_words, '', text_match)
        result = text_match
    else:
        if len(text) != 0:
            result = text.lower()

    return result

def extract_between(text, regex_before, regex_after):
    """extract the substring between the two regexes

    :param text: text to be inputted
    :type text: str
    :param regex_before: text before the substring to be extracted
    :type regex_before: str
    :param regex_after: text after the substring to be extracted
    :type regex_after: str
    :return: substring in between two regexes
    :rtype: str
    """
    text = re.sub(regex_before, '', text)
    text = re.sub(regex_after, '', text)
    return text

def get_favourite(text):
    """uses extract_what_comes_after() to extract the user's favourite X.

    :param text: user input
    :type text: str
    :return: user's favourite something as uttered in user input
    :rtype: 
    """
    regex_key_words = r'(favourite|best|fave|fav) \w+ is '
    regex_post_key_words = r'(\s|\w)+'
    return extract_what_comes_after(text, regex_key_words, regex_post_key_words)


def levenshtein(txt1, txt2):
    """returns levenshtein distance of two strings. This levensthein implementation was derived from 
    the pseudocode presented in:
    'Levenshtein Distance Technique in Dictionary Lookup Methods: An Improved Approach' 
    by R. Haldar and D. Mukhopadhyay
    https://arxiv.org/abs/1101.1232
    6 Jan 2011

    :param txt1: first string
    :type txt1: str
    :param txt2: second string
    :type txt2: str
    :return: levenshtein distance of two strings
    :rtype: int
    """
    # Levenshtein distance derived from pseudocode from
    # 'Levenshtein distance Technique in Dictionary Lookup Methods' by Haldar and Mukhopadhyay 
    lev_mat = [[-1 for _ in range(len(txt2)+1)] for _ in range(len(txt1)+1)]
    for col in range(len(txt2)+1):
        lev_mat[0][col] = col

    for row in range(len(txt1)+1):
        lev_mat[row][0] = row

    for row in range(1,len(txt1)+1):
        for col in range(1,len(txt2)+1):
            if txt1[row-1] == txt2[col-1]:
                cost = 0
            else:
                cost = 1

            lev_mat[row][col] = min(lev_mat[row - 1][col] + 1, lev_mat[row][col - 1] + 1, lev_mat[row -  1][col - 1] + cost)

    return lev_mat[-1][-1]