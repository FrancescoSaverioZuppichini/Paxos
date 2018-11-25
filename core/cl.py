import sys
import time

from utils import make_network, make_logger
from paxos import Worker

role, id, config_path = sys.argv[1], sys.argv[2], sys.argv[3]

network = make_network(config_path)

(ip, port), n = network[role]

logger = make_logger(debug=True)

w = Worker.from_role(role, ip, port, id, logger)

logger('Spawning {}'.format(str(w)))

w(network)
w.start()

if role == 'clients':
    v = sys.argv[4]
    w.submit(v)

# python3 batch.py clients 0 config.txt 2