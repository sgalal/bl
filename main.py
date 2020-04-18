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
import re
from urllib.parse import quote

with open('config.py') as f:
	exec(f.read())
logging.info('Configuration loaded')

# Functions

def chunks(lst, n):
	"""Split a list into n-sized chunks, without padding."""
	return [lst[i:i + n] for i in range(0, len(lst), n)]

def glob(base_path, file, ignore_string=None):
	from pathlib import Path
	if not ignore_string:
		for source_file in Path(base_path).glob(file):
			yield str(source_file.relative_to(base_path))
	else:
		for source_file in Path(base_path).glob(file):
			path = str(source_file.relative_to(base_path))
			if ignore_string not in path:
				yield path

def memoize(func):
	memo = {}
	def wrapper(*args):
		try:
			return memo[args]
		except KeyError:
			res = func(*args)
			memo[args] = res
			return res
	return wrapper

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

@memoize
def get_source_embedding(source_file_relpath, last_revision_of_file):
	revision_path = os.path.join(embeddings_path, last_revision_of_file)
	if not os.path.exists(revision_path):
		os.mkdir(revision_path)
	embedding_data_path = os.path.join(revision_path, quote(source_file_relpath, safe='')) + '.npy'

	if os.path.exists(embedding_data_path):  # The embedding is already calculated before
		return np.load(embedding_data_path)
	else:  # Not calculated before
		logging.info('Embedding not found. Calculating...')

		with open(os.path.join(repo_path, source_file_relpath)) as f:  # Open the source code file
			content = f.read()

		source_tokens = tokenize_code(source_file_relpath + ' ' + content)
		source_token_groups = chunks(source_tokens, chunk_size)
		source_embedding = bc.encode(source_token_groups, is_tokenized=True)

		np.save(embedding_data_path, source_embedding)  # Save the embedding for future use
		return source_embedding

for i, bug in enumerate(ET.parse(bug_file_path).getroot()):  # For every bug in the repository
	if i <= 5 or i > 6:
		continue  # Skip several bugs to speed up debugging

	fixed_files = bug.findall("./fixedFiles/file[@type='M']")  # Get all fixed files with type M (modify, instead of add or delete)
	fixed_files = [fixed_file.text for fixed_file in fixed_files if 'test' not in fixed_file.text]  # Ignore modification of test files
	if fixed_files:  # If the bug is fixed by modifying some files
		summary = unescape(bug.find('./buginformation/summary').text)  # Bug title
		description = unescape(bug.find('./buginformation/description').text or '')  # Bug description
		bug_version = unescape(bug.find('./buginformation/version').text)  # Version that the bug was reported

		bug_tokens = tokenize_code(summary + ' ' + description)
		bug_token_groups = chunks(bug_tokens, chunk_size)
		bug_embedding = bc.encode(bug_token_groups, is_tokenized=True)

		repo.git.reset('--hard', bug_version)  # Switch to the version that the bug is reported
		logging.info('Switched to tag %s', bug_version)

		res = []
		# For every source code in the current version (ignoring test files)
		for source_file_relpath in glob(repo_path, '**/*.java', ignore_string='test'):
			last_revision_of_file = get_last_revision_of_file(repo, source_file_relpath)
			source_embedding = get_source_embedding(source_file_relpath, last_revision_of_file)
			similarities = cosine_similarity(bug_embedding, source_embedding)
			maximum_similarity = np.amax(similarities)  # Use the maximum value as the final similarity
			logging.debug('Similarity %f with file %s', maximum_similarity, source_file_relpath)
			res.append((maximum_similarity, source_file_relpath))

		print('Prediction:')
		for maximum_similarity, source_file_relpath in sorted(res, reverse=True)[:10]:
			print(maximum_similarity, source_file_relpath)
		print('Fixed files:')
		for fixed_file in fixed_files:
			print(fixed_file)
		input('Paused...')

bc.close()
logging.info('Closed the BERT server connection')
