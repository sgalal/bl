# -*- coding: utf-8 -*-

from datetime import datetime
from git import Repo
import json
import logging
import numpy as np
import os
import pickle
import re
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from xml.sax.saxutils import unescape

import utils

logging.basicConfig(level=logging.DEBUG)

def make_bug(rw, bug_element):
	bug = SimpleNamespace()

	# Ensure the bug is fixed (not a duplicate bug report)
	is_fixed = bug_element.attrib.get('resolution') in ('Fixed', 'Complete')
	if not is_fixed:
		return

	bug.id = unescape(bug_element.attrib['id'])
	summary = unescape(bug_element.find('./buginformation/summary').text)
	description = unescape(bug_element.find('./buginformation/description').text or '')
	bug.text = summary + '. ' + description

	bug.open_date = unescape(bug_element.attrib.get('opendate'))
	bug.fix_date = unescape(bug_element.attrib.get('fixdate'))
	if not (bug.open_date and bug.fix_date):
		return

	# Ensure the open date is earlier than the close date
	open_date_obj = datetime.strptime(bug.open_date, '%Y-%m-%d %H:%M:%S')
	fix_date_obj = datetime.strptime(bug.fix_date, '%Y-%m-%d %H:%M:%S')
	is_valid_time = fix_date_obj > open_date_obj
	if not is_valid_time:
		return

	fixed_files = bug_element.findall("./fixedFiles/file")

	bug.bug_open_sha = utils.get_commit_before(rw.repo, bug.open_date).hexsha

	existed_fixed_files_in_open_sha = utils.filter_existed_files(rw, fixed_files, commit=bug.bug_open_sha)

	bug.fixed_files = list(existed_fixed_files_in_open_sha)

	# No fixed files found
	if not bug.fixed_files:
		return

	return bug

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

	def calculate_bug_data(self):
		bug_elements = ET.parse(self.bug_file_path).getroot().findall('./bug')
		for bug_element in bug_elements:
			bug_object = make_bug(self, bug_element)
			if bug_object is not None:
				yield bug_object

	def load_bug_data(self):
		'''Load bug data from file'''
		if os.path.exists(self.bug_data_path):
			with open(self.bug_data_path, 'r') as f:
				return [SimpleNamespace(**bug) for bug in json.load(f)]

	def store_bug_data(self, bugs):
		'''Store bug data to file'''
		with open(self.bug_data_path, 'w') as f:
			json.dump([vars(bug) for bug in bugs], f, ensure_ascii=False)

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
			bug_objects = list(self.calculate_bug_data())
			self.store_bug_data(bug_objects)

		# Calculate bug embeddings
		bug_embeddings = self.load_bug_embeddings()
		if bug_embeddings is None:
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

		if os.path.exists(embedding_data_path):  # If the embedding is already calculated before
			return np.load(embedding_data_path)
		else:  # If not calculated before
			logging.info('Embedding not found. Calculating...')
			s = utils.get_formatted_source_file(self.repo, source_file, commit=commit) or '.'
			source_tokens = utils.get_token_groups(s)
			source_embedding = bc.encode(source_tokens)
			np.save(embedding_data_path, source_embedding)  # Save the embedding for future use
			return source_embedding
