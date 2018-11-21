import sys
import time

from paxos import Group

role, id, config= sys.argv[1], sys.argv[2], sys.argv[3]

print(role, id, config)

LOCAL_CONFIG_PATH = 'configs/{}-{}.txt'.format(role, id)

local_config = ''
#
# with open(config, 'r') as f:
#     for line in f.readlines():
#         role_, _, _= line.strip().split(' ')
#         if role_ == role_:
#             local_config += line
#             break
#
# with open(config, 'w') as f:
#     f.write(local_config)

network = Group.from_config(config)

network[role].start()

if role == 'clients':
    v = sys.argv[4]
    network[role][0].submit(v)