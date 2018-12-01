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