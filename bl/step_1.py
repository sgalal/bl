#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Initialize bugs

from git import Repo
import json
import os
import xml.etree.ElementTree as ET

import bug_obj
from config import PROJECT_ROOT

def calculate_bug_data(repo):
	bug_file_path = os.path.join(PROJECT_ROOT, 'bugrepo', 'repository.xml')
	bug_elements = ET.parse(bug_file_path).getroot().findall('./bug')
	for bug_element in bug_elements:
		bug_object = bug_obj.make_bug(repo, bug_element)
		if bug_object is not None:
			yield bug_object

def store_bug_data(bugs):
	'''Store bug data to file'''
	bug_data_path = os.path.join(PROJECT_ROOT, 'bugs.json')
	with open(bug_data_path, 'w') as f:
		json.dump([vars(bug) for bug in bugs], f, ensure_ascii=False)

if __name__ == "__main__":
	git_repo_path = os.path.join(PROJECT_ROOT, 'gitrepo')
	repo = Repo(git_repo_path)
	bugs = calculate_bug_data(repo)
	store_bug_data(bugs)
