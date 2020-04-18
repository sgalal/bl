# bl

**N.B.:** This project is not completed yet!

An experimental bug localization tool

## Run

## Setup server

```sh
$ virtualenv venv -p `which python3`
$ . venv/bin/activate
$ pip install bert-serving-server tensorflow-gpu\<2
$ wget https://storage.googleapis.com/bert_models/2018_10_18/uncased_L-24_H-1024_A-16.zip
$ unzip uncased_L-24_H-1024_A-16.zip
$ ZEROMQ_SOCK_TMP_DIR=/tmp/ bert-serving-start -model_dir uncased_L-24_H-1024_A-16 -num_worker=1 -show_tokens_to_client
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

Modify `config.py`, then:

```
$ . venv/bin/activate
$ ./main.py
```

## Running BERT server in Google Colab

Google Colab \<==\> Relay server \<==\> Local client

Install frp:

```sh
$ wget https://github.com/fatedier/frp/releases/download/v0.32.1/frp_0.32.1_linux_amd64.tar.gz
$ tar -zxvf frp_0.32.1_linux_amd64.tar.gz
```

### Setup on relay server

`frps_5555.ini`:

```ini
[common]
bind_port = 27700
bind_udp_port = 27701
```

`frps_5556.ini`:

```ini
[common]
bind_port = 27702
bind_udp_port = 27703
```

Run:

```sh
$ ./frps -c ./frps_5555.ini &
$ ./frps -c ./frps_5556.ini &
```

### Setup on Google Colab

`frpc_5555.txt`:

```ini
[common]
server_addr = <SERVER_IP>
server_port = 27700

[secret_ssh]
type = stcp
sk = <SK>
local_ip = 127.0.0.1
local_port = 5555
```

`frpc_5556.txt`:

```ini
[common]
server_addr = <SERVER_IP>
server_port = 27702

[secret_ssh]
type = stcp
sk = <SK>
local_ip = 127.0.0.1
local_port = 5556
```

Run:

```sh
$ frp_0.32.1_linux_amd64/frpc -c frp_0.32.1_linux_amd64/frpc_5555.txt &
$ frp_0.32.1_linux_amd64/frpc -c frp_0.32.1_linux_amd64/frpc_5556.txt &
```

### Setup on local client

`frpc_user_5555.ini`:

```ini
[common]
server_addr = <SERVER_IP>
server_port = 27700

[secret_ssh_visitor]
type = stcp
role = visitor
server_name = <SERVER_NAME>
sk = <SK>
bind_addr = 127.0.0.1
bind_port = 5555
```

`frpc_user_5556.ini`:

```ini
[common]
server_addr = <SERVER_IP>
server_port = 27702

[secret_ssh_visitor]
type = stcp
role = visitor
server_name = <SERVER_NAME>
sk = <SK>
bind_addr = 127.0.0.1
bind_port = 5556
```

Run:

```sh
$ ./frpc -c ./frpc_user_5555.ini &
$ ./frpc -c ./frpc_user_5556.ini &
```

Note that `SERVER_IP`, `SERVER_NAME` and `SK` should be setup correctly. `SERVER_NAME` and `SK` are random strings.
