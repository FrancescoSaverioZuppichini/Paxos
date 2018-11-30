import sys
import time

from utils import make_network, make_logger
from paxos import Worker

role, id, config_path = sys.argv[1], sys.argv[2], sys.argv[3]
# config_path, role = './config.txt', 'learners'
network = make_network(config_path)

(ip, port), n = network[role]

logger = make_logger(debug=True)

w = Worker.from_role(role, ip, port, id, logger, network=network)

# w = Worker.from_role('learners', '239.0.0.1', 8000, 1, logger, network=network)

logger('Spawning {}'.format(str(w)))
w.start()

time.sleep(0.5)

w.spawn()

if role == 'clients':
    v = sys.argv[4]
    w.submit(v)

# python3 cl.py clients 0 config.txt 2