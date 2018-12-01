from .Worker import Worker
from .Message import Message

class AcceptorState:
    def __init__(self):
        self.rnd = 0
        self.v_rnd = 0
        self.v_val = 0

class Acceptor(Worker):

    def make_state(self):
        return AcceptorState()


    def handle_phase_1a(self, msg, state):
        c_rnd = msg.data[0]
        instance_id = msg.instance

        if c_rnd > state.rnd:
            state.rnd = c_rnd
            proposers = self.network['proposers'][0]

            self.sendmsg(proposers,
                         Message.make_phase_1b(state.rnd, state.v_rnd, state.v_val, instance_id))

    def handle_phase_2a(self, msg, state):
        c_rnd, c_val = msg.data
        instance_id = msg.instance

        state.v_rnd = c_rnd
        state.v_val = c_val

        proposers = self.network['proposers'][0]

        self.sendmsg(proposers,
                     Message.make_phase_2b(state.v_rnd, state.v_val, instance_id))

    def on_rcv(self, msg):
        instance_id = msg.instance
        state = self.get_state(instance_id)

        if msg.phase == Message.PHASE_1A: self.handle_phase_1a(msg, state)
        elif msg.phase == Message.PHASE_2A: self.handle_phase_2a(msg, state)