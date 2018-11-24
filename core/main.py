from paxos import Worker
from utils import make_config, make_network, logger
import time
CONFIG_FILE = './config.txt'

network = make_network(CONFIG_FILE)

network = {
    'clients': (('239.0.0.1', 5000), 1),
    'proposers': (('239.0.0.1', 6000), 1),
    'acceptors': (('239.0.0.1', 7000), 5),
    'learners': (('239.0.0.1', 8000), 2)
}



my_logger = logger(debug=False)
workers = []

for role, ((ip, port), n) in network.items():
    for id in range(n):
        w = Worker.from_role(role, ip, port, id, logger=my_logger, loss_prob=0)
        workers.append(w)

print(network)

for w in workers:
    w(network)
    w.start()

workers[0].submit(1)
