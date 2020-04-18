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
from urllib.parse import quote

with open('config.py') as f:
	exec(f.read())
logging.info('Configuration loaded')

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
logging.info('Connected to BERT server')

def get_last_revision_of_file(repo, path):
	return next(repo.iter_commits(paths=path, max_count=1)).hexsha

def get_source_embedding(source_file, last_revision_of_file):
	source_file_relpath = str(source_file.relative_to(repo_path))
	revision_path = os.path.join(embeddings_path, last_revision_of_file)
	if not os.path.exists(revision_path):
		os.mkdir(revision_path)
	embedding_data_path = os.path.join(revision_path, quote(source_file_relpath, safe='')) + '.npy'

	if os.path.exists(embedding_data_path):  # Already calculated before
		return np.load(embedding_data_path)
	else:  # Not calculated
		logging.info('Embedding not found. Calculating...')

		with source_file.open() as f:  # Open the source code
			content = f.read()

		source_tokens = tokenize_code(source_file_relpath + ' ' + content)
		source_token_groups = chunks(source_tokens, chunk_size)
		source_embedding = bc.encode(source_token_groups, is_tokenized=True)

		np.save(embedding_data_path, source_embedding)
		return source_embedding

for i, bug in enumerate(ET.parse(bug_file_path).getroot()):  # For every bug in the repository
	if i > 1:
		continue  # Skip several bugs for testing purpose

	fixed_files = bug.findall("./fixedFiles/file[@type='M']")
	if fixed_files:  # If the bug is fixed by modifying files (instead of adding or deleting)
		res = []

		summary = unescape(bug.find('./buginformation/summary').text)
		description = unescape(bug.find('./buginformation/description').text)
		bug_version = unescape(bug.find('./buginformation/version').text)

		bug_tokens = tokenize_code(summary + ' ' + description)
		bug_token_groups = chunks(bug_tokens, chunk_size)
		bug_embedding = bc.encode(bug_token_groups, is_tokenized=True)

		repo.git.reset('--hard', bug_version)  # Switch to the version that the bug is reported
		logging.info('Switched to tag %s', bug_version)
		for source_file in Path(repo_path).glob('**/*.java'):  # For every source code in the current version
			source_file_relpath = str(source_file.relative_to(repo_path))
			if 'test' not in source_file_relpath:  # Ignore test files
				last_revision_of_file = get_last_revision_of_file(repo, source_file_relpath)
				source_embedding = get_source_embedding(source_file, last_revision_of_file)
				similarities = cosine_similarity(bug_embedding, source_embedding)
				maximum_similarity = np.amax(similarities)
				logging.info('Similarity %f with file %s', maximum_similarity, source_file_relpath)
				res.append((maximum_similarity, source_file_relpath))
		print('Prediction:')
		for maximum_similarity, source_file_relpath in sorted(res, reverse=True)[:10]:
			print(maximum_similarity, source_file_relpath)
		print('Fixed files:', [fixed_file.text for fixed_file in fixed_files])

bc.close()
logging.info('Closed the BERT server connection')
