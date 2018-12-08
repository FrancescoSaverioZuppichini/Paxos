from .Worker import Worker
from .Message import Message

import sys

class LearnerState:
    def __init__(self):
        self.v = None

    def __repr__(self):
        return str(self.v)

class Learner(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.printed = [None]

    def make_state(self):
        return LearnerState()

    def handle_phase_spawn(self, msg):
        to = msg.by
        msg = Message.make_share_state(self.state)
        self.sendmsg(self.network['learners'][0], msg, to=to)

    def handle_phase_share_state(self, msg):
        self.state = {**self.state, **msg.data[0]}
        for s in self.state.values():
            if s.v not in self.printed:
                print(s.v)

    def handle_phase_decide(self, msg, state):
        v_val = msg.data[0]
        state.v = v_val
        print(v_val)
        sys.stdout.flush()
        self.printed.append(v_val)

    def on_rcv(self, msg):
        instance_id = msg.instance
        state = self.get_state(instance_id)

        if msg.phase == Message.DECIDE: self.handle_phase_decide(msg, state)
        elif msg.phase == Message.SHARE_STATE and self.i_am_the_receiver(msg): self.handle_phase_share_state(msg)
        elif msg.phase == Message.SPAWN and not self.i_am_the_sender(msg): self.handle_phase_spawn(msg)


    def spawn(self):
        self.sendmsg(self.network['learners'][0], Message.make_spawn())