from .Worker import Worker
from .Message import Message
import time

class Client(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def submit(self, v):
        self.v = v
        self.sendmsg(self.network['proposers'][0], Message.make_submit(v, instance=None))