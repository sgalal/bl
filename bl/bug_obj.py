# -*- coding: utf-8 -*-

from datetime import datetime
import json
import logging
from types import SimpleNamespace
import os
import re
from xml.sax.saxutils import unescape

from config import PROJECT_ROOT, TEXT_CHUNK_SIZE
import utils

def trim_full_path(s):
	'''
	>>> trim_full_path('spring-rabbit/src/main/java/org/springframework/amqp/rabbit/listener/BlockingQueueConsumer.java')
	'org.springframework.amqp.rabbit.listener.BlockingQueueConsumer.java'
	'''
	return re.sub(r'^.+?/java/', '', s, flags=re.MULTILINE).replace('/', '.')

def filter_existed_files(repo, fixed_files, commit='master') -> set:
	'''Check a file path represents a valid file in the underlying Git repository, filter out the valid files'''
	all_source_files_in_commit = list(utils.list_all_source_files(repo, commit=commit))
	def inner():
		for file_object in fixed_files:
			for source_file in all_source_files_in_commit:
				if trim_full_path(source_file.path) == file_object.text:
					is_not_empty = bool(utils.get_formatted_source_file_from_sha(repo, source_file.hexsha).rstrip())  # Check the file is not empty
					if is_not_empty:
						yield source_file.hexsha, source_file.path
	return set(inner())

def get_commit_before(repo, time, branch='master'):
	'''Get the Git commit before a specific date'''
	return next(repo.iter_commits(branch, before=time, max_count=1))

def make_bug(repo, bug_element):
	bug = SimpleNamespace()

	# Ensure the bug is fixed (not a duplicate bug report)
	is_fixed = bug_element.attrib.get('resolution') in ('Fixed', 'Complete')
	if not is_fixed:
		logging.debug('Bug is not fixed')
		return

	bug.id = unescape(bug_element.attrib['id'])
	summary = unescape(bug_element.find('./buginformation/summary').text)
	description = unescape(bug_element.find('./buginformation/description').text or '')
	bug.text = ' '.join(utils.format_source_file(summary + '. ' + description).split()[:TEXT_CHUNK_SIZE])

	bug.open_date = unescape(bug_element.attrib.get('opendate'))
	bug.fix_date = unescape(bug_element.attrib.get('fixdate'))
	if not (bug.open_date and bug.fix_date):
		logging.debug('Bug without date')
		return

	# Ensure the open date is earlier than the fix date
	open_date_obj = datetime.strptime(bug.open_date, '%Y-%m-%d %H:%M:%S')
	fix_date_obj = datetime.strptime(bug.fix_date, '%Y-%m-%d %H:%M:%S')
	is_valid_time = fix_date_obj > open_date_obj
	if not is_valid_time:
		logging.debug('Bug time is not valid')
		return

	fixed_files = bug_element.findall("./fixedFiles/file")

	bug.bug_open_sha = get_commit_before(repo, bug.open_date).hexsha
	bug.bug_fix_sha = get_commit_before(repo, bug.fix_date).hexsha

	existed_fixed_files_in_open_sha = filter_existed_files(repo, fixed_files, commit=bug.bug_open_sha)

	bug.fixed_files = list(existed_fixed_files_in_open_sha)

	# No fixed files found
	if not bug.fixed_files:
		logging.debug('Bug has no valid fixed file')
		return

	return bug

def load_bug_data():
	'''Load bug data from file'''
	bug_data_path = os.path.join(PROJECT_ROOT, 'bugs.json')
	with open(bug_data_path, 'r') as f:
		return [SimpleNamespace(**bug) for bug in json.load(f)]
