from paxos import Group
from utils import make_config

CONFIG_FILE = './config.txt'

# workers = Worker.from_file(CONFIG_FILE)

# print(workers)

role2ip_port_n = {
    'clients': ('239.0.0.1', 5000, 1),
    'proposers': ('239.0.0.1', 6000, 5),
    'acceptors': ('239.0.0.1', 7000, 10000),
    'learners': ('239.0.0.1', 8000, 10)
}

config = make_config(role2ip_port_n)

network = Group.from_config(config)

print(network)

for g in network.values():
    g(network)
    g.start()

network['proposers'][0].propose(1)
