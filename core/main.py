import pprint

from paxos import Worker
from utils import make_config, make_network, make_logger

# CONFIG_FILE = './config.txt'

# network = make_network(CONFIG_FILE)

network = {
    'clients': (('239.0.0.1', 5000), 1),
    'proposers': (('239.0.0.1', 6000), 1),
    'acceptors': (('239.0.0.1', 7000), 5),
    'learners': (('239.0.0.1', 8000), 2)
}

workers = Worker.from_network(network)

pprint.pprint(network)

[w.start() for w in workers]


workers[0].submit(1)
