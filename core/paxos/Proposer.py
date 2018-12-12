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

        self.rcv_v_rnd = 0
        self.v_rnd2v_val = {}

        self.v = None

        self.rcv_phase1b = []
        self.rcv_phase2b = []

        self.last_rcv_ping_from_leader = None

    def __str__(self):
        return 'c_rnd={}, c_val={}, v={}'.format(self.c_rnd, self.c_val, self.v)


class Proposer(Worker):
    PING_RATE_S = 2
    LEADER_WAIT_S = 3.5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ping_proposers_t = Thread(target=self.ping_proposers)
        self.monitor_leader_t = Thread(target=self.monitor_leader)

        self.ping_proposers_t.daemon = True
        self.monitor_leader_t.daemon = True

        self.last_instance_id = 0
        self.leader_id = self.id

        self.new_v = None

        self.flags = {}

    def ping_proposers(self):
        while True:
            if self.i_am_the_leader:
                if self.current_msg != None: self.sendmsg(self.network['proposers'][0],
                                                          Message.ping_from_leader(self.current_msg.instance,
                                                                                   self.id))
            time.sleep(self.PING_RATE_S)

    def monitor_leader(self):
        is_leader_dead = False
        # TODO bad code should be refactor
        while True:
            time.sleep(0.01)
            if self.current_msg != None:
                state = self.get_state(self.current_msg.instance)
                if state.last_rcv_ping_from_leader != None:
                    now = time.time()
                    elapsed = now - state.last_rcv_ping_from_leader
                    if elapsed > self.LEADER_WAIT_S and not is_leader_dead:
                        self.logger('Leader probably dead')
                        is_leader_dead = True
                        self.leader_id = self.id
                        self.spaw()
                    else:
                        is_leader_dead = False

    def run(self):
        if not self.ping_proposers_t.is_alive(): self.monitor_leader_t.start()
        if not self.ping_proposers_t.is_alive(): self.ping_proposers_t.start()
        super().run()

    def make_state(self):
        return ProposerState()

    def init_memory(self):
        self.rcv_phase1b = []
        self.rcv_phase2b = []

    def spawn(self):
        self.sendmsg(self.network['proposers'][0], Message.make_phase_1l(leader_id=self.id))

    def handle_submit(self, msg, state):
        v, leader_id = msg.data

        self.new_v = v
        self.last_instance_id += 1

        state = self.get_state(self.last_instance_id)

        state.v = v
        state.c_rnd = (state.c_rnd + 1) * (self.id + 1)
        state.leader_id = leader_id

        acceptors = self.network['acceptors'][0]

        self.sendmsg(acceptors,
                     Message.make_phase_1a(state.c_rnd, self.last_instance_id))

    def handle_phase_1l(self, msg, state):
        self.leader_id = max(self.leader_id, int(msg.data[0]))

    def handle_share_state_1a(self, msg, state):
        data = list(map(lambda k: (k[0], k[1].v), self.state.items()))
        self.sendmsg(msg.by[1], Message.make_phase_share_state_1b(data))

    def handle_phase_1b(self, msg, state):
        rnd, v_rnd, v_val = msg.data
        instance_id = msg.instance

        state.rcv_v_rnd = max(state.rcv_v_rnd, v_rnd)
        state.rcv_phase1b.append(rnd)

        quorum_n = max(Config.MIN_ACCEPTORS_N, self.network['acceptors'][-1]) // 2
        # TODO this whole logic was copy and paste from the weird pseudocode. It is not memory efficient
        # REVIEW I don't care since it is working well
        if len(state.rcv_phase1b) > quorum_n:
            self.logger('[{}] quorum={} for PHASE_1B'.format(msg.instance, len(state.rcv_phase1b)))

            if state.rcv_phase1b.count(state.c_rnd) == len(state.rcv_phase1b):
                if v_rnd not in state.v_rnd2v_val: state.v_rnd2v_val[v_rnd] = []

                state.v_rnd2v_val[v_rnd].append(v_val)

                k = state.rcv_v_rnd  # largest v-rnd value received
                V = list(set(state.v_rnd2v_val[k]))  # set of (v-rnd, v-val) received with v-rnd=k

                c_val = V[0]  # the only v-val in V

                if k == 0:
                    c_val = state.v
                else:
                    state.v = c_val
                state.c_val = c_val

                acceptors = self.network['acceptors'][0]

                self.sendmsg(acceptors,
                             Message.make_phase_2a(state.c_rnd, state.c_val, instance_id))

            # prevent others quorum
            state.rcv_phase1b = []

    def handle_phase_1c(self, msg, state):
        v_rnd = msg.data[0]
        if self.i_am_the_leader and v_rnd >= state.c_rnd:
            state.c_rnd = v_rnd + 1
            state.leader_id = self.id

            acceptors = self.network['acceptors'][0]

            self.sendmsg(acceptors,
                         Message.make_phase_1a(state.c_rnd, msg.instance))

            if msg.instance + 1 not in self.flags:
                self.last_instance_id = msg.instance + 1

                self.flags[msg.instance + 1] = True

                state = self.get_state(msg.instance + 1)

                state.v = self.new_v
                state.c_rnd = (state.c_rnd + 1) * (self.id + 1)
                state.leader_id = self.leader_id

                acceptors = self.network['acceptors'][0]

                self.sendmsg(acceptors,
                             Message.make_phase_1a(state.c_rnd, msg.instance + 1))

    def handle_phase_2b(self, msg, state):
        v_rnd, v_val = msg.data
        instance_id = msg.instance

        state.rcv_phase2b.append(v_rnd)

        quorum_n = max(Config.MIN_ACCEPTORS_N, self.network['acceptors'][-1]) // 2

        if len(state.rcv_phase2b) > quorum_n:
            self.logger('[{}] quorum={} for PHASE_2B'.format(msg.instance, len(state.rcv_phase2b)))
            # quorum
            if state.rcv_phase2b.count(state.c_rnd) == len(state.rcv_phase2b):
                # all values were c-rnd
                learners = self.network['learners'][0]

                self.sendmsg(learners, Message.make_decide(state.v, instance_id))
            # prevent others quorum
            state.rcv_phase2b = []

    def handle_ping_from_leader(self, msg, state):
        state.last_rcv_ping_from_leader = time.time()

    def on_rcv(self, msg):
        instance_id = msg.instance
        state = self.get_state(instance_id)

        if msg.phase == Message.PING:
            self.sendmsg(msg.by[1], Message.make_pong())
        elif msg.phase == Message.PING_FROM_LEADER:
            self.handle_ping_from_leader(msg, state)
        elif msg.phase == Message.PHASE_1L:
            self.handle_phase_1l(msg, state)
        elif msg.phase == Message.PHASE_1C:
            self.handle_phase_1c(msg, state)
        if self.i_am_the_leader:
            if msg.phase == Message.SUBMIT:
                self.handle_submit(msg, state)
            elif msg.phase == Message.PHASE_1B:
                self.handle_phase_1b(msg, state)
            elif msg.phase == Message.PHASE_2B:
                self.handle_phase_2b(msg, state)
            elif msg.phase == Message.SHARE_STATE_1A:
                self.handle_share_state_1a(msg, state)

    @property
    def i_am_the_leader(self):
        return self.id == self.leader_id
