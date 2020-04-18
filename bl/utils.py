# -*- coding: utf-8 -*-

import re

def chunks(lst, n):
	"""Split a list into n-sized chunks, without padding."""
	return [lst[i:i + n] for i in range(0, len(lst), n)]

def glob(base_path, file, ignore_string=None):
	from pathlib import Path
	if not ignore_string:
		for source_file in Path(base_path).glob(file):
			yield str(source_file.relative_to(base_path))
	else:
		for source_file in Path(base_path).glob(file):
			path = str(source_file.relative_to(base_path))
			if ignore_string not in path:
				yield path

def memoize(func):
	memo = {}
	def wrapper(*args):
		try:
			return memo[args]
		except KeyError:
			res = func(*args)
			memo[args] = res
			return res
	return wrapper

# =============== TODO FIXME: IMPROVE THE CODE BELOW =============== #

re_split_camel_case = re.compile(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))')
def split_camel_case(s):
	'''
	>>> list(split_camel_case('AaaBgsHhTTPRequest'))
	['aaa', 'bgs', 'hh', 'ttp', 'request']
	'''
	if s:
		if s[0].islower():
			s = s[0].upper() + s[1:]
		for x in re_split_camel_case.findall(s):
			yield x.lower()

re_tokenize_code = re.compile(r'[^a-zA-Z\'.,]+')
def tokenize_code(s):
	JAVA_KEYWORDS = ["abstract", "continue", "for", "new", "switch", "assert",
		"default", "goto", "package", "synchronized", "boolean", "do", "if",
		"private", "this", "break", "double", "implements", "protected",
		"throw", "byte", "else", "import", "public", "throws", "case",
		"enum", "instanceof", "return", "transient", "catch", "extends", "int",
		"short", "try", "char", "final", "interface", "static", "void", "class",
		"finally", "long", "strictfp", "volatile", "const", "float", "native",
		"super", "while", "org", "eclipse", "swt", "string", "main", "args",
		"null", "this", "extends", "true", "false"]
	res = []
	for x in re_tokenize_code.split(s):
		if x and x not in JAVA_KEYWORDS:
			for y in split_camel_case(x):
				res.append(y)
	return res

# =============== TODO FIXME: IMPROVE THE CODE ABOVE =============== #
