# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.INFO)

import argparse

parser = argparse.ArgumentParser(description='Run predict')
parser.add_argument('--project-root', help='path to the project root', required=True)
parser.add_argument('--bert-port', type=int, default=5555)
parser.add_argument('--bert-port-out', type=int, default=5556)
parser.add_argument('--text-chunk-size', type=int, default=15)
parser.add_argument('--bert-ip', help='IP address of the BERT server', default='localhost')
args = parser.parse_args()

PROJECT_ROOT = args.project_root
BERT_PORT = args.bert_port
BERT_PORT_OUT = args.bert_port_out
TEXT_CHUNK_SIZE = args.text_chunk_size
BERT_IP = args.bert_ip

TOP_N = 10  # Predict 10 possible files
AVERAGE_N = 3
