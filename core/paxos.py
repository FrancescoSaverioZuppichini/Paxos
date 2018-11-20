import socket
import json
import numpy as np

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
            print('Connected by', addr)
            with conn:
                # while True:
                msg = conn.recv(1024)
                if not msg: break
                msg = Message.from_enc(msg.decode())
                print('received {}'.format(msg.phase))
                self.on_rcv(conn, msg)

    def on_rcv(self, conn, msg):
        pass

    def sendmsg(self, ip, port, msg):
        # while True:
        with  socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(msg)
            print('{}->{} msg={}'.format(self, (ip,port), msg))
            # msg = s.recv(1024)
            # if not msg: break

            # data = s.recv(1024)

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

    def propose(self, v):
        self.v = v
        self.c_rnd += 1

        for a in self.network['acceptors']:
            self.sendmsg(a.ip, a.port, Message.make_phase_1a(self.c_rnd).encode().encode())

    def on_rcv(self, conn, msg):
        if msg.phase == Message.PHASE_1B:
            rnd, v_rnd, v_val = msg.data
            print('proposer received PHASE_1B with rnd={},v_rnd={}, v_val={}'.format(rnd, v_rnd, v_val))

            self.rcv_v_rnd.append(v_rnd)

            if v_rnd not in self.v_rnd2v_val: self.v_rnd2v_val[v_rnd] = []
            self.v_rnd2v_val[v_rnd].append(v_val)


            k = np.max(self.rcv_v_rnd) # largest v-rnd velued received
            V = list(set(self.v_rnd2v_val[k])) # set of (v-rnd, v-val) received with v-rnd=k

            c_val = V[0] # the only v-val in V

            if k == 0: c_val = self.v

            self.c_val = c_val

            for a in self.network['acceptors']:
                self.sendmsg(a.ip, a.port, Message.make_phase_2a(self.c_rnd, self.c_val).encode().encode())

class Acceptor(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rnd = 0
        self.v_rnd = 0
        self.v_val = 0

    def on_rcv(self, conn, msg):
        if msg.phase == Message.PHASE_1A:
            c_rnd = msg.data[0]

            print('acceptor received PHASE_1A with c-rnd={}'.format(c_rnd))
            if c_rnd > self.rnd:
                proposer = self.network['proposers'][0]

                self.sendmsg(proposer.ip, proposer.port, Message.make_phase_1b(self.rnd, self.v_rnd, self.v_val).encode().encode())

        elif msg.phase == Message.PHASE_2A:
            c_rnd, c_val = msg.data

            print('acceptor received PHASE_2A with c-rnd={}, c_val={}'.format(c_rnd, c_val))

class Message():
    PHASE_1A = 'PHASE_1A'
    PHASE_1B = 'PHASE_1B'
    PHASE_2A = 'PHASE_2A'
    PHASE_2B = 'PHASE_2B'

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
        return cls(cls.PHASE_2B, [v_rnd, v_val]
                   )

# phase_1 = Message(Message.PHASE_1A, [0])
# print(phase_1.data)
# encoded = json.dumps(phase_1.__dict__)
# print(Message.from_enc(encoded).data)