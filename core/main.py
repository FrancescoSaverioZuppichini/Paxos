from paxos import Worker, Group

CONFIG_FILE = './config.txt'

# workers = Worker.from_file(CONFIG_FILE)

# print(workers)

network = Group.from_config(CONFIG_FILE)

print(network)


for g in network.values():
    for w in g.workers:
        w(network)
    g.start()

network['proposers'].workers[0].propose(1)
        # w.start()
# network = {'clients' : [], 'proposers' : [], 'acceptors' : [], 'learners': []}
#
# [network[w.role].append(w) for w in workers]
#
# [w(network) for w in workers]
#
# [w.start() for w in workers]
# print('-'*64)
# p = network['proposers'][0]
# p.propose(0)
