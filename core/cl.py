import sys
import time

from paxos import make_network, make_logger, from_role
from paxos import Worker

role, id, config_path = sys.argv[1], sys.argv[2], sys.argv[3]
# config_path, role = './config.txt', 'learners'
network = make_network(config_path)

(ip, port), n = network[role]

logger = make_logger(debug=False)

w = from_role(role, ip, port, id, logger, network=network)

logger('Spawning {}'.format(str(w)))
w.start()

time.sleep(0.5)

w.spawn()

if role == 'clients':
    for value in sys.stdin:
        value = value.strip()
        logger('v : {}'.format(value))
        w.submit(value)

# python3 cl.py clients 0 config.txt 2