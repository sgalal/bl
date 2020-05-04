# -*- coding: utf-8 -*-

import asyncio
from bert_serving.client import BertClient
from functools import partial, reduce
import logging
from multiprocessing import Pool
import sys
import traceback

from config import BERT_IP, BERT_PORT, BERT_PORT_OUT, PROJECT_ROOT, TOP_N
from repowrapper import RepoWrapper
import utils

def main(bc):
	rw = RepoWrapper(PROJECT_ROOT)
	bugs = list(rw.list_all_bug_objects_with_embeddings(bc))

	def f(acc, bug):
		i, top_n_rank, map_value, mrr_value = acc
		top_n_rank_new, map_value_new, mrr_value_new = utils.predict_bug(bc, rw, bug)

		i += 1
		top_n_rank += top_n_rank_new
		map_value += map_value_new
		mrr_value += mrr_value_new

		logging.info('Total %d, Top N rank %.2f%%, map %.2f, mrr %.2f', i, top_n_rank / i, map_value / i, mrr_value / i)
		return i, top_n_rank, map_value, mrr_value

	reduce(f, bugs, (0, 0, 0, 0))

if __name__ == '__main__':
	with BertClient(ip=BERT_IP, port=BERT_PORT, port_out=BERT_PORT_OUT, show_server_config=logging.root.isEnabledFor(logging.DEBUG)) as bc:
		logging.info('Connected to BERT server')
		try:
			main(bc)
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
		finally:
			logging.info('Closing the BERT server connection')
