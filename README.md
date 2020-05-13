# bl

**N.B.:** This project is not ready for production!

An bug localization tool using BERT

Prerequisite: Python 3.6+

## Data Preparation

[samasaki/Bench4BL](https://github.com/samasaki/Bench4BL/blob/master/downloads.sh)

```sh
$ wget https://raw.githubusercontent.com/samasaki/Bench4BL/master/downloads.sh
$ wget https://raw.githubusercontent.com/samasaki/Bench4BL/master/unpacking.sh
$ sh downloads.sh
$ sh unpacking.sh _archives data
```

The scripts downloads the archives to `_archives` directory, then unpacks them to `data` directory.

## Configuration

Copy `bl/config.template.py` to `bl/config.py`, then modify the configuration:

```sh
TOP_N = 10  # Predict 10 possible files
BERT_IP = '172.23.160.1'
BERT_PORT = 5555
BERT_PORT_OUT = 5556
```

## Fine-tuning BERT

Prepare data:

```sh
cd WEAVER/gitrepo
git checkout master 
git pull
git checkout master
git pull
cd ../.
```

```sh
$ pip install "GitPython>=3.1,<3.2"
$ cat > run.sh
bl/prepare_train.py --project-root ../Bench4BL/data/Commons/CODEC
bl/prepare_train.py --project-root ../Bench4BL/data/Commons/COLLECTIONS
bl/prepare_train.py --project-root ../Bench4BL/data/Commons/COMPRESS
bl/prepare_train.py --project-root ../Bench4BL/data/Commons/CONFIGURATION
bl/prepare_train.py --project-root ../Bench4BL/data/Commons/CRYPTO
bl/prepare_train.py --project-root ../Bench4BL/data/Commons/CSV
bl/prepare_train.py --project-root ../Bench4BL/data/Commons/IO
bl/prepare_train.py --project-root ../Bench4BL/data/Commons/LANG
bl/prepare_train.py --project-root ../Bench4BL/data/Commons/MATH
bl/prepare_train.py --project-root ../Bench4BL/data/Commons/WEAVER
$ sh run.sh
```

This will generate `data.sqlite3`.

Prepare BERT model:

```sh
$ pip install "tensorflow-gpu<2"
$ wget https://storage.googleapis.com/bert_models/2020_02_20/uncased_L-8_H-256_A-4.zip
$ mkdir uncased_L-8_H-256_A-4
$ unzip uncased_L-8_H-256_A-4.zip -d uncased_L-8_H-256_A-4
```

Clone BERT repository:

```sh
$ git clone https://github.com/sgalal/bert.git --branch bl
$ export BERT_BASE_DIR=`pwd`/uncased_L-8_H-256_A-4
$ export BERT_REPO_DIR=`pwd`/bert
```

Run:

```sh
$ cd bert
$ python run_classifier.py \
  --task_name=BLPR \
  --do_train=true \
  --do_eval=true \
  --data_dir=$BERT_REPO_DIR/.. \
  --vocab_file=$BERT_BASE_DIR/vocab.txt \
  --bert_config_file=$BERT_BASE_DIR/bert_config.json \
  --init_checkpoint=$BERT_BASE_DIR/bert_model.ckpt \
  --max_seq_length=512 \
  --train_batch_size=32 \
  --learning_rate=2e-5 \
  --num_train_epochs=3.0 \
  --output_dir=/tmp/blpr_output/
```

## Run BERT server with fine-tuned BERT model

Prepare BERT model and the fine-tuning output `/tmp/blpr_output/`.

Run:

```sh
$ pip install "tensorflow-gpu<2" bert-serving-server
$ bert-serving-start -model_dir=uncased_L-10_H-256_A-4 -tuned_model_dir=/tmp/blpr_output/ -ckpt_name=model.ckpt-18992 -max_seq_len=192 -num_worker=1 -show_tokens_to_client
```

## Run client

```sh
$ pip install bert-serving-client "GitPython>=3.1,<3.2"
$ . venv/bin/activate
$ bl/run_predict.py --project-root ../Bench4BL/data/Commons/COMPRESS
```

# Initialize bugs

1. Run `initialize_bugs.py`
