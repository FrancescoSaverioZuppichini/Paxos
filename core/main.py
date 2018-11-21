from paxos import Worker, Group

CONFIG_FILE = './config.txt'

# workers = Worker.from_file(CONFIG_FILE)

# print(workers)

network = Group.from_config(CONFIG_FILE)

print(network)


for g in network.values():
    g(network)
    g.start()

network['proposers'][0].propose(1)
