import socket
import json
import numpy as np
import time

from threading import Thread

class Worker(Thread):
    def __init__(self, role, ip, port):
        super().__init__()
        self.role, self.ip, self.port = role, ip, port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((ip, port))
        self.network = None

    def __call__(self, network):
        self.network = network

    def listen(self):
        self.server.listen(10)
        print('{} listening'.format(self))

        while True:
            conn, addr  = self.server.accept()
            with conn:
                msg = conn.recv(1024)
                if not msg: break
                msg = Message.from_enc(msg.decode())
                # print('{} received {}'.format(self, msg.phase))
                self.on_rcv(conn, msg)

    def on_rcv(self, conn, msg):
        pass

    def sendmsg(self, ip, port, msg):
        with  socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(msg)
            # print('{}->{} msg={}'.format(self, (ip,port), msg))

    def run(self):
        self.listen()

    @staticmethod
    def from_file(config_file):
        configs = []
        with open(config_file, 'r') as f:
            for line in f.readlines():
                role, ip, port = line.strip().split(' ')
                cls = Worker
                if role == 'proposers':
                    cls = Proposer
                elif role == 'acceptors':
                    cls = Acceptor
                elif role == 'learners':
                    cls = Learner
                configs.append(cls(role, ip, int(port)))
        return configs

    def __str__(self):
        return str((self.role, self.ip, self.port))

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

        for a in self.network['acceptors']:
            self.sendmsg(a.ip, a.port,
                         Message.make_phase_1a(self.c_rnd).encode().encode())

    def on_rcv(self, conn, msg):
        if msg.phase == Message.PHASE_1B:
            rnd, v_rnd, v_val = msg.data
            print('{:.6f}:{} received PHASE_1B with rnd={},v_rnd={}, v_val={}'.format(time.time(), self, rnd, v_rnd, v_val))

            self.rcv_v_rnd.append(v_rnd)
            self.rcv_phase1b.append(rnd)

            if len(self.rcv_phase1b) > len(self.network['acceptors']) / 2:
                print('{:.6f}:{} quorum for PHASE_1B'.format(time.time(), self))

                filtered = filter(lambda x: x == self.c_rnd, self.rcv_phase1b)

                if len(list(filtered)) == len(self.rcv_phase1b):
                    if v_rnd not in self.v_rnd2v_val: self.v_rnd2v_val[v_rnd] = []

                    self.v_rnd2v_val[v_rnd].append(v_val)

                    k = np.max(self.rcv_v_rnd) # largest v-rnd velued received
                    V = list(set(self.v_rnd2v_val[k])) # set of (v-rnd, v-val) received with v-rnd=k

                    c_val = V[0] # the only v-val in V

                    if k == 0: c_val = self.v

                    self.c_val = c_val

                    for a in self.network['acceptors']:
                        self.sendmsg(a.ip, a.port,
                                     Message.make_phase_2a(self.c_rnd, self.c_val).encode().encode())
                # prevent others quorum
                self.rcv_phase1b = []

        elif msg.phase == Message.PHASE_2B:
            v_rnd, v_val = msg.data
            print('{:.6f}:{} received PHASE_2B with v_rnd={}, v_val={}'.format(time.time(), self, v_rnd, v_val))

            self.rcv_phase2b.append(v_rnd)

            if len(self.rcv_phase2b) > len(self.network['acceptors']) // 2:
                print('{:.6f}:{} quorum for PHASE_2B'.format(time.time(), self))
                # quorum
                filtered = filter(lambda x: x == self.c_rnd, self.rcv_phase2b)

                if len(list(filtered)) == len(self.rcv_phase2b):
                    print('{:.6f}:{} PHASE_2B checked'.format(time.time(), self))
                    # TODO should lock after send?
                    # all values were c-rnd
                    for l in self.network['learners']:
                        self.sendmsg(l.ip, l.port, Message.make_decide(self.v).encode().encode())

                # prevent others quorum
                self.rcv_phase2b = []

class Acceptor(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rnd = 0
        self.v_rnd = 0
        self.v_val = 0

    def on_rcv(self, conn, msg):
        if msg.phase == Message.PHASE_1A:
            c_rnd = msg.data[0]

            print('{:.6f}:{} received PHASE_1A with c-rnd={}'.format(time.time(), self, c_rnd))
            if c_rnd > self.rnd:
                self.rnd = c_rnd
                # TODO should get the correct proposer  maybe add 'from' in msg?
                proposer = self.network['proposers'][0]

                self.sendmsg(proposer.ip, proposer.port,
                             Message.make_phase_1b(self.rnd, self.v_rnd, self.v_val).encode().encode())

        elif msg.phase == Message.PHASE_2A:
            c_rnd, c_val = msg.data
            self.v_rnd = c_rnd
            self.v_val = c_val

            proposer = self.network['proposers'][0]

            self.sendmsg(proposer.ip, proposer.port,
                         Message.make_phase_2b(self.v_rnd, self.v_val).encode().encode())


            print('{:.6f}:{} received PHASE_2A with c-rnd={}, c_val={}'.format(time.time(), self, c_rnd, c_val))

class Learner(Worker):

    def on_rcv(self, conn, msg):
        if msg.phase == Message.DECIDE:
            v_val = msg.data[0]

            print('{:.6f}:{} DECIDE v_val={}'.format(time.time(), self, v_val))

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
