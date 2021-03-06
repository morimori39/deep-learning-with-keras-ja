# -*- coding: utf-8 -*-
from __future__ import print_function
import operator

import nltk
import numpy as np
from keras.callbacks import TensorBoard
from keras.layers import Dense, Dropout, Activation
from keras.models import Sequential
from keras.preprocessing.text import Tokenizer, one_hot
from sklearn.model_selection import train_test_split
from sklearn.metrics.pairwise import cosine_distances
from sklearn.preprocessing import OneHotEncoder
import codecs

np.random.seed(42)

LOG_DIR = './logs'
BATCH_SIZE = 128
NUM_EPOCHS = 20

with codecs.open("./data/alice_in_wonderland.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if len(line) != 0]

try:
    sents = nltk.sent_tokenize(" ".join(lines))
except LookupError:
    print("Englisth tokenize does not downloaded. So download it.")
    nltk.download("punkt")
    sents = nltk.sent_tokenize(" ".join(lines))


tokenizer = Tokenizer(5000)  # use top 5000 words only
tokens = tokenizer.fit_on_texts(sents)
vocab_size = len(tokenizer.word_index) + 1

w_lefts, w_centers, w_rights = [], [], []
for sent in sents:
    embedding = one_hot(sent, vocab_size)
    triples = list(nltk.trigrams(embedding))
    w_lefts.extend([x[0] for x in triples])
    w_centers.extend([x[1] for x in triples])
    w_rights.extend([x[2] for x in triples])

ohe = OneHotEncoder(n_values=vocab_size)
Xleft = ohe.fit_transform(np.array(w_lefts).reshape(-1, 1)).todense()
Xright = ohe.fit_transform(np.array(w_rights).reshape(-1, 1)).todense()
X = (Xleft + Xright) / 2.0
Y = ohe.fit_transform(np.array(w_centers).reshape(-1, 1)).todense()
Xtrain, Xtest, Ytrain, Ytest = train_test_split(X, Y, test_size=0.3,
                                                random_state=42)
print(Xtrain.shape, Xtest.shape, Ytrain.shape, Ytest.shape)

model = Sequential()
model.add(Dense(300, input_shape=(Xtrain.shape[1],)))
model.add(Activation("relu"))
model.add(Dropout(0.5))
model.add(Dense(Ytrain.shape[1]))
model.add(Activation("softmax"))

model.compile(optimizer="rmsprop", loss="categorical_crossentropy", 
              metrics=["accuracy"])
history = model.fit(Xtrain, Ytrain, batch_size=BATCH_SIZE, 
                    epochs=NUM_EPOCHS, verbose=1,
                    callbacks=[TensorBoard(LOG_DIR)],
                    validation_data=(Xtest, Ytest))

# evaluate model
score = model.evaluate(Xtest, Ytest, verbose=1)
print("Test score: {:.3f}, accuracy: {:.3f}".format(score[0], score[1]))

# using the word2vec model
word2idx = tokenizer.word_index
idx2word = {v: k for k, v in word2idx.items()}

# retrieve the weights from the first dense layer. This will convert
# the input vector from a one-hot sum of two words to a dense 300 
# dimensional representation
W, b = model.layers[0].get_weights()

idx2emb = {}    
for word in word2idx.keys():
    wid = word2idx[word]
    vec_in = ohe.fit_transform(np.array(wid)).todense()
    vec_emb = np.dot(vec_in, W)
    idx2emb[wid] = vec_emb

for word in ["stupid", "alice", "succeeded"]:
    wid = word2idx[word]
    source_emb = idx2emb[wid]
    distances = []
    for i in range(1, vocab_size):
        if i == wid:
            continue
        target_emb = idx2emb[i]
        distances.append(((wid, i), 
                         cosine_distances(source_emb, target_emb)))
    sorted_distances = sorted(distances, key=operator.itemgetter(1))[0:10]
    predictions = [idx2word[x[0][1]] for x in sorted_distances]
    print("{:s} => {:s}".format(word, ", ".join(predictions)))
