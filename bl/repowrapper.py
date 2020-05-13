# -*- coding: utf-8 -*-

from git import Repo
import json
import logging
import numpy as np
import os
import pickle
import re

import utils

logging.basicConfig(level=logging.DEBUG)

class RepoWrapper:
	def __init__(self, project_root):
		# Constants
		self.project_root = project_root
		self.bug_file_path = os.path.join(project_root, 'bugrepo/repository.xml')
		self.repo_path = os.path.join(project_root, 'gitrepo')

		# Embeddings and data
		self.embeddings_path = os.path.join(project_root, 'embeddings')
		self.bug_data_path = os.path.join(project_root, 'bug_data.json')
		self.bug_embeddings_path = os.path.join(project_root, 'bug_embeddings.npy')

		if not os.path.exists(self.embeddings_path):
			os.mkdir(self.embeddings_path)

		# Objects
		self.repo = Repo(self.repo_path)

		# Cache
		self.SOURCE_EMBEDDING_CACHE = {}

	def load_bug_embeddings(self):
		'''Load bug embeddings from file'''
		if os.path.exists(self.bug_embeddings_path):
			return np.load(self.bug_embeddings_path)

	def store_bug_embeddings(self, embeddings):
		'''Store bug embeddings to file'''
		np.save(self.bug_embeddings_path, embeddings)

	def list_all_bug_objects_with_embeddings(self, bc):
		# Calculate bug data
		bug_objects = self.load_bug_data()  # Return None if not cached on disk
		if bug_objects is None:
			logging.info('Bug object cache not found, calculating...')
			bug_objects = list(self.calculate_bug_data())
			self.store_bug_data(bug_objects)

		# Calculate bug embeddings
		bug_embeddings = self.load_bug_embeddings()
		if bug_embeddings is None:
			logging.info('Bug embedding cache not found, calculating...')
			bug_texts = [bug_object.text for bug_object in bug_objects]
			bug_embeddings = bc.encode(bug_texts)
			self.store_bug_embeddings(bug_embeddings)

		for bug_object, bug_embedding in zip(bug_objects, bug_embeddings):
			bug_object.embedding = bug_embedding
			yield bug_object

	def get_source_embedding(self, bc, source_file, commit='master'):
		last_commit_of_file = utils.get_last_commit_of_file(self.repo, path=source_file, commit=commit).hexsha

		# Construct path of embedding data
		revision_path = os.path.join(self.embeddings_path, last_commit_of_file)
		if not os.path.exists(revision_path):
			os.mkdir(revision_path)
		embedding_data_path = os.path.join(revision_path, utils.url_encode(source_file)) + '.npy'
		source_text_path = os.path.join(revision_path, utils.url_encode(source_file)) + '.txt'  # Only for debug purpose

		if (embedding_data_path, source_text_path) in self.SOURCE_EMBEDDING_CACHE:  # If the embedding is cached in memory
			return self.SOURCE_EMBEDDING_CACHE[embedding_data_path, source_text_path]
		if os.path.exists(embedding_data_path):  # If the embedding is already calculated before
			res = np.load(embedding_data_path)
			self.SOURCE_EMBEDDING_CACHE[embedding_data_path, source_text_path] = res
			return res
		else:  # If not calculated before
			logging.info('Embedding not found. Calculating...')
			s = utils.get_formatted_source_file(self.repo, source_file, commit=commit) or '.'
			with open(source_text_path, 'w', errors='ignore') as f:
				f.write(s)  # Only for debug purpose
			source_tokens = utils.get_token_groups(s)
			res = bc.encode(source_tokens)

			np.save(embedding_data_path, res)  # Save the embedding for future use
			self.SOURCE_EMBEDDING_CACHE[embedding_data_path, source_text_path] = res

			return res
