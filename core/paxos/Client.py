import time

from .Worker import Worker
from .Message import Message

class Client(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer = []

    def submit(self):
        while len(self.buffer) > 0:
            v = self.buffer.pop()
            self.sendmsg(self.network['proposers'][0], Message.make_submit(v))
            time.sleep(0.001)
