#!/usr/bin/python
#-*- coding: utf-8 -*-
# File: japanese_examples.py
# Description: Looks for example sentences in the Tanaka Corpus for the current card's expression.
#
# Authors: Andreas Klauer, Guaillaume Viry, Johan de Jong
# License: GPLv2

# --- initialize kanji database ---
from aqt import mw
from aqt.qt import *

import os
import codecs
import cPickle
import random
import re
from operator import itemgetter


# ************************************************
#                User Options                    *
# ************************************************

# Amount of examples to show or add:
MAX = 20          # Amount to temporarily show when this add-on is loaded
MAX_PERMANENT = 5 # Amount to add permanently to the Examples field

# Only try lookups if the note's model name contains (case insensitive):
NOTE_TRIGGER = "example_sentences"

# Source and destination fields (edit if the names if your fields are different)
# These field names are case sensitive
SOURCE_FIELDS = ["Expression", "kanji-vocab"]
DEST_FIELD = "Examples"

# Prefer shorter sentences by weighting?
WEIGHTED_SAMPLE = True

# Automatically fill the Examples field when adding notes?
LOOKUP_ON_ADD = True


# ************************************************
#                Global Variables                *
# ************************************************

fname = os.path.join(mw.pm.addonFolder(), "japanese_examples.utf")
file_pickle = os.path.join(mw.pm.addonFolder(), "japanese_examples.pickle")
f = codecs.open(fname, 'r', 'utf8')
content = f.readlines()
f.close()

dictionaries = ({},{})


# ************************************************
#              Lookup functions                  *
# ************************************************

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
        linelength = len(content[2*i][3:].split("#ID=")[0])
        for word in words:
            # Choose the appropriate dictionary; priority (0) or normal (1)
            if word.endswith("~"):
                dictionary = dictionaries[0]
                word = word[:-1]
            else:
                dictionary = dictionaries[1]

            if word in dictionary and not word.isdigit():
                dictionary[word].append((2*i,linelength))
            elif not word.isdigit():
                dictionary[word]=[]
                dictionary[word].append((2*i,linelength))

    # Sort all the entries based on their length
    for dictionary in dictionaries:
        for d in dictionary:
            dictionary[d] = sorted(dictionary[d], key=itemgetter(1))


class Node:
    pass


def weighted_sample(somelist, n):
    # TODO: See if http://stackoverflow.com/questions/2140787/select-random-k-elements-from-a-list-whose-elements-have-weights is faster for some practical use-cases.
    # This method is O(n²), but is straightforward and simple.

    # Magic numbers:
    minlength = 25
    maxlength = 70
    power = 3

    #
    l = []   # List containing nodes with their (constantly) updated weights
    ret = [] # Array of return values
    tw = 0.0 # Total weight

    for a,b in somelist:
        bold = b
        b = max(b,minlength)
        b = min(b,maxlength)
        b = b - minlength
        b = maxlength - minlength - b + 1
        b = b**power
        z = Node()
        z.w = b
        z.v = a
        tw += b
        l.append(z)

    for j in range(n):
        g = tw * random.random()
        for z in l:
            if g < z.w:
                ret.append(z.v)
                tw -= z.w
                z.w = 0.0
                break
            else:
                g -= z.w

    return ret


def find_examples(expression, maxitems):
    examples = []

    for dictionary in dictionaries:
        if expression in dictionary:
            index = dictionary[expression]
            if WEIGHTED_SAMPLE:
                index = weighted_sample(index, min(len(index),maxitems))
            else:
                index = random.sample(index, min(len(index),maxitems))
                index = [a for a,b in index]

            maxitems -= len(index)
            for j in index:
                example = content[j].split("#ID=")[0][3:]
                if dictionary == dictionaries[0]:
                    example = example + " {CHECKED}"
                example = example.replace(expression,'<FONT COLOR="#ff0000">%s</FONT>' %expression)
                color_example = content[j+1]
                regexp = "(?:\(*%s\)*)(?:\([^\s]+?\))*(?:\[\d+\])*\{(.+?)\}" %expression
                match = re.compile("%s" %regexp).search(color_example)
                regexp_reading = "(?:\s([^\s]*?))(?:\(%s\))" % expression
                match_reading = re.search(regexp_reading, color_example)
                if match:
                    expression_bis = match.group(1)
                    example = example.replace(expression_bis,'<FONT COLOR="#ff0000">%s</FONT>' %expression_bis)
                elif match_reading:
                    expression_bis = match_reading.group(1)
                    example = example.replace(expression_bis,'<FONT COLOR="#ff0000">%s</FONT>' %expression_bis) 
                else:
                    example = example.replace(expression,'<FONT COLOR="#ff0000">%s</FONT>' %expression)
                examples.append("%s<br>%s<br><br>" % tuple(example.split('\t')))
        else:
            match = re.search(u"(.*?)[／/]", expression)
            if match:
                res = find_examples(match.group(1), maxitems)
                maxitems -= len(res)
                examples.extend(res)

            match = re.search(u"(.*?)[(（](.+?)[)）]", expression)
            if match:
                if match.group(1).strip():
                    res = find_examples("%s%s" % (match.group(1), match.group(2)), maxitems)
                    maxitems -= len(res)
                    examples.extend(res)

    return examples


def find_examples_multiple(n, maxitems, modelname=""):
    if not modelname:
        modelname = n.model()['name'].lower()

    if NOTE_TRIGGER.lower() not in modelname or DEST_FIELD not in n:
        return False

    lookup_fields = [fld for fld in SOURCE_FIELDS if fld in n]

    if not lookup_fields:
        return False

    # Find example sentences
    examples = []
    for fld in lookup_fields:
        if not mw.col.media.strip(n[fld]).strip():
            continue
        maxitems = maxitems - len(examples)
        res = find_examples(n[fld], maxitems)
        examples.extend(res)

    return "".join(examples)


# ************************************************
#                  Interface                     *
# ************************************************

def setupBrowserMenu(browser):
    """ Add menu entry to browser window """
    a = QAction("Bulk-add Examples", browser)
    browser.connect(a, SIGNAL("triggered()"), lambda e=browser: onRegenerate(e))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)

def onRegenerate(browser):
    add_examples_bulk(browser.selectedNotes())


# ************************************************
#              Hooked functions                  *
# ************************************************

def add_examples_bulk(nids):
    mw.checkpoint("Bulk-add Examples")
    mw.progress.start()
    for nid in nids:
        note = mw.col.getNote(nid)

        # Find example sentences
        examples = find_examples_multiple(note, MAX_PERMANENT)

        if not examples:
            continue

        note[DEST_FIELD] = examples
        note.flush()
    mw.progress.finish()
    mw.reset()


def add_examples_temporarily(fields, model, data, collection):
    examples = find_examples_multiple(fields, MAX, modelname=model['name'].lower())

    if not examples:
        return fields

    fields[DEST_FIELD] = examples
    return fields


def add_examples_focusLost(flag, n, fidx):
    # get idx for all lookup fields
    lookupIdx = []
    for f in SOURCE_FIELDS:
        for c, name in enumerate(mw.col.models.fieldNames(n.model())):
            if name == f:
                lookupIdx.append(c)

    # event coming from src field?
    if fidx not in lookupIdx:
        return flag

    examples = find_examples_multiple(n, MAX_PERMANENT)

    if not examples:
        return flag

    # return if destination field is already filled
    if n[DEST_FIELD]:
        return flag

    # update field
    n[DEST_FIELD] = examples

    return True


# ************************************************
#                    Main                        *
# ************************************************

# Load or generate the dictionaries
if  (os.path.exists(file_pickle) and
    os.stat(file_pickle).st_mtime > os.stat(fname).st_mtime):
    f = open(file_pickle, 'rb')
    dictionaries = cPickle.load(f)
    f.close()
else:
    build_dico()
    f = open(file_pickle, 'wb')
    cPickle.dump(dictionaries, f, cPickle.HIGHEST_PROTOCOL)
    f.close()


# Hooks:
from anki.hooks import addHook

addHook("mungeFields", add_examples_temporarily)

if LOOKUP_ON_ADD:
    addHook('editFocusLost', add_examples_focusLost)

addHook("browser.setupMenus", setupBrowserMenu) # Bulk add

