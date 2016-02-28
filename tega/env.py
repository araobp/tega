import os

# REST API server host name or IP address
HOST = 'localhost'

# REST API server port number
PORT = 8888

# REST API HTTP request headers
HEADERS = {'Content-type': 'application/json',
           'Accept': 'application/json',
           'Connection': 'Keep-Alive'}

# REST API transaction gc period in sec
TRANSACTION_GC_PERIOD = 300

# WebSocket URL
WEBSOCKET_PUBSUB_URL = 'ws://{}:{}/_pubsub'

# Connect retry timer in sec (Local DB to Global DB)
CONNECT_RETRY_TIMER = 5

# Directory for log and snapshot files
DATA_DIR = './var'

# tega logo
LOGO = '''
   __                  
  / /____  ____ _____ _
 / __/ _ \/ __ `/ __ `/
/ /_/  __/ /_/ / /_/ / 
\__/\___/\__, /\__,_/  
        /____/       '''

# Request timeout in sec
REQUEST_TIMEOUT = 30

# readline history
HISTORY_FILE = os.path.expanduser('~/.tega_history')
HISTORY_LENGTH = 20
