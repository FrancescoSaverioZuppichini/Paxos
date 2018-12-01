import time
import numpy as  np

from threading import Thread
from .Worker import Worker
from .Message import Message

from .utils import Config
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