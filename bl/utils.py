# -*- coding: utf-8 -*-

import io
import logging
import re
from typing import List
from urllib.parse import quote

from config import TEXT_CHUNK_SIZE, TOP_N
import similarity

JAVA_KEYWORDS = ["abstract", "continue", "for", "new", "switch", "assert",
	"default", "goto", "package", "synchronized", "boolean", "do", "if",
	"private", "this", "break", "double", "implements", "protected",
	"throw", "byte", "else", "import", "public", "throws", "case",
	"enum", "instanceof", "return", "transient", "catch", "extends", "int",
	"short", "try", "char", "final", "interface", "static", "void", "class",
	"finally", "long", "strictfp", "volatile", "const", "float", "native",
	"super", "while", "org", "eclipse", "swt", "string", "main", "args",
	"null", "this", "extends", "true", "false",
	"map", "java", "util", "tree", "push", "iter", "io",
	"apos", "lt", "gt", "br", "li"]

def chunks(lst, chunk_size):
	"""Split a list into n-sized chunks, without padding"""
	a = [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
	# Combine the last two elements to ensure the size is never smaller than n/2
	if len(a) > 1 and len(a[-1]) < (chunk_size // 2):
		a[-2] += a[-1]
		a.pop()
	return a

def url_encode(s):
	return quote(s, safe='')

def format_source_file(s) -> str:
	'''
	Regularize JAVA code to feed to the BERT model
	>>> format_source_file('aBcDefHTTPIjkl_mnOpqR')
	'a bc def http ijkl mn opq r'
	>>> format_source_file('#import { a *= 2; return x; }')
	'# a 2 x'
	'''
	# Remove copyright header
	s = re.match(r'^(/\*[\s\S]+?\*/\n)?([\s\S]*)', s, flags=re.MULTILINE)[2]
	# Remove imports
	s = re.sub(r'^import .+\n', '', s, flags=re.MULTILINE)
	s = re.sub(r'^.+? @author .+\n', '', s, flags=re.MULTILINE)
	# Handle Java packages and class methods
	s = re.sub(r'(\S)\.(\S)', r'\1 \2', s)
	# Handle camelcases
	s = re.sub(r'(\S)_(\S)', r'\1 \2', s)
	s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
	s = re.sub(r'([A-Z])([A-Z])([a-z])', r'\1 \2\3', s)
	# Handle Java symbols
	s = re.sub(r'''[@{}+=*/%!<>&|:~^;()\[\]"]''', ' ', s)
	s = re.sub(r' [\-?] ', ' ', s)
	# Remove stopwords
	for word in JAVA_KEYWORDS:
		s = re.sub(r'\b' + word + r'\b', '', s, flags=re.IGNORECASE)
	# Remove redundant whitespaces
	s = re.sub(r'\s+', ' ', s)
	# Lower the characters since we are using the uncased BERT model
	return s.lower()

def get_token_groups(s):
	'''This is the actual tokens of file that feeds into the BERT model'''
	return [' '.join(x) for x in chunks(s.split(), chunk_size=TEXT_CHUNK_SIZE)]

def trim_full_path(s):
	'''
	>>> trim_full_path('spring-rabbit/src/main/java/org/springframework/amqp/rabbit/listener/BlockingQueueConsumer.java')
	'org.springframework.amqp.rabbit.listener.BlockingQueueConsumer.java'
	'''
	return re.sub(r'^.+?/java/', '', s, flags=re.MULTILINE).replace('/', '.')

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

def list_all_source_files(repo, commit='master', pattern='.java') -> List[str]:
	return (file for file in repo.tree(commit).traverse() if file.type == 'blob' and file.path.endswith(pattern))

def get_commit_before(repo, time, branch='master') -> str:
	'''Get the Git commit before a specific date'''
	return next(repo.iter_commits(branch, before=time, max_count=1))

def get_last_commit_of_file(repo, path, commit='master') -> str:
	'''Get the last commit of file before a specific commit'''
	return next(repo.iter_commits(commit, paths=path, max_count=1))

def calculate_top_n_rank(source_files, fixed_files):
	return any(source_file == fixed_file for source_file in source_files[:TOP_N] for fixed_file in fixed_files)

def calculate_map(source_files, fixed_files):
	acc = 0
	for i, source_file in enumerate(source_files):
		pj = sum(predicted_file == fixed_file for predicted_file in source_files[:i + 1] for fixed_file in fixed_files) / (i + 1)
		posj = any(source_file == fixed_file for fixed_file in fixed_files)
		acc += pj * posj
	positive_count = sum(predicted_file == fixed_file for predicted_file in source_files for fixed_file in fixed_files)
	assert positive_count != 0, 'As we have ensured that every fixed file exists in the underlying repository, ' \
		'this exception should never happen'
	return acc / positive_count

def calculate_mrr(source_files, fixed_files):
	for i, source_file in enumerate(source_files, start=1):
		if any(source_file == fixed_file for fixed_file in fixed_files):
			return 1 / i
	raise Exception('As we ensure that every fixed file exists in the underlying repository, ' \
		'this exception should never happen')

def predict_bug(bc, rw, bug):
	def inner():
		for file_object in list_all_source_files(rw.repo, commit=bug.bug_open_sha):
			source_file = file_object.path

			source_embedding = rw.get_source_embedding(bc, source_file, commit=bug.bug_open_sha)

			similarity_score = similarity.get_similarity_score(bug.embedding, source_embedding)

			final_score = similarity_score

			yield similarity_score, source_file
	similarity_scores_and_source_files = sorted(inner(), reverse=True)

	source_files = [source_file for _, source_file in similarity_scores_and_source_files]

	top_n_rank = calculate_top_n_rank(source_files, bug.fixed_files)
	map_value = calculate_map(source_files, bug.fixed_files)
	mrr_value = calculate_mrr(source_files, bug.fixed_files)

	logging.debug('Predicted files:\n%s', '\n'.join('%.6f %s' % (similarity_score, source_file) for similarity_score, source_file in similarity_scores_and_source_files[:TOP_N]))
	logging.debug('Fixed files:\n%s', '\n'.join(bug.fixed_files))

	return top_n_rank, map_value, mrr_value

def filter_existed_files(rw, fixed_files, commit='master') -> set:
	'''Check a file path represents a valid file in the underlying Git repository, filter out the valid files'''
	all_source_files_in_commit = list(list_all_source_files(rw.repo, commit=commit))
	def inner():
		for file_object in fixed_files:
			for source_file in all_source_files_in_commit:
				if trim_full_path(source_file) == file_object.path:
					is_not_empty = bool(get_formatted_source_file_from_sha(rw.repo, file_object.hexsha).rstrip())  # Check the file is not empty
					if is_not_empty:
						yield source_file
	return set(inner())

def get_patch_text_of_file(repo, sha_old, sha_new, file_path) -> str:
	patch = repo.git.diff(sha_old, sha_new, '--', file_path)
	return sanitize_patch(patch)

def get_formatted_source_file(repo, path, commit='master') -> str:
	s = repo.git.show('%s:%s' % (commit, path))
	return format_source_file(s)

def get_formatted_source_file_from_sha(repo, hexsha) -> str:
	'''Get the content of a file object by its hexsha'''
	return format_source_file(repo.git.cat_file(hexsha, '-p'))
