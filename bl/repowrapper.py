# -*- coding: utf-8 -*-

# For array operations
import numpy as np

# For xml parsing
import xml.etree.ElementTree as ET
from xml.sax.saxutils import unescape

# For Git operations
from git import Repo

# Utilities
import logging
import os
import re
from typing import *

# This project
import utils

class Bug:
	def __init__(self, bug_element):
		self.bug_element = bug_element
		self.summary = unescape(bug_element.find('./buginformation/summary').text)
		self.description = unescape(bug_element.find('./buginformation/description').text or '')
		self.open_date = unescape(bug_element.attrib['opendate'])

	def get_fixed_files(self, modified_only=False, ignore_test=False, regularize_java_path=False) -> List[str]:
		'''Get a list of fixed files of a bug'''
		def inner() -> Iterator[str]:
			if modified_only:
				xpath = "./fixedFiles/file[@type='M']"
			else:
				xpath = './fixedFiles/file'
			for fixed_file in self.bug_element.findall(xpath):
				if not ignore_test or 'test' not in fixed_file.text:
					if regularize_java_path:
						yield utils.regularize_java_path(fixed_file.text)
					else:
						yield fixed_file.text
		return list({x: None for x in inner()})  # Use dict comprehension instead of set to preserve insertion order

	def get_embedding(self, bc):
		'''Get the embedding of bug, according to the bug summary and description'''
		tokens = utils.tokenize_code(self.summary + ' ||| ' + self.description)
		if logging.root.isEnabledFor(logging.DEBUG): 
			embedding, encoded_tokens = bc.encode(tokens, show_tokens=True)
			logging.info('%s', encoded_tokens)
		else:
			embedding = bc.encode(tokens)
		return embedding

class RepoWrapper:
	def __init__(self, project_root):
		# Constants
		self.project_root = project_root
		self.bug_file_path = os.path.join(project_root, 'bugrepo/repository.xml')
		self.repo_path = os.path.join(project_root, 'gitrepo')
		self.embeddings_path = os.path.join(project_root, 'embeddings')

		# Objects
		self.repo = Repo(self.repo_path)

	def get_bugs(self) -> Iterator[Bug]:
		'''Iterate through bugs in the repository'''
		return (Bug(bug_element) for bug_element in ET.parse(self.bug_file_path).getroot())

	def get_commit_before(self, time, branch='master') -> str:
		return next(self.repo.iter_commits(branch, before=time, max_count=1)).hexsha

	def git_reset(self, commit) -> None:
		'''Reset the underlying git repository to a certain commit'''
		self.repo.git.reset('--hard', commit)
		logging.info('Reset to commit %s', commit)

	def glob(self, pattern, ignore_string=None) -> Iterator[str]:
		from pathlib import Path
		for source_file in Path(self.repo_path).glob(pattern):
			path = str(source_file.relative_to(self.repo_path))
			if not ignore_string or ignore_string not in path:
				yield path

	def get_last_commit_of_file(self, path) -> str:
		return next(self.repo.iter_commits(paths=path, max_count=1)).hexsha

	@utils.memorize
	def get_source_embedding(self, bc, source_file, last_commit_of_file):
		# Construct path of embedding data
		revision_path = os.path.join(self.embeddings_path, last_commit_of_file)
		if not os.path.exists(revision_path):
			os.mkdir(revision_path)
		embedding_data_path = os.path.join(revision_path, utils.url_encode(source_file)) + '.npy'

		if os.path.exists(embedding_data_path):  # If the embedding is already calculated before
			return np.load(embedding_data_path)
		else:  # If not calculated before
			logging.debug('Embedding not found. Calculating...')

			with open(os.path.join(self.repo_path, source_file)) as f:  # Open the source code file
				content = re.match(r'^(/\*[\s\S]+?\*/\n)?([\s\S]*)', f.read())[2]

			source_tokens = utils.tokenize_code(source_file + ' ||| ' + content)
			source_embedding = bc.encode(source_tokens)

			np.save(embedding_data_path, source_embedding)  # Save the embedding for future use
			return source_embedding
