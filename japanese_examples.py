#!/usr/bin/python
#-*- coding: utf-8 -*-
# File: japanese_examples.py
# Description: Looks for example sentences in the Tanaka Corpus for the current card's expression.
# This addon was first based on Andreas Klauer's "kanji_info" plugin, and is a modified version
# of Guillaume VIRY's example sentences plugin for Anki 1.
#
# Author: Guillaume VIRY
# License:     GPL

# --- initialize kanji database ---
from aqt import mw
import os
import codecs
import cPickle
import random
import re

# file containing the Tanaka corpus sentences
file = os.path.join(mw.pm.addonFolder(), "japanese_examples.utf")
file_pickle = os.path.join(mw.pm.addonFolder(), "japanese_examples.pickle")
f = codecs.open(file, 'r', 'utf8')
content = f.readlines()
f.close()

dictionaries = ({},{})
MAX = 20

def build_dico():
    def splitter(txt):
        txt = re.compile('\s|\[|\]|\(|\{|\)|\}').split(txt)
        for i in range(0,len(txt)):
            if txt[i] == "~":
                txt[i-2] = txt[i-2] + "~"
                txt[i-1] = txt[i-1] + "~"
                txt[i] = ""
        return [x for x in txt if x]

    for i, line in enumerate(content[1::2]):
        words = set(splitter(line)[1:-1])
        for word in words:
            # Choose the appropriate dictionary; priority (0) or normal (1)
            if word.endswith("~"):
                dictionary = dictionaries[0]
                word = word[:-1]
            else:
                dictionary = dictionaries[1]

            if word in dictionary and not word.isdigit():
                dictionary[word].append(2*i)
            elif not word.isdigit():
                dictionary[word]=[]
                dictionary[word].append(2*i)

if  (os.path.exists(file_pickle) and
    os.stat(file_pickle).st_mtime > os.stat(file).st_mtime):
    f = open(file_pickle, 'rb')
    dictionaries = cPickle.load(f)
    f.close()
else:
    build_dico()
    f = open(file_pickle, 'wb')
    cPickle.dump(dictionaries, f, cPickle.HIGHEST_PROTOCOL)
    f.close()

def find_examples(expression):
    info_question = ""
    info_answer = ""
    maxitems = MAX

    examples_question = []
    examples_answer = []

    for dictionary in dictionaries:
        if expression in dictionary:
            index = dictionary[expression]
            index = random.sample(index, min(len(index),maxitems))
            maxitems -= len(index)
            for j in index:
                example = content[j].split("#ID=")[0][3:]
                if dictionary == dictionaries[0]:
                    example = example + " {CHECKED}"
                example = example.replace(expression,'<FONT COLOR="#ff0000">%s</FONT>' %expression)
                color_example = content[j+1]
                regexp = "(?:\(*%s\)*)(?:\([^\s]+?\))*(?:\[\d+\])*\{(.+?)\}" %expression
                match = re.compile("%s" %regexp).search(color_example)
                if match:
                    expression_bis = match.group(1)
                    example = example.replace(expression_bis,'<FONT COLOR="#ff0000">%s</FONT>' %expression_bis)
                else:
                    example = example.replace(expression,'<FONT COLOR="#ff0000">%s</FONT>' %expression)
                examples_question.append("<br>%s<br><br>" % example.split('\t')[0])
                examples_answer.append("<br>%s<br>%s<br>" % tuple(example.split('\t')))
        else:
            match = re.search(u"(.*?)[／/]", expression)
            if match:
                return find_examples(match.group(1))

            match = re.search(u"(.*?)[(（](.+?)[)）]", expression)
            if match:
                if match.group(1).strip():
                    return find_examples("%s%s" % (match.group(1), match.group(2)))

    info_question = "".join(examples_question)
    info_answer = "".join(examples_answer)
    return (info_question,info_answer)


def add_examples(fields, model, data, n):

    if "example_sentences" not in model['name'].lower():
        return fields

    if "Examples" not in fields or "Expression" not in fields:
        return fields

    info_question, info_answer = find_examples(fields["Expression"])

    fields["Examples"] = info_answer
    return fields


from anki.hooks import addHook

addHook("mungeFields", add_examples)

