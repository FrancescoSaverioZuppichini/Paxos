import pprint
import time

from paxos import Worker, Message

CONFIG_FILE = './config.txt'

workers = Worker.from_file(CONFIG_FILE)

print(workers)

network = {'clients' : [], 'proposers' : [], 'acceptors' : [], 'learners': []}

[network[w.role].append(w) for w in workers]
[w(network) for w in workers]

[w.start() for w in workers]


p = network['proposers'][0]
p.propose(0)
#
# pprint.pprint(network)
#
# workers[0].start()
# #
# workers[1].sendmsg(workers[0], Message.make_phase_1a(0).encode().encode())
