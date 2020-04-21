#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# For xml parsing
import xml.etree.ElementTree as ET
from xml.sax.saxutils import unescape

# For Git operations
from git import Repo

# Utilities
import logging
import os
import random
import sqlite3
import sys
import traceback
import utils

# This project
from config import PROJECT_ROOT
from repowrapper import RepoWrapper

here = os.path.dirname(os.path.abspath(__file__))
random.seed(42)

conn = sqlite3.connect(os.path.join(here, '../data.sqlite3'))
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS data
( 'id' INTEGER PRIMARY KEY
, 'bug_description' TEXT NOT NULL
, 'token_group' TEXT NOT NULL
, 'label' TEXT NOT NULL
);''')

def finalize():
	cur.close()
	conn.commit()
	conn.execute('VACUUM')
	conn.close()

def main():
	rw = RepoWrapper(PROJECT_ROOT)
	rw.git_fetch()
	for i, bug in enumerate(rw.get_bugs(has_open_date=True, fixed_only=True)):
		if i == 300:
			break  # Restrict to 300 bugs

		fixed_files = bug.get_fixed_files(modified_only=True, ignore_test=True, regularize_java_path=True)
		if fixed_files:
			rw.git_reset('origin/master')
			bug_commit = rw.get_commit_before(bug.open_date)
			rw.git_reset(bug_commit)
			bug_description = bug.get_merged_description()

			# Git repo
			source_files = list(rw.glob('**/*.java', ignore_string='test'))

			# Positive examples
			fixed_files_full_path = [source_file for source_file in source_files for fixed_file in fixed_files if source_file.endswith(fixed_file)]
			for fixed_file in fixed_files_full_path:
				logging.info('Found fixed file: %s', fixed_file)
				if rw.exists_file(fixed_file):
					token_groups = rw.get_token_groups_of_file(fixed_file, chunk=True)
					for token_group in token_groups:
						cur.execute('INSERT INTO data VALUES (?, ?, ?, ?)', (None, bug_description, token_group, '1'))

			# Negative examples
			choice_count = min(len(source_files), 8)
			unrelated_files = [source_file for source_file in source_files for fixed_file in fixed_files if not source_file.endswith(fixed_file)]
			chosen_unrelated_files = random.sample(unrelated_files, choice_count)
			for unrelated_file in chosen_unrelated_files:
					token_groups = rw.get_token_groups_of_file(unrelated_file, chunk=True)
					for token_group in token_groups:
						cur.execute('INSERT INTO data VALUES (?, ?, ?, ?)', (None, bug_description, token_group, '0'))

if __name__ == '__main__':
	try:
		main()
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
	finally:
		finalize()
