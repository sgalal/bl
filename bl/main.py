#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from bert_serving.client import BertClient
from functools import partial, reduce
import logging
from multiprocessing import Pool
import sys
import traceback
from sentence_transformers import SentenceTransformer

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

if __name__ == '__main__':
	bc = SentenceTransformer('bert-base-nli-mean-tokens')
	logging.info('Connected to BERT server')
