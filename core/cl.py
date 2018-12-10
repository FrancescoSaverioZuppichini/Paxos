import sys
import time

from paxos import make_network, make_logger, from_role

role, id, config_path = sys.argv[1], sys.argv[2], sys.argv[3]
network = make_network(config_path)

(ip, port), n = network[role]

logger = make_logger(debug=False)

w = from_role(role, ip, port, id, logger, network=network)

logger('Spawning {}'.format(str(w)))
w.start()

time.sleep(0.1)

w.spawn()

if role == 'clients':
    for value in sys.stdin:
        value = value.strip()
        logger('v : {}'.format(value))
        w.buffer.append(value)
        w.submit()

# python3 cl.py clients 0 config.txt 2