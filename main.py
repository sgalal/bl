#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# For bert service
from bert_serving.client import BertClient
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# For parsing xml
import xml.etree.ElementTree as ET
from xml.sax.saxutils import unescape

# For Git operations
from git import Repo

# Utilities
import logging
import os
from pathlib import Path
import re

# Configurations

logging.basicConfig(level=logging.INFO)

here = '/home/ayaka/Hub/Bench4BL/data/Wildfly/WFARQ'
bug_file_path = os.path.join(here, 'bugrepo/repository.xml')
repo_path = os.path.join(here, 'gitrepo')

chunk_size = 25  # For embeddings

# Constants

JAVA_KEYWORDS = ["abstract", "continue", "for", "new", "switch", "assert", "default", "goto", "package", "synchronized", "boolean", "do", "if", "private", "this", "break", "double", "implements", "protected", "throw", "byte", "else", "import", "public", "throws", "case", "enum", "instanceof", "return", "transient", "catch", "extends", "int", "short", "try", "char", "final", "interface", "static", "void", "class", "finally", "long", "strictfp", "volatile", "const", "float", "native", "super", "while", "org", "eclipse", "swt", "string", "main", "args", "null", "this", "extends", "true", "false"]

# Functions

def chunks(lst, n):
	"""Split a list into n-sized chunks, without padding."""
	return [lst[i:i + n] for i in range(0, len(lst), n)]

# =============== TODO FIXME: IMPROVE THE CODE BELOW =============== #

def split_camel_case(s):
	'''
	>>> list(split_camel_case('AaaBgsHhTTPRequest'))
	['aaa', 'bgs', 'hh', 'ttp', 'request']
	'''
	if s:
		if s[0].islower():
			s = s[0].upper() + s[1:]
		for x in re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))', s):
			yield x.lower()

def tokenize_code(s):
	res = []
	for x in re.split(r'[^a-zA-Z\'.,]+', s):
		if x and x not in JAVA_KEYWORDS:
			for y in split_camel_case(x):
				res.append(y)
	return res

# =============== TODO FIXME: IMPROVE THE CODE ABOVE =============== #

repo = Repo(repo_path)
bc = BertClient()

for i, bug in enumerate(ET.parse(bug_file_path).getroot()):  # For every bug in the repository
	if i < 1 or i > 2:
		continue  # Skip several bugs for testing

	fixed_files = bug.findall("./fixedFiles/file[@type='M']")
	if fixed_files:  # If the bug is fixed by modifying files (instead of adding or deleting)
		res = []

		summary = unescape(bug.find('./buginformation/summary').text)
		description = unescape(bug.find('./buginformation/description').text)
		bug_version = unescape(bug.find('./buginformation/version').text)

		bug_tokens = tokenize_code(summary + ' ' + description)
		bug_token_groups = chunks(bug_tokens, chunk_size)
		bug_token_id_groups = bc.encode(bug_token_groups, is_tokenized=True)

		repo.head.reference = repo.tags[bug_version].commit  # Switch to the version that the bug is reported
		logging.info('Switched to tag %s', bug_version)
		for source_file in Path(repo_path).glob('**/*.java'):  # For every source code in the current version
			source_file_relpath = str(source_file.relative_to(repo_path))
			if 'test' not in source_file_relpath:
				with source_file.open() as f:  # Open the source code
					content = f.read()
					source_tokens = tokenize_code(source_file_relpath + ' ' + content)
					source_token_groups = chunks(source_tokens, chunk_size)
					source_token_id_groups = bc.encode(source_token_groups, is_tokenized=True)
					similarities = cosine_similarity(bug_token_id_groups, source_token_id_groups)
					maximum_similarity = np.amax(similarities)
					logging.info('Similarity %f with file %s', maximum_similarity, source_file_relpath)
					res.append((maximum_similarity, source_file_relpath))
		print('Prediction:', sorted(res, reverse=True)[:10])
		print('Fixed files:', [fixed_file.text for fixed_file in fixed_files])
