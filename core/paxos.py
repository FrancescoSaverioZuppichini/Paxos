import socket
import json
import numpy as np
import time
import struct
import random
import pickle

from utils import make_logger, Config

from threading import Thread
from threading import Timer

class Worker(Thread):
    """
    Basic class to handle all asynchronous operations. It provides a simple
    interface to communicate with other group by creating a 'client' socket and
    to listen to incoming messages by creating a 'server' socket. In order to avoid
    blocking this class implement `threading.Thread`. When calling the `.start` methods
    the server socket will start to listen.
    """
    def __init__(self, role, ip, port, id=None, logger=None, loss_prob=0, network=None):
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
        self.network = network
        self.state = {}
        self.current_msg = None

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
            msg = Message.from_enc(msg)
            self.current_msg = msg
            self.on_rcv(msg)

    def spawn(self):
        pass

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

    def sendmsg(self, addr, msg, to=None):
        """
        This function uses the 'client' socket to send a messages to a group.
        If loss_prob is > 0 then the message can be lost.
        :param addr:
        :param msg:
        :return:
        """
        msg.by = self.id
        msg.to = to
        should_send = self.loss_prob <= random.random()
        if should_send: self.client.sendto(msg.encode(), addr)
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
                w = Worker.from_role(role, ip, port, id, logger=logger, loss_prob=loss_prob, network=network)
                workers.append(w)

        return workers

    def __str__(self):
        return str(self.role) + ' ' + str(self.addr) + ' ' + str(self.id)


class ProposerState:
    def __init__(self):
        self.c_rnd = 0
        self.c_val = 0

        self.rcv_v_rnd = []
        self.v_rnd2v_val = {}

        self.v = 0
        self.leader_id = None

        self.rcv_phase1b = []
        self.rcv_phase2b = []

        self.last_rcv_ping_from_leader = None

class Proposer(Worker):
    PING_RATE_S = 2
    LEADER_WAIT_S = 3
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ping_proposers_t = Thread(target=self.ping_proposers)
        self.monitor_leader_t = Thread(target=self.monitor_leader)

        self.ping_proposers_t.daemon = True
        self.monitor_leader_t.daemon = True

    def ping_proposers(self):
        while True:
            print('.', end='')
            time.sleep(self.PING_RATE_S)
            if self.current_msg != None: self.sendmsg(self.network['proposers'][0], Message.ping_from_leader(self.current_msg.instance))

    def monitor_leader(self):
        is_leader_dead = False

        while True:
            if self.current_msg != None:
                state = self.get_state(self.current_msg.instance)
                if state.last_rcv_ping_from_leader != None:
                    now = time.time()
                    elapsed = now - state.last_rcv_ping_from_leader
                    if elapsed > self.LEADER_WAIT_S and not is_leader_dead:
                        print('Leader could be dead')
                        is_leader_dead = True

    def run(self):
        self.monitor_leader_t.start()
        super().run()

    def make_state(self):
        return ProposerState()

    def init_memory(self):
        self.rcv_phase1b = []
        self.rcv_phase2b = []

    def propose(self, state, msg):
        v, leader_id = msg.data

        state.v = v
        state.c_rnd += 1
        state.leader_id = leader_id

        if int(self.id) == int(state.leader_id):

            acceptors = self.network['acceptors'][0]

            self.logger('[{}] {} sending PHASE_1A with c_rnd={}'.format(msg.instance, self, state.c_rnd))

            self.sendmsg(acceptors,
                         Message.make_phase_1a(state.c_rnd, msg.instance))

            if not self.ping_proposers_t.is_alive(): self.ping_proposers_t.start()

    def on_rcv(self, msg):
        instance_id = msg.instance
        state = self.get_state(instance_id)

        if msg.phase == Message.SUBMIT:
            self.propose(state, msg)

        if msg.phase == Message.PING_FROM_LEADER:
            self.logger(
                '[{}] {} received PING_FROM_LEADER with id={}'.format(msg.instance, self, msg.by))
            state.last_rcv_ping_from_leader = time.time()

        if int(self.id) == int(state.leader_id):

            if msg.phase == Message.PHASE_1B:
                rnd, v_rnd, v_val = msg.data
                self.logger('[{}] {} received PHASE_1B with rnd={},v_rnd={}, v_val={} received={}'.format(msg.instance, self, rnd, v_rnd, v_val, len(state.rcv_phase2b)))

                state.rcv_v_rnd.append(v_rnd)
                state.rcv_phase1b.append(rnd)

                quorum_n =  max(Config.MIN_ACCEPTORS_N, self.network['acceptors'][-1]) // 2

                if len(state.rcv_phase1b) > quorum_n:
                    self.logger('[{}] {} quorum={} for PHASE_1B'.format(msg.instance, self, len(state.rcv_phase1b)))

                    if state.rcv_phase1b.count(state.c_rnd) == len(state.rcv_phase1b):
                        if v_rnd not in state.v_rnd2v_val: state.v_rnd2v_val[v_rnd] = []

                        state.v_rnd2v_val[v_rnd].append(v_val)

                        k = np.max(state.rcv_v_rnd)  # largest v-rnd velued received
                        V = list(set(state.v_rnd2v_val[k]))  # set of (v-rnd, v-val) received with v-rnd=k

                        c_val = V[0]  # the only v-val in V

                        if k == 0: c_val = state.v

                        state.c_val = c_val

                        self.logger('[{}] {} sending PHASE_2A with c_rnd={} c_val={}'.format(msg.instance, self, state.c_rnd, state.c_val))

                        acceptors = self.network['acceptors'][0]

                        self.sendmsg(acceptors,
                                     Message.make_phase_2a(state.c_rnd, state.c_val, instance_id))

                    # prevent others quorum
                    state.rcv_phase1b = []

            elif msg.phase == Message.PHASE_2B:
                v_rnd, v_val = msg.data
                self.logger('[{}] {} received PHASE_2B with v_rnd={}, v_val={} received={}'.format(msg.instance, self, v_rnd, v_val, len(state.rcv_phase2b)))

                state.rcv_phase2b.append(v_rnd)
                quorum_n =  max(Config.MIN_ACCEPTORS_N, self.network['acceptors'][-1]) // 2

                if len(state.rcv_phase2b) > quorum_n:
                    self.logger('[{}] {} quorum={} for PHASE_2B'.format(msg.instance, self, len(state.rcv_phase2b)))
                    # quorum
                    if state.rcv_phase2b.count(state.c_rnd) == len(state.rcv_phase2b):
                        # all values were c-rnd
                        learners = self.network['learners'][0]

                        self.logger('[{}] {} sending DECIDE with v={}'.format(msg.instance, self, state.v))

                        self.sendmsg(learners, Message.make_decide(state.v, instance_id))

                    # prevent others quorum
                    state.rcv_phase2b = []

class AcceptorState:
    def __init__(self):
        self.rnd = 0
        self.v_rnd = 0
        self.v_val = 0

class Acceptor(Worker):

    def make_state(self):
        return AcceptorState()

    def on_rcv(self, msg):
        instance_id = msg.instance
        state = self.get_state(instance_id)


        if msg.phase == Message.PHASE_1A:
            c_rnd = msg.data[0]

            self.logger('[{}] {} received PHASE_1A with c-rnd={}'.format(msg.instance, self, c_rnd))

            if c_rnd > state.rnd:
                state.rnd = c_rnd
                # TODO should get the correct proposer  maybe add 'from' in msg?
                proposers = self.network['proposers'][0]

                self.logger('[{}] {} sending PHASE_1B with rnd={} v_rnd={} v_val={}'.format(msg.instance, self, state.rnd, state.v_rnd, state.v_val))

                self.sendmsg(proposers,
                             Message.make_phase_1b(state.rnd, state.v_rnd, state.v_val, instance_id))

        elif msg.phase == Message.PHASE_2A:
            c_rnd, c_val = msg.data
            state.v_rnd = c_rnd
            state.v_val = c_val

            self.logger('[{}] {} received PHASE_2A with c-rnd={}, c_val={}'.format(msg.instance, self, c_rnd, c_val))

            proposers = self.network['proposers'][0]

            self.logger('[{}] {} sending PHASE_2B with v_rnd={} v_val={}'.format(msg.instance, self, state.v_rnd, state.v_val))

            self.sendmsg(proposers,
                         Message.make_phase_2b(state.v_rnd, state.v_val, instance_id))

class LearnerState:
    def __init__(self):
        self.v = None

    def __repr__(self):
        return str(self.v)

class Learner(Worker):


    def make_state(self):
        return LearnerState()

    def on_rcv(self, msg):
        instance_id = msg.instance

        if instance_id != None:
            state = self.get_state(instance_id)

        if msg.phase == Message.SPAWN and int(self.id) != int(msg.by):
            print('sending my state')
            self.sendmsg(self.network['learners'][0], Message.make_share_state(self.state), to=msg.by)

        if msg.phase == Message.SHARE_STATE and int(self.id) == int(msg.to):
            self.state = msg.data[0]
            for s in self.state.values():
                print(s.v)

        if msg.phase == Message.DECIDE:
            v_val = msg.data[0]
            state.v = v_val
            self.logger('[{}] {} DECIDE v_val={}'.format(msg.instance, self, v_val))

            print(v_val)

    def spawn(self):
        self.sendmsg(self.network['learners'][0], Message.make_spawn())

class Client(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last = time.time()

    def submit(self, v):
        msg = Message.make_submit(v, instance=self.last, leader_id=0)
        self.logger('[{}] {} sending SUBMIT with val={}'.format(self, msg.instance, v))
        self.sendmsg(self.network['proposers'][0], msg)
        self.last += 1



class Message():
    SUBMIT = 'SUBMIT'
    PHASE_1A = 'PHASE_1A'
    PHASE_1B = 'PHASE_1B'
    PHASE_2A = 'PHASE_2A'
    PHASE_2B = 'PHASE_2B'
    DECIDE = 'DECIDE'

    SPAWN = 'SPAWN'
    SHARE_STATE = 'SHARE_STATE'

    PING_FROM_LEADER = 'PING_FROM_LEADER'
    PONG = 'I_AM_ALIVE'

    def __init__(self, phase, data, instance=None, by=None, to=None):
        super().__init__()
        self.phase = phase
        self.data = data
        self.instance = instance
        self.by = by
        self.to = to

    def encode(self):
        return pickle.dumps(self)

    @classmethod
    def from_enc(self, enc):
        # dec = json.loads(enc)
        m = pickle.loads(enc)
        return m

    @classmethod
    def make_spawn(cls, *args, **kwargs):
        return cls(Message.SPAWN, [], *args, **kwargs)

    @classmethod
    def make_share_state(cls, state, *args, **kwargs):
        return cls(Message.SHARE_STATE, [state], *args, **kwargs)

    @classmethod
    def make_submit(cls, v, leader_id=0, *args, **kwargs):
        return cls(cls.SUBMIT, [v, leader_id],  *args, **kwargs)

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

    @classmethod
    def you_are_leader(cls, *args, **kwargs):
        return cls(cls.YOU_ARE_LEADER, *args, **kwargs)

    @classmethod
    def leader_selected(cls, leader_id, *args, **kwargs):
        return cls(cls.LEADER_SELECTED, [leader_id], *args, **kwargs)

    @classmethod
    def ping_from_leader(cls, *args, **kwargs):
        return cls(cls.PING_FROM_LEADER, [], *args, **kwargs)

