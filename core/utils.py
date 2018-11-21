import time
import tempfile

def loginfo(info):
    print('[{:.6f}]:{}'.format(time.time(), info))


def make_config(role2ip_port_n):
    with open('temp.txt', 'w') as f:
        for role, (ip, port, n) in role2ip_port_n.items():
            for _ in range(n):
                f.write('{} {} {}\n'.format(role, ip, port))
    return 'temp.txt'