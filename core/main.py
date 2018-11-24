from paxos import Worker
from utils import make_config, make_network
import time
CONFIG_FILE = './config.txt'

# workers = Worker.from_file( l)

# print(workers)

role2ip_port_n = {
    'clients': ('239.0.0.1', 5000, 1),
    'proposers': ('239.0.0.1', 6000, 5),
    'acceptors': ('239.0.0.1', 7000, 10),
    'learners': ('239.0.0.1', 8000, 2)
}


CONFIG_FILE = make_config(role2ip_port_n)



network = make_network(CONFIG_FILE)

workers = []

for role, ((ip, port), n) in network.items():
    for id in range(n):
        w = Worker.from_role(role, ip, port, id)
        workers.append(w)


print(network)

for w in workers:
    w(network)
    w.start()

workers[0].submit(1)
