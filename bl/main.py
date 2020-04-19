#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# For bert service
from bert_serving.client import BertClient
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Utilities
from heapq import nlargest
import logging
import os
import sys
import traceback

# This project
from config import BERT_IP, BERT_PORT, BERT_PORT_OUT, PROJECT_ROOT, TOP_N
from repowrapper import RepoWrapper
import utils

logging.basicConfig(level=logging.INFO)
logging.info('Configuration loaded')

def calculate_similarity(bc, rw, source_file, bug_embedding):
	'''Calculate the similarity of a file and a given bug embedding'''
	last_commit_of_file = rw.get_last_commit_of_file(source_file)
	source_embedding = rw.get_source_embedding(bc, source_file, last_commit_of_file)
	similarities = cosine_similarity(bug_embedding, source_embedding)
	maximum_similarity = np.amax(similarities)  # Use the maximum value as the final similarity
	logging.debug('Similarity %f with file %s', maximum_similarity, source_file)
	return maximum_similarity, source_file

def main(bc):
	count = 0
	correct_count = 0
	rw = RepoWrapper(PROJECT_ROOT)
	for bug in rw.get_bugs():
		fixed_files = bug.get_fixed_files(modified_only=True, ignore_test=True, regularize_java_path=True)
		if fixed_files:
			bug_embedding = bug.get_embedding(bc)
			bug_commit = rw.get_commit_before(bug.open_date)
			rw.git_reset(bug_commit)

			similarities_of_files = (calculate_similarity(bc, rw, source_file, bug_embedding) for source_file in rw.glob('**/*.java', ignore_string='test'))

			predicted_files = [source_file for _, source_file in nlargest(TOP_N, similarities_of_files)]
			logging.info('Predicted files:\n%s', '\n'.join(predicted_files))
			logging.info('Fixed files:\n%s', '\n'.join(fixed_files))

			is_correct = any(predicted_file.endswith(fixed_file) for predicted_file in predicted_files for fixed_file in fixed_files)
			count += 1
			correct_count += is_correct
			logging.info('Total %d, correct %d, correct rate %.1f%%', count, correct_count, correct_count / count * 100)

if __name__ == '__main__':
	with BertClient(ip=BERT_IP, port=BERT_PORT, port_out=BERT_PORT_OUT, show_server_config=logging.root.isEnabledFor(logging.DEBUG)) as bc:
		logging.info('Connected to BERT server')
		try:
			main(bc)
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
		finally:
			logging.info('Closing the BERT server connection')
