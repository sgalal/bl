# -*- coding: utf-8 -*-

import re
from urllib.parse import quote

JAVA_KEYWORDS = ["abstract", "continue", "for", "new", "switch", "assert",
	"default", "goto", "package", "synchronized", "boolean", "do", "if",
	"private", "this", "break", "double", "implements", "protected",
	"throw", "byte", "else", "import", "public", "throws", "case",
	"enum", "instanceof", "return", "transient", "catch", "extends", "int",
	"short", "try", "char", "final", "interface", "static", "void", "class",
	"finally", "long", "strictfp", "volatile", "const", "float", "native",
	"super", "while", "org", "eclipse", "swt", "string", "main", "args",
	"null", "this", "extends", "true", "false",
	"map", "java", "util", "tree", "set", "concurrent", "push", "keys", "iter"]

def chunks(lst, chunk_size):
	"""Split a list into n-sized chunks, without padding"""
	a = [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
	# Combine the last two elements to ensure the size is never smaller than n
	if len(a) > 1:
		a[-2] += a[-1]
		a.pop()
	return a

def memorize(func):
	memo = {}
	def wrapper(*args):
		try:
			return memo[args]
		except KeyError:
			res = func(*args)
			memo[args] = res
			return res
	return wrapper

def url_encode(s):
	return quote(s, safe='')

def regularize_code(s):
	'''
	Regularize JAVA code to feed to the BERT model
	>>> regularize_code('aBcDefHTTPIjkl_mnOpqR')
	'a bc def http ijkl mn opq r'
	>>> regularize_code('#import { a *= 2; return x; }')
	'# a 2 x'
	'''
	# Handle Java packages
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

def regularize_java_path(path):
	'''
	>>> regularize_path('org.wildfly.security.credential.store.impl.KeystorePasswordStore.java')
	'org/wildfly/security/credential/store/impl/KeystorePasswordStore.java'
	'''
	*a, b = path.split('.')
	return '/'.join(a) + '.' + b
