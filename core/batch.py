import sys
import time

from utils import make_network, loginfo
from paxos import Worker

role, id, config_path = sys.argv[1], sys.argv[2], sys.argv[3]


network = make_network(config_path)

(ip, port), n = network[role]


w = Worker.from_role(role, ip, port, id)

loginfo('Spawning {}'.format(str(w)))

w(network)
w.start()

if role == 'clients':
    v = sys.argv[4]
    w.submit(v)


# python3 batch.py clients 0 config.txt 2