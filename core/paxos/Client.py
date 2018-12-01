from .Worker import Worker
from .Message import Message
import time

class Client(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last = time.clock()

    def submit(self, v):
        msg = Message.make_submit(v, instance=self.last, leader_id=0)
        self.sendmsg(self.network['proposers'][0], msg)
