import pprint

from paxos import Worker
from utils import make_config, make_network, make_logger
import time
# CONFIG_FILE = './config.txt'

# network = make_network(CONFIG_FILE)
# define the topology
# key = ((ip, port), n)
network = {
    'clients': (('239.0.0.1', 5000), 1),
    'proposers': (('239.0.0.1', 6000), 2),
    'acceptors': (('239.0.0.1', 7000), 3),
    'learners': (('239.0.0.1', 8000), 1)
}
# optionally create a logger function. e.g. lambda x: print(x)
logger = make_logger(debug=True)
# creates all the workers from the network dictionary
workers = Worker.from_network(network, logger=logger)

pprint.pprint(network)
# start the server in each workers
[w.start() for w in workers]

time.sleep(0.5)
# get the client
workers[0].submit('Hello world!')
# workers[0].submit('Hello world!')

