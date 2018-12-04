import time
from datetime import datetime
from threading import Thread

class Config:
    MIN_ACCEPTORS_N = 3

def make_logger(debug=True):

    def loginfo(info):
        if debug:
            print('[{}]:{}'.format(datetime.now().isoformat(), info))

    return loginfo

def make_config(role2ip_port_n):
    with open('temp.txt', 'w') as f:
        for role, (ip, port, n) in role2ip_port_n.items():
            for _ in range(n):
                f.write('{} {} {}\n'.format(role, ip, port))
    return 'temp.txt'

def make_network(config_path):
    network = {}
    print(config_path)
    with open(config_path, 'r') as f:
        for line in f.readlines():
            role, ip, port = line.strip().split(' ')
            if role not in network:
                network[role] = [(ip, int(port)), 0]
            network[role][-1] = network[role][-1] + 1
    return network
