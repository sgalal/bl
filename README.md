# bl

**N.B.:** This project is not ready for production!

An bug localization tool using BERT

## Run

## Setup server

```sh
$ virtualenv venv -p `which python3`
$ . venv/bin/activate
$ pip install bert-serving-server tensorflow-gpu\<2
$ wget https://storage.googleapis.com/bert_models/2018_10_18/uncased_L-24_H-1024_A-16.zip
$ unzip uncased_L-24_H-1024_A-16.zip
$ ZEROMQ_SOCK_TMP_DIR=/tmp/ bert-serving-start -model_dir uncased_L-24_H-1024_A-16 -max_seq_len=30 -num_worker=1 -show_tokens_to_client
```

## Setup client

### Data Preparation

[samasaki/Bench4BL](https://github.com/samasaki/Bench4BL/blob/master/downloads.sh)

```sh
$ wget https://raw.githubusercontent.com/samasaki/Bench4BL/master/downloads.sh
$ wget https://raw.githubusercontent.com/samasaki/Bench4BL/master/unpacking.sh
$ sh downloads.sh
$ sh unpacking.sh _archives data
```

The scripts downloads the archives to `_archives` directory, then unpacks them to `data` directory.

### Setup BERT client

Prerequisite: Python 3.6+

```sh
$ virtualenv venv -p `which python3`
$ . venv/bin/activate
$ pip install -r requirements.txt
```

### Run

Create `bl/config.py`, like:

```sh
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.INFO)

PROJECT_ROOT = '/home/ayaka/Hub/Bench4BL/data/Apache/HBASE'
TOP_N = 10  # Predict 10 possible files
BERT_IP = '172.23.160.1'
BERT_PORT = 5555
BERT_PORT_OUT = 5556
```

Run:

```sh
$ . venv/bin/activate
$ bl/main.py
```
