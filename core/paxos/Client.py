from .Worker import Worker
from .Message import Message
import time

class Client(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.leader_is_alive = False
        self.leader_id = None

    def on_rcv(self, msg):
        # if msg.phase == Message.PONG:
        #     if not self.leader_is_alive:
        #         role, port, id = msg.by
        #
        #         self.leader_id = id
        #
        #         msg = Message.make_submit(self.v, instance=None, leader_id=id)
        #         self.sendmsg(self.network['proposers'][0], msg)
        #
        #         self.leader_is_alive = True
        #
        # if msg.phase == Message.LEADER_DEAD:
        #     self.leader_is_alive = False
        #     role, port, id = msg.by
        #
        #     self.leader_id = id
        #
        #     msg = Message.make_submit(self.v, instance=self.instance, leader_id=id)
        #     self.sendmsg(self.network['proposers'][0], msg)

        pass

    def submit(self, v):
        self.v = v
        self.sendmsg(self.network['proposers'][0], Message.make_submit(v, instance=None))