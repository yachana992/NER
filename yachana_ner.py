# -*- coding: utf-8 -*-
"""NER.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Ae5zbVGpJcb8PHBTrvFMpKMzlHXv6Ki-
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from collections import Counter
from sklearn.model_selection import train_test_split

data = pd.read_csv("annotatedNepaliNERDataPOS.csv")

data = data.head(5000)

# A class to retrieve the sentences from the dataset
class getsentence(object):
    
    def __init__(self, data):
        self.n_sent = 1.0
        self.data = data
        self.empty = False
        agg_func = lambda s: [(w, p, t) for w, p, t in zip(s["Word"].values.tolist(),
                                                           s["Pos"].values.tolist(),
                                                           s["Tag"].values.tolist())]
        self.grouped = self.data.groupby("Sent").apply(agg_func)
        self.sentences = [s for s in self.grouped]

getter = getsentence(data)
sentences = getter.sentences


# Defines feature set of a word
def word2features(sent, i):
    """
    Arguments:
    sent = word in a sentence
    i = index of the word in the sentence
    
    Output:
    features = dictionary of features of each word
    """
    word = sent[i][0]
    length = len(word)
    postag = sent[i][1]

    features = {
        'bias': 1.0,
        'word': word,
        'word[-3:]': word[-3:],
        'word[-2:]': word[-2:],
        'word.isdigit()': word.isdigit(),
        'postag': postag,
        'postag[:2]': postag[:2],
        'length': length,
    }
    if i > 0:
        word1 = sent[i-1][0]
        postag1 = sent[i-1][1]
        features.update({
            '-1:word1': word1,
            '-1:postag': postag1,
            '-1:postag[:2]': postag1[:2],
        })
    else:
        features['BOS'] = True

    if i < len(sent)-1:
        word1 = sent[i+1][0]
        postag1 = sent[i+1][1]
        features.update({
            '+1:word1': word1,
            '+1:postag': postag1,
            '+1:postag[:2]': postag1[:2],
        })
    else:
        features['EOS'] = True

    return features

def sent2features(sent):
    """
    Arguments:
    sent = sentence
    
    Output:
    returns a feature vector for words in a sentence
    """
    return [word2features(sent, i) for i in range(len(sent))]

def sent2labels(sent):
    """
    Arguments:
    sent = sentence
    
    Output:
    return lists of labels in the sentences
    """
    return [label for token, postag, label in sent]

#Creating the features and labels for the dataset
X = [sent2features(s) for s in sentences]
y = [sent2labels(s) for s in sentences]

X_feat = [item for sublist in X for item in sublist]
y_label = [item for sublist in y for item in sublist]

#Converting the feature arrays into feature vectors)
vec = DictVectorizer(sparse=False)
X_arr = vec.fit_transform(X_feat)
print(X_arr)

print(np.unique(y_label))

y_data, meta_data = pd.factorize(y_label)

print(y_data)

#Splitting the dataset into train and test set
X_train, X_test, y_train, y_test = train_test_split(X_arr, y_data, test_size=0.33, random_state=42)

#calculating entropy
def entropy(y):
    hist = np.bincount(y)
    ps = hist / len(y)
    return -np.sum([p * np.log2(p) for p in ps if p > 0])


class Node:

    def __init__(self, feature=None, threshold=None, left=None, right=None, *, value=None):
        self.feature = feature
        self.threshold = threshold
        self.left = left
        self.right = right
        self.value = value

    def is_leaf_node(self):
        return self.value is not None


class DecisionTree:
    
    #Initializing the class
    def __init__(self, min_samples_split=2, max_depth=100, n_feats=None):
        self.min_samples_split = min_samples_split
        self.max_depth = max_depth
        self.n_feats = n_feats
        self.root = None
   
#function to fit the model
    def fit(self, X, y):
        """
        Argument:
        X = features 
        y = labels
        """
        self.n_feats = X.shape[1] if not self.n_feats else min(self.n_feats, X.shape[1])
        self.root = self._grow_tree(X, y)

    def predict(self, X):
        return np.array([self._traverse_tree(x, self.root) for x in X])

    def _grow_tree(self, X, y, depth=0):
        n_samples, n_features = X.shape
        n_labels = len(np.unique(y))

        # stopping criteria
        if (depth >= self.max_depth
                or n_labels == 1
                or n_samples < self.min_samples_split):
            leaf_value = self._most_common_label(y)
            return Node(value=leaf_value)

        feat_idxs = np.random.choice(n_features, self.n_feats, replace=False)

        # greedily select the best split according to information gain
        best_feat, best_thresh = self._best_criteria(X, y, feat_idxs)
        
        # grow the children that result from the split
        left_idxs, right_idxs = self._split(X[:, best_feat], best_thresh)
        left = self._grow_tree(X[left_idxs, :], y[left_idxs], depth+1)
        right = self._grow_tree(X[right_idxs, :], y[right_idxs], depth+1)
        return Node(best_feat, best_thresh, left, right)

    def _best_criteria(self, X, y, feat_idxs):
        best_gain = -1
        split_idx, split_thresh = None, None
        for feat_idx in feat_idxs:
            X_column = X[:, feat_idx]
            thresholds = np.unique(X_column)
            for threshold in thresholds:
                gain = self._information_gain(y, X_column, threshold)

                if gain > best_gain:
                    best_gain = gain
                    split_idx = feat_idx
                    split_thresh = threshold

        return split_idx, split_thresh

    def _information_gain(self, y, X_column, split_thresh):
        # parent loss
        parent_entropy = entropy(y)

        # generate split
        left_idxs, right_idxs = self._split(X_column, split_thresh)

        if len(left_idxs) == 0 or len(right_idxs) == 0:
            return 0

        # compute the weighted avg. of the loss for the children
        n = len(y)
        n_l, n_r = len(left_idxs), len(right_idxs)
        e_l, e_r = entropy(y[left_idxs]), entropy(y[right_idxs])
        child_entropy = (n_l / n) * e_l + (n_r / n) * e_r

        # information gain is difference in loss before vs. after split
        ig = parent_entropy - child_entropy
        return ig

    def _split(self, X_column, split_thresh):
        left_idxs = np.argwhere(X_column <= split_thresh).flatten()
        right_idxs = np.argwhere(X_column > split_thresh).flatten()
        return left_idxs, right_idxs

    def _traverse_tree(self, x, node):
        if node.is_leaf_node():
            return node.value

        if x[node.feature] <= node.threshold:
            return self._traverse_tree(x, node.left)
        return self._traverse_tree(x, node.right)

    def _most_common_label(self, y):
        counter = Counter(y)
        most_common = counter.most_common(1)[0][0]
        return most_common

#Fitting the model
clf = DecisionTree(max_depth=10)
clf.fit(X_train,y_train)

#Predicting labels for the test set
y_pred = clf.predict(X_test)

#To calculate the accuracy of the model
def accuracy(y_true, y_pred):
    accuracy = np.sum(y_true == y_pred) / len(y_true)
    return accuracy

#Calculating accuracy of the model
acc = accuracy(y_test, y_pred)

print(acc)

print(y_pred)
