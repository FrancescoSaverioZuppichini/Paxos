import socket
import json
import numpy as np
import time
import struct

from threading import Thread
from utils import loginfo


class Group(Thread):

    def __init__(self, role, ip, port, workers=None):
        super().__init__()
        self.role = role
        self.ip = ip
        self.port = port
        self.workers = [] if workers == None else workers

        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind((ip, port))

        self.group = socket.inet_aton(ip)

        mreq = struct.pack('4sL', self.group, socket.INADDR_ANY)

        self.server.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            mreq)

    @property
    def addr(self):
        return self.ip, self.port

    def listen(self):
        loginfo('{} listening'.format(self))
        while True:
            msg, address = self.server.recvfrom(1024)

            msg = Message.from_enc(msg.decode())

            [w.on_rcv(msg) for w in self.workers]

    def run(self):
        self.listen()

    def __call__(self, network):
        self.network = network

    def __getitem__(self, item):
        return self.workers[item]

    def __len__(self):
        return len(self.workers)

    def append(self, object):
        self.workers.append(object)

    def __str__(self):
        return str((self.role, self.ip, self.port, len(self)))

    @classmethod
    def from_config(cls, config_file):
        network = {'clients': None, 'proposers': None, 'acceptors': None, 'learners': None}

        with open(config_file, 'r') as f:
            for line in f.readlines():
                role, ip, port = line.strip().split(' ')
                if network[role] == None:
                    network[role] = cls(role, ip, int(port))

                worker = Worker.from_role(role, network[role], id=len(network[role]))
                network[role].append(worker)

        return network


class Worker():
    def __init__(self, group, id):
        super().__init__()
        self.group = group
        self.id = id
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the time-to-live for messages to 1 so they do not
        # go past the local network segment.
        self.client.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))

        # Reuse address to test on localhost
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # add the process to the multicast group
        self.client.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                               struct.pack('4sL', socket.inet_aton(group.ip),
                                           socket.INADDR_ANY))

    def __call__(self, network):
        self.network = network

    def on_rcv(self, msg):
        pass

    def sendmsg(self, addr, msg):
        self.client.sendto(msg, addr)

    @staticmethod
    def from_role(role, *args, **kwargs):
        cls = Worker
        if role == 'proposers':
            cls = Proposer
        elif role == 'acceptors':
            cls = Acceptor
        elif role == 'learners':
            cls = Learner
        return cls(*args, **kwargs)

    def __str__(self):
        return str(self.group) + str(self.id)


class Proposer(Worker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.c_rnd = 0
        self.c_val = 0

        self.rcv_v_rnd = []
        self.v_rnd2v_val = {}

        self.v = 0

    def init_memory(self):
        self.rcv_phase1b = []
        self.rcv_phase2b = []

    def propose(self, v):
        self.v = v
        self.c_rnd += 1

        self.init_memory()

        acceptors = self.group.network['acceptors']
        # for a in self.network['acceptors']:
        self.sendmsg(acceptors.addr,
                     Message.make_phase_1a(self.c_rnd).encode().encode())

    def on_rcv(self, msg):
        if msg.phase == Message.PHASE_1B:
            rnd, v_rnd, v_val = msg.data
            loginfo('{} received PHASE_1B with rnd={},v_rnd={}, v_val={}'.format(self, rnd, v_rnd, v_val))

            self.rcv_v_rnd.append(v_rnd)
            self.rcv_phase1b.append(rnd)

            if len(self.rcv_phase1b) > len(self.group.network['acceptors']) / 2:
                loginfo('{} quorum for PHASE_1B'.format(self))

                filtered = filter(lambda x: x == self.c_rnd, self.rcv_phase1b)

                if len(list(filtered)) == len(self.rcv_phase1b):
                    if v_rnd not in self.v_rnd2v_val: self.v_rnd2v_val[v_rnd] = []

                    self.v_rnd2v_val[v_rnd].append(v_val)

                    k = np.max(self.rcv_v_rnd)  # largest v-rnd velued received
                    V = list(set(self.v_rnd2v_val[k]))  # set of (v-rnd, v-val) received with v-rnd=k

                    c_val = V[0]  # the only v-val in V

                    if k == 0: c_val = self.v

                    self.c_val = c_val

                    acceptors = self.group.network['acceptors']

                    # for a in self.network['acceptors']:
                    self.sendmsg(acceptors.addr,
                                 Message.make_phase_2a(self.c_rnd, self.c_val).encode().encode())
                # prevent others quorum
                self.rcv_phase1b = []

        elif msg.phase == Message.PHASE_2B:
            v_rnd, v_val = msg.data
            loginfo('{} received PHASE_2B with v_rnd={}, v_val={}'.format(self, v_rnd, v_val))

            self.rcv_phase2b.append(v_rnd)

            if len(self.rcv_phase2b) > len(self.group.network['acceptors']) // 2:
                loginfo('{} quorum for PHASE_2B'.format(self))
                # quorum
                filtered = filter(lambda x: x == self.c_rnd, self.rcv_phase2b)

                if len(list(filtered)) == len(self.rcv_phase2b):
                    loginfo('{:.6f}:{} PHASE_2B checked'.format(time.time(), self))
                    # TODO should lock after send?
                    # all values were c-rnd

                    learners = self.group.network['learners']

                    # for l in self.network['learners']:
                    self.sendmsg(learners.addr, Message.make_decide(self.v).encode().encode())

                # prevent others quorum
                self.rcv_phase2b = []


class Acceptor(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rnd = 0
        self.v_rnd = 0
        self.v_val = 0

    def on_rcv(self, msg):
        if msg.phase == Message.PHASE_1A:
            c_rnd = msg.data[0]

            loginfo('{} received PHASE_1A with c-rnd={}'.format(self, c_rnd))
            if c_rnd > self.rnd:
                self.rnd = c_rnd
                # TODO should get the correct proposer  maybe add 'from' in msg?
                proposers = self.group.network['proposers']

                self.sendmsg(proposers.addr,
                             Message.make_phase_1b(self.rnd, self.v_rnd, self.v_val).encode().encode())

        elif msg.phase == Message.PHASE_2A:
            c_rnd, c_val = msg.data
            self.v_rnd = c_rnd
            self.v_val = c_val

            proposers = self.group.network['proposers']

            self.sendmsg(proposers.addr,
                         Message.make_phase_2b(self.v_rnd, self.v_val).encode().encode())

            loginfo('{} received PHASE_2A with c-rnd={}, c_val={}'.format(self, c_rnd, c_val))


class Learner(Worker):

    def on_rcv(self, msg):
        if msg.phase == Message.DECIDE:
            v_val = msg.data[0]

            loginfo('{} DECIDE v_val={}'.format(self, v_val))


class Message():
    PHASE_1A = 'PHASE_1A'
    PHASE_1B = 'PHASE_1B'
    PHASE_2A = 'PHASE_2A'
    PHASE_2B = 'PHASE_2B'
    DECIDE = 'DECIDE'

    def __init__(self, phase, data):
        super().__init__()
        self.phase = phase
        self.data = data

    def encode(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_enc(self, enc):
        dec = json.loads(enc)
        m = self(dec['phase'], dec['data'])
        return m

    @classmethod
    def make_phase_1a(cls, c_rnd):
        return cls(cls.PHASE_1A, [c_rnd])

    @classmethod
    def make_phase_1b(cls, rnd, v_rnd, v_val):
        return cls(cls.PHASE_1B, [rnd, v_rnd, v_val])

    @classmethod
    def make_phase_2a(cls, c_rnd, c_val):
        return cls(cls.PHASE_2A, [c_rnd, c_val])

    @classmethod
    def make_phase_2b(cls, v_rnd, v_val):
        return cls(cls.PHASE_2B, [v_rnd, v_val])

    @classmethod
    def make_decide(cls, v_val):
        return cls(cls.DECIDE, [v_val])
