# standard imports
import os
import ast
# third party imports
from nltk.corpus import stopwords
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import f1_score, confusion_matrix
import joblib
import numpy as np
from nltk.stem.porter import PorterStemmer
# local imports
import src.common as common

CONFIG = common.CONFIG["classifier"]

stemmer = PorterStemmer()
analyzer = CountVectorizer().build_analyzer()

def stemming_analyzer(doc):
    return (stemmer.stem(w) for w in analyzer(doc))

class Model:

    def __init__(self):
        """instantiates the Model class
        """

        self.x_all = []
        self.y_all = []

    
    def prepare_data(self, x_and_y:list, override=False):
        """arrange data into X and Y training arrays
        for the classifier to train on. This function can
        be used to add new intents to a model.

        :param intents: rows/tuples of intents from database as a list,
        the tuples must contain the following: (intentID, matches).
        The intentID must be the same as in the database.
        """
        if override:
            self.x_all = []
            self.y_all = []


        for intentID, matches in x_and_y:
            matches = ' '.join(matches)
            try: # if the intentID is already in the list, then concatenate new matches to existing ones
                intent_idx = self.y_all.index(intentID)
                self.x_all[intent_idx] = self.x_all[intent_idx] + " " + matches
            except ValueError: # if intent not in list yet then 
                self.x_all.append(matches)
                self.y_all.append(intentID)

    def train_and_test(self):
        """train and test the classifier model
        using the prepared labels and data. This step
        must be performed after prepare_data() has
        been invoked.

        :param filepath: saves the model to the specified 
        filepath as a .joblib file
        """

        self.tfidf_vectorizer = TfidfVectorizer(stop_words=stopwords.words('english'), analyzer=stemming_analyzer)
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.x_all)

    def predict(self, user_input:str):
        """use the saved classifier model to
        predict the label based on input

        :param user_input: input on which the classifier
        will use to predict the label
        :return: a tuple containing the predicted label,
        confidence level and other possible labels in stated order.
        """

        user_input = [user_input]
        user_input_tfidf = self.tfidf_vectorizer.transform(user_input)
        similarities = cosine_similarity(user_input_tfidf, self.tfidf_matrix)
        possible_idx = list(similarities.argsort()[0])
        similarities_sorted = list(np.sort(similarities)[0])
        idx_n_sims = list(zip(possible_idx, similarities_sorted))
        possible_intents = [(self.y_all[idx], sim) for idx, sim in idx_n_sims][::-1]

        return possible_intents