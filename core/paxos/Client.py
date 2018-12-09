from .Worker import Worker
from .Message import Message
import time

class Client(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer = []

    def submit(self):
        while len(self.buffer) > 0:
            v = self.buffer.pop()
            self.sendmsg(self.network['proposers'][0], Message.make_submit(v, instance=None))
            time.sleep(0.001)