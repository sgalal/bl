#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Prepare training

# For xml parsing
import xml.etree.ElementTree as ET
from xml.sax.saxutils import unescape

# For Git operations
from git import Repo

# Utilities
import git
import binascii
import logging
import os
import random
import sqlite3
import sys
import traceback
import utils
import io

# This project
from config import PROJECT_ROOT, TEXT_CHUNK_SIZE
from repowrapper import RepoWrapper

from bug_obj import load_bug_data



here = os.path.dirname(os.path.abspath(__file__))
random.seed(42)

conn = sqlite3.connect(os.path.join(here, '../data.sqlite3'))
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS bugs
( id INTEGER PRIMARY KEY
, bug_description TEXT NOT NULL
);''')

cur.execute('''
CREATE TABLE IF NOT EXISTS file_segments
( id INTEGER PRIMARY KEY
, bug_id INTEGER NOT NULL REFERENCES bugs(id)
, token_group TEXT NOT NULL
, label TEXT NOT NULL
);''')

def finalize():
	cur.close()
	conn.commit()
	conn.execute('VACUUM')
	conn.close()

def sanitize_patch(patch):
	'''Sanitize the output of git diff to keep only the removed part ans its context'''
	if not patch:  # The file is actually not modified
		return patch
	def inner():
		with io.StringIO(patch) as f:
			for _ in range(5):
				next(f)  # Skip patch header
			for line in f:
				if line and line[0] in '- ':  # The line is a removed line or its context
					yield line[1:]
	return ''.join(inner())

def get_patch_text_of_file(repo, sha_old, sha_new, file_path) -> str:
	patch = repo.git.diff(sha_old, sha_new, '--', file_path)
	return utils.format_source_file(sanitize_patch(patch))

def get_blob_by_sha(repo, hexsha):
	return git.objects.blob.Blob(repo, binascii.a2b_hex(hexsha))

def main():
	git_repo_path = os.path.join(PROJECT_ROOT, 'gitrepo')
	repo = Repo(git_repo_path)

	for bug_object in load_bug_data():
		cur.execute('INSERT INTO bugs VALUES (?, ?)', (None, bug_object.text))
		bug_id = cur.lastrowid

		# Positive examples
		for fixed_file_sha, fixed_file_path in bug_object.fixed_files:
			fixed_file_object = get_blob_by_sha(repo, fixed_file_sha)
			patch = get_patch_text_of_file(repo, bug_object.bug_open_sha, bug_object.bug_fix_sha, fixed_file_path)
			if patch:
				cur.execute('INSERT INTO file_segments VALUES (?, ?, ?, ?)', (None, bug_id, patch, '1'))

		# Negative examples
		#choice_count = min(len(source_files), 8)
		#unrelated_files = [source_file for source_file in source_files for fixed_file in fixed_files if not source_file.endswith(fixed_file)]
		#chosen_unrelated_files = random.sample(unrelated_files, choice_count)
		#for unrelated_file in chosen_unrelated_files:
		#	token_groups = rw.get_token_groups_of_file(unrelated_file, chunk=True)
		#	for token_group in token_groups:
		#		cur.execute('INSERT INTO file_segments VALUES (?, ?, ?, ?)', (None, bug_id, token_group, '0'))

if __name__ == '__main__':
	try:
		main()
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
	finally:
		finalize()
