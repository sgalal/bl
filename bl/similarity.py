# -*- coding: utf-8 -*-

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import AVERAGE_N

def average_of_n_largest_in_array(arr, n):
	assert arr.shape[0] == 1
	if arr.shape[1] <= n:
		return np.mean(arr[0])
	else:
		return np.mean(np.partition(arr, -n)[0][-n:])

def get_similarity_score(bug_embedding, source_embedding):
	similarities = cosine_similarity([bug_embedding], source_embedding)
	maximum_similarity = average_of_n_largest_in_array(similarities, AVERAGE_N)  # Use the N maximum value as the final similarity
	return (maximum_similarity * 1000 - 930) / 20
