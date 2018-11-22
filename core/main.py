from paxos import Worker
from utils import make_config
import time
CONFIG_FILE = './config.txt'

# workers = Worker.from_file( l)

# print(workers)

# role2ip_port_n = {
#     'clients': ('239.0.0.1', 5000, 1),
#     'proposers': ('239.0.0.1', 6000, 5),
#     'acceptors': ('239.0.0.1', 7000, 1000),
#     'learners': ('239.0.0.1', 8000, 10)
# }
#
# CONFIG_FILE = make_config(role2ip_port_n)

network = {'clients': None, 'proposers': None, 'acceptors': None, 'learners': None}



workers = []
with open(CONFIG_FILE, 'r') as f:
    for line in f.readlines():
        role, ip, port = line.strip().split(' ')
        if network[role] == None:
            network[role] = [(ip, int(port)), 0]
        network[role][-1] = network[role][-1] + 1

        w = Worker.from_role(role, ip, int(port), network[role][-1])

        workers.append(w)

print(network)
for w in workers:
    w(network)
    w.start()

workers[0].submit(1)
