from .Worker import Worker
from .Message import Message

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

        if msg.phase == Message.SPAWN and not self.i_am_the_sender(msg):
            msg = Message.make_share_state(self.state)
            self.logger('sending', msg)
            self.sendmsg(self.network['learners'][0], msg, to=msg.by)

        if msg.phase == Message.SHARE_STATE and self.i_am_the_receiver(msg):
            if len(self.state) == 0:

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