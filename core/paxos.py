import socket
import json
import numpy as np
import time
import struct
import random

from utils import make_logger, Config

from threading import Thread

class Worker(Thread):
    """
    Basic class to handle all asynchronous operations. It provides a simple
    interface to communicate with other group by creating a 'client' socket and
    to listen to incoming messages by creating a 'server' socket. In order to avoid
    blocking this class implement `threading.Thread`. When calling the `.start` methods
    the server socket will start to listen.
    """
    def __init__(self, role, ip, port, id=None, logger=None, loss_prob=0):
        """

        :param role: 'clients', 'proposers', 'acceptors' and 'learners'
        :param ip: The current ip
        :param port: The current port
        :param id: The current id of the Worker
        :param logger: A function that prints the input
        :param loss_prob: (0,1) The probability for a message to be lost
        """
        super().__init__()
        self.role, self.ip, self.port, self.id = role, ip, port, id
        self.make_server()
        self.make_client()

        self.logger = make_logger() if logger == None else logger
        self.loss_prob = loss_prob
        self.state = {}

    def make_client(self):
        """
        Create a socket to send messages to other groups
        :return:
        """
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client.settimeout(0.2)
        self.client.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                               struct.pack('4sL', socket.inet_aton(self.ip),
                                           socket.INADDR_ANY))

    def make_server(self):
        """
        Create a multicast socket to listen to incoming group messages
        :return:
        """
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                        struct.pack('4sL', socket.inet_aton(self.ip),
                                    socket.INADDR_ANY))
    @property
    def addr(self):
        return (self.ip, self.port)

    def run(self):
        """
        Overrides `threading.Thread` `run`. This will bind the server socket
        to the current address and start listening. When a messages arrives
        it is decoded and the `on_rcv` function it is called.
        :return:
        """
        self.server.bind((self.ip, self.port))

        self.logger('{} listening'.format(self))
        while True:
            msg, address = self.server.recvfrom(1024)
            msg = Message.from_enc(msg.decode())
            self.on_rcv(msg)

    def on_rcv(self, msg):
        """
        This function must be implemented to correctly switch behavior based on
        the message
        :param msg: A Message instance
        :return:
        """
        raise NotImplementedError

    def get_state(self, instance_id):
        if instance_id not in self.state:
            self.state[instance_id] = self.make_state()
        return self.state[instance_id]

    def make_state(self):
        return {}

    def sendmsg(self, addr, msg):
        """
        This function uses the 'client' socket to send a messages to a group.
        If loss_prob is > 0 then the message can be lost.
        :param addr:
        :param msg:
        :return:
        """
        should_send = self.loss_prob <= random.random()
        if should_send: self.client.sendto(msg.encode().encode(), addr)
        else: self.logger('{} loss msg={}'.format(self, msg.phase))

    def __call__(self, network):
        self.network = network

    @staticmethod
    def from_role(role, *args, **kwargs):
        """
        Factory method to create the correct `Worker` instance based
        on the role
        :param role: 'clients', 'proposers', 'acceptors' and 'learners'
        :param args:
        :param kwargs:
        :return:
        """
        cls = Worker
        if role == 'proposers':
            cls = Proposer
        elif role == 'acceptors':
            cls = Acceptor
        elif role == 'learners':
            cls = Learner
        elif role == 'clients':
            cls = Client
        return cls(role, *args, **kwargs)

    @staticmethod
    def from_network(network, logger=None, loss_prob=0):
        """
        Factory method to create multiples workers based on the network dict.
        :param network:
        :param logger:
        :param loss_prob:
        :return:
        """
        workers = []

        for role, ((ip, port), n) in network.items():
            for id in range(n):
                w = Worker.from_role(role, ip, port, id, logger=logger, loss_prob=loss_prob)
                workers.append(w)
                w(network)

        return workers

    def __str__(self):
        return str(self.role) + ' ' + str(self.addr) + ' ' + str(self.id)

class Proposer(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.c_rnd = 0
        self.c_val = 0

        self.rcv_v_rnd = []
        self.v_rnd2v_val = {}

        self.v = 0

    def make_state(self):
        return { 'c_rnd' : 0 ,
                 'c_val' : 0,
                 
                 }

    def init_memory(self):
        self.rcv_phase1b = []
        self.rcv_phase2b = []

    def propose(self, v):
        self.v = v
        self.c_rnd += 1
        self.init_memory()

        acceptors = self.network['acceptors'][0]

        self.logger('{} sending PHASE_1A with c_rnd={}'.format(self, self.c_rnd))

        self.sendmsg(acceptors,
                     Message.make_phase_1a(self.c_rnd))

    def on_rcv(self, msg):
        if msg.phase == Message.SUBMIT:
            v, self.proposer_id = msg.data
            self.propose(v)

        if int(self.id) == int(self.proposer_id):

            if msg.phase == Message.PHASE_1B:
                rnd, v_rnd, v_val = msg.data
                self.logger('{} received PHASE_1B with rnd={},v_rnd={}, v_val={} received={}'.format(self, rnd, v_rnd, v_val, len(self.rcv_phase2b)))

                self.rcv_v_rnd.append(v_rnd)
                self.rcv_phase1b.append(rnd)

                quorum_n =  max(Config.MIN_ACCEPTORS_N, self.network['acceptors'][-1]) // 2

                if len(self.rcv_phase1b) > quorum_n:
                    self.logger('{} quorum={} for PHASE_1B'.format(self, len(self.rcv_phase1b)))

                    if self.rcv_phase1b.count(self.c_rnd) == len(self.rcv_phase1b):
                        if v_rnd not in self.v_rnd2v_val: self.v_rnd2v_val[v_rnd] = []

                        self.v_rnd2v_val[v_rnd].append(v_val)

                        k = np.max(self.rcv_v_rnd)  # largest v-rnd velued received
                        V = list(set(self.v_rnd2v_val[k]))  # set of (v-rnd, v-val) received with v-rnd=k

                        c_val = V[0]  # the only v-val in V

                        if k == 0: c_val = self.v

                        self.c_val = c_val

                        self.logger('{} sending PHASE_2A with c_rnd={} c_val'.format(self, self.c_rnd, self.c_val))

                        acceptors = self.network['acceptors'][0]

                        self.sendmsg(acceptors,
                                     Message.make_phase_2a(self.c_rnd, self.c_val))

                    # prevent others quorum
                    self.rcv_phase1b = []

            elif msg.phase == Message.PHASE_2B:
                v_rnd, v_val = msg.data
                self.logger('{} received PHASE_2B with v_rnd={}, v_val={} received={}'.format(self, v_rnd, v_val, len(self.rcv_phase2b)))

                self.rcv_phase2b.append(v_rnd)
                quorum_n =  max(Config.MIN_ACCEPTORS_N, self.network['acceptors'][-1]) // 2


                if len(self.rcv_phase2b) > quorum_n:
                    self.logger('{} quorum={} for PHASE_2B'.format(self, len(self.rcv_phase2b)))
                    # quorum
                    if self.rcv_phase2b.count(self.c_rnd) == len(self.rcv_phase2b):
                        # all values were c-rnd
                        learners = self.network['learners'][0]

                        self.logger('{} sending DECIDE with v={}'.format(self, self.v))

                        self.sendmsg(learners, Message.make_decide(self.v))

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

            self.logger('{} received PHASE_1A with c-rnd={}'.format(self, c_rnd))

            if c_rnd > self.rnd:
                self.rnd = c_rnd
                # TODO should get the correct proposer  maybe add 'from' in msg?
                proposers = self.network['proposers'][0]

                self.logger('{} sending PHASE_1B with rnd={} v_rnd={} v_val={}'.format(self, self.rnd, self.v_rnd, self.v_val))

                self.sendmsg(proposers,
                             Message.make_phase_1b(self.rnd, self.v_rnd, self.v_val))

        elif msg.phase == Message.PHASE_2A:
            c_rnd, c_val = msg.data
            self.v_rnd = c_rnd
            self.v_val = c_val

            self.logger('{} received PHASE_2A with c-rnd={}, c_val={}'.format(self, c_rnd, c_val))

            proposers = self.network['proposers'][0]

            self.logger('{} sending PHASE_2B with v_rnd={} v_val={}'.format(self, self.v_rnd, self.v_val))

            self.sendmsg(proposers,
                         Message.make_phase_2b(self.v_rnd, self.v_val))

class Learner(Worker):

    def on_rcv(self, msg):
        if msg.phase == Message.DECIDE:
            v_val = msg.data[0]

            self.logger('{} DECIDE v_val={}'.format(self, v_val))

            print('value {}'.format(v_val))

class Client(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last = 0

    def submit(self, v):
        self.logger('{} sending SUBMIT with val={}'.format(self, v))
        self.sendmsg(self.network['proposers'][0], Message.make_submit(v, instance=self.last))
        self.last += 1

class Message():
    SUBMIT = 'SUBMIT'
    PHASE_1A = 'PHASE_1A'
    PHASE_1B = 'PHASE_1B'
    PHASE_2A = 'PHASE_2A'
    PHASE_2B = 'PHASE_2B'
    DECIDE = 'DECIDE'

    def __init__(self, phase, data, instance):
        super().__init__()
        self.phase = phase
        self.data = data
        self.instance = instance

    def encode(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_enc(self, enc):
        dec = json.loads(enc)
        m = self(dec['phase'], dec['data'], dec['instance'])
        return m

    @classmethod
    def make_submit(cls, v, id=0, *args, **kwargs):
        return cls(cls.SUBMIT, [v, id],  *args, **kwargs)

    @classmethod
    def make_phase_1a(cls, c_rnd,  *args, **kwargs):
        return cls(cls.PHASE_1A, [c_rnd],  *args, **kwargs)

    @classmethod
    def make_phase_1b(cls, rnd, v_rnd, v_val,  *args, **kwargs):
        return cls(cls.PHASE_1B, [rnd, v_rnd, v_val],  *args, **kwargs)

    @classmethod
    def make_phase_2a(cls, c_rnd, c_val,  *args, **kwargs):
        return cls(cls.PHASE_2A, [c_rnd, c_val],  *args, **kwargs)

    @classmethod
    def make_phase_2b(cls, v_rnd, v_val,  *args, **kwargs):
        return cls(cls.PHASE_2B, [v_rnd, v_val],  *args, **kwargs)

    @classmethod
    def make_decide(cls, v_val,  *args, **kwargs):
        return cls(cls.DECIDE, [v_val],  *args, **kwargs)
