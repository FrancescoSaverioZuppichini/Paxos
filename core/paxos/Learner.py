from .Worker import Worker
from .Message import Message


class LearnerState:
    def __init__(self):
        self.v = None

    def __repr__(self):
        return str(self.v)


class Learner(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
        self.last = 1

    def make_state(self):
        return LearnerState()

    def handle_share_state_1b(self, msg, state):
        prop_state = msg.data[0]

        for instance_id, v in prop_state:
            state = self.get_state(instance_id)
            # TODO refactor
            self.cache[instance_id] = v
            state.v = v

        self.print()

    def handle_phase_decide(self, msg, state):
        v_val = msg.data[0]
        state.v = v_val

        self.cache[msg.instance] = v_val
        self.print()

    def print(self):
        while self.last in self.cache:
            print(self.cache[self.last], flush=True)
            del self.cache[self.last]
            self.last+= 1

    def on_rcv(self, msg):
        instance_id = msg.instance
        state = self.get_state(instance_id)

        if msg.phase == Message.DECIDE:
            self.handle_phase_decide(msg, state)
        elif msg.phase == Message.SHARE_STATE_1B:
            self.handle_share_state_1b(msg, state)


    def spawn(self):
        self.sendmsg(self.network['proposers'][0], Message.make_phase_share_state_1a([]))
