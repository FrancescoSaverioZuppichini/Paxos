from paxos import Worker

CONFIG_FILE = './config.txt'

workers = Worker.from_file(CONFIG_FILE)

print(workers)

network = {'clients' : [], 'proposers' : [], 'acceptors' : [], 'learners': []}

[network[w.role].append(w) for w in workers]
[w(network) for w in workers]

[w.start() for w in workers]
print('-'*64)
p = network['proposers'][0]
p.propose(0)
