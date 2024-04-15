# Python Chat App using TUI and Socket

## Setup and Installation

1. Install Python 3.12.X on your system
2. Install dependencies using `pip`

```shell
pip install -r requirements.txt
```

## Running the client

### \[CLI Application\] 1. Find local server at port 50000

```shell
python -m app.client_cli
```

### \[CLI Application\] 2. Custom server address

```shell
python -m app.client_cli [REMOTE_HOST]:[REMOTE_PORT]
```

```shell
python -m app.client_cli localhost:50000
```

## Running the server

### 1. Running with default address (bind to all interfaces at port 50000)

```shell
python -m app.server
```

### 2. Running with custom address and port

```shell
python -m app.server [HOST]:[PORT]
```

```shell
python -m app.server 0.0.0.0:50000
```

```shell
python -m app.server localhost:50000
```