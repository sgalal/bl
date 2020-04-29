# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.INFO)

import argparse

parser = argparse.ArgumentParser(description='Run predict')
parser.add_argument('--project-root', help='path to the project root', required=True)
args = parser.parse_args()

# Modify the configuration below

PROJECT_ROOT = args.project_root
TOP_N = 10  # Predict 10 possible files
BERT_IP = '172.27.112.1'
BERT_PORT = 5555
BERT_PORT_OUT = 5556
