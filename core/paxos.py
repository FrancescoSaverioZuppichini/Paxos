import socket
import json

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
        self.server.listen(1)
        print('{} listening'.format(self))

        while True:
            conn, addr = self.server.accept()

            with conn:
                print('Connected by', addr)
                msg = conn.recv(2048)
                msg = Message.from_enc(msg.decode())
                print('received {}'.format(msg.phase))
                self.on_rcv(msg)

    def on_rcv(self, msg):
        pass

    def sendmsg(self, to, msg):
        with  socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((to.ip, to.port))
            s.sendall(msg)
            print('{}->{} msg={}'.format(self, to, msg))
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

    def propose(self, v):
        self.c_rnd += 1

        for a in self.network['acceptors']:
            self.sendmsg(a, Message.make_phase_1a(self.c_rnd).encode().encode())

    def on_rcv(self, msg):
        if msg.phase == Message.PHASE_1B:
            print('proposer received PHASE_1B')
            pass

class Acceptor(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rnd = 0
        self.v_rnd = 0
        self.v_val = 0

    def on_rcv(self, msg):
        if msg.phase == Message.PHASE_1A:
            print('acceptor received PHASE_1A')
            pass

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