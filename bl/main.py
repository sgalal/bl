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
from heapq import nlargest
import logging
import os
import sys
import traceback

# This project
from config import CHUNK_SIZE, BERT_PORT, BERT_PORT_OUT, PROJECT_ROOT, TOP_N
from utils import chunks, glob, memoize, regularize_java_path, split_camel_case, tokenize_code, url_encode

logging.basicConfig(level=logging.INFO)
logging.info('Configuration loaded')

# Configurations

bug_file_path = os.path.join(PROJECT_ROOT, 'bugrepo/repository.xml')
repo_path = os.path.join(PROJECT_ROOT, 'gitrepo')
embeddings_path = os.path.join(PROJECT_ROOT, 'embeddings')

if not os.path.exists(embeddings_path):
	os.mkdir(embeddings_path)

repo = Repo(repo_path)

bc = BertClient(port=BERT_PORT, port_out=BERT_PORT_OUT)
logging.info('Connected to BERT server')

def finalize():
	bc.close()
	logging.info('Closed the BERT server connection')

def get_last_revision_of_file(repo, path):
	return next(repo.iter_commits(paths=path, max_count=1)).hexsha

@memoize
def get_source_embedding(source_file_relpath, last_revision_of_file):
	revision_path = os.path.join(embeddings_path, last_revision_of_file)
	if not os.path.exists(revision_path):
		os.mkdir(revision_path)
	embedding_data_path = os.path.join(revision_path, url_encode(source_file_relpath)) + '.npy'

	if os.path.exists(embedding_data_path):  # If the embedding is already calculated before
		return np.load(embedding_data_path)
	else:  # If not calculated before
		logging.debug('Embedding not found. Calculating...')

		with open(os.path.join(repo_path, source_file_relpath)) as f:  # Open the source code file
			content = f.read()

		source_tokens = tokenize_code(source_file_relpath + ' ' + content)
		source_token_groups = chunks(source_tokens, CHUNK_SIZE)
		source_embedding = bc.encode(source_token_groups, is_tokenized=True)

		np.save(embedding_data_path, source_embedding)  # Save the embedding for future use
		return source_embedding

def main():
	count = 0
	correct_count = 0

	for i, bug in enumerate(ET.parse(bug_file_path).getroot()):  # For every bug in the repository
		# Get all fixed files with type M (modify, instead of add or delete)
		fixed_files = bug.findall("./fixedFiles/file[@type='M']")
		# Get the text field (i.e. file name) of the files
		fixed_files = (fixed_file.text for fixed_file in fixed_files)
		# Ignore modification of test files
		fixed_files = [fixed_file for fixed_file in fixed_files if 'test' not in fixed_file]

		fixed_files_count = len(fixed_files)

		if fixed_files:  # If the bug is fixed by modifying some files
			summary = unescape(bug.find('./buginformation/summary').text)  # Bug title
			description = unescape(bug.find('./buginformation/description').text or '')  # Bug description
			bug_opendate = unescape(bug.attrib['opendate'])
			bug_commit = get_commit_before_time(repo, bug_opendate)  # Commit that the bug was reported

			bug_tokens = tokenize_code(summary + ' ' + description)
			bug_token_groups = chunks(bug_tokens, CHUNK_SIZE)
			bug_embedding = bc.encode(bug_token_groups, is_tokenized=True)

			repo.git.reset('--hard', bug_commit)  # Switch to the version that the bug is reported
			logging.info('Checkout commit %s', bug_commit)

			res = []
			# For every source code in the current version (ignoring test files)
			for source_file_relpath in glob(repo_path, '**/*.java', ignore_string='test'):
				last_revision_of_file = get_last_revision_of_file(repo, source_file_relpath)
				source_embedding = get_source_embedding(source_file_relpath, last_revision_of_file)
				similarities = cosine_similarity(bug_embedding, source_embedding)
				maximum_similarity = np.amax(similarities)  # Use the maximum value as the final similarity
				logging.debug('Similarity %f with file %s', maximum_similarity, source_file_relpath)
				res.append((maximum_similarity, source_file_relpath))

			predicted_files = [source_file_relpath for _, source_file_relpath in nlargest(max(TOP_N, fixed_files_count), res)]
			logging.info('Predicted files:\n%s', '\n'.join(predicted_files))

			fixed_files = [regularize_java_path(fixed_file) for fixed_file in fixed_files]
			logging.info('Fixed files:\n%s', '\n'.join(fixed_files))

			for fixed_file in fixed_files:
				is_correct = any(predicted_file.endswith(fixed_file) for predicted_file in predicted_files)
				count += 1
				correct_count += is_correct

			logging.info('Total %d, correct %d, correct rate %.1f%%', count, correct_count, correct_count / count * 100)

if __name__ == '__main__':
	try:
		main()
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
	finally:
		finalize()
