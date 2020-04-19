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

Modify `bl/config.py`, then:

```sh
$ . venv/bin/activate
$ bl/main.py
```

## Running BERT server on Google Colab

Google Colab \<==\> Relay server \<==\> Local client

Install frp:

```sh
$ wget https://github.com/fatedier/frp/releases/download/v0.32.1/frp_0.32.1_linux_amd64.tar.gz
$ tar -zxvf frp_0.32.1_linux_amd64.tar.gz
```

### Setup relay server

`frps.ini`:

```ini
[common]
bind_port = 27700
bind_udp_port = 27701
```

Run:

```sh
$ frps -c frps.ini &
```

### Setup Google Colab

`frpc.txt`:

```ini
[common]
server_addr = <SERVER_IP>
server_port = 27700

[secret_ssh_5555_service_0]
type = stcp
sk = <SK_5555>
local_ip = 127.0.0.1
local_port = 5555

[secret_ssh_5556_service_0]
type = stcp
sk = <SK_5556>
local_ip = 127.0.0.1
local_port = 5556
```

Run:

```sh
$ frpc -c frpc.txt &
```

### Setup client

`frpc_user.ini`:

```ini
[common]
server_addr = <SERVER_IP>
server_port = 27700

[secret_ssh_5555_service_0]
type = stcp
role = visitor
server_name = secret_ssh_5555_service_0
sk = <SK_5555>
bind_addr = 127.0.0.1
bind_port = 5555

[secret_ssh_5556_service_0]
type = stcp
role = visitor
server_name = secret_ssh_5556_service_0
sk = <SK_5556>
bind_addr = 127.0.0.1
bind_port = 5556
```

Run:

```sh
$ frpc -c frpc_user.ini &
```

Note that `SERVER_IP`, `SERVER_NAME` and `SK` should be setup correctly. `SERVER_NAME` and `SK` are random strings.
