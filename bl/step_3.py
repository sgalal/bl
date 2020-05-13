#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bert_serving.client import BertClient
from functools import reduce
import logging
import sys
import traceback

from config import BERT_IP, BERT_PORT, BERT_PORT_OUT, PROJECT_ROOT
from repowrapper import RepoWrapper
import utils

def run(bc):
	rw = RepoWrapper(PROJECT_ROOT)
	bugs = list(rw.list_all_bug_objects_with_embeddings(bc))
	bugs_len = len(bugs)

	def f(acc, bug):
		i, top_n_rank, map_value, mrr_value = acc
		top_n_rank_new, map_value_new, mrr_value_new = utils.predict_bug(bc, rw, bug)

		i += 1
		top_n_rank += top_n_rank_new
		map_value += map_value_new
		mrr_value += mrr_value_new

		logging.info('%d/%d, Top N rank %.4f%%, map %.4f, mrr %.4f', i, bugs_len, top_n_rank / i * 100, map_value / i, mrr_value / i)
		return i, top_n_rank, map_value, mrr_value

	reduce(f, bugs, (0, 0, 0, 0))

def main():
	with BertClient(ip=BERT_IP, port=BERT_PORT, port_out=BERT_PORT_OUT, show_server_config=logging.root.isEnabledFor(logging.DEBUG)) as bc:
		logging.info('Connected to BERT server')
		try:
			run(bc)
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
		finally:
			logging.info('Closing the BERT server connection')

if __name__ == '__main__':
	main()
