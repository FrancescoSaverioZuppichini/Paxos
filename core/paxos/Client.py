import time

from .Worker import Worker
from .Message import Message

class Client(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer = []
        self.DELAY = 0.001

    def submit(self, v):
        self.sendmsg(self.network['proposers'][0], Message.make_submit(v))
        time.sleep(self.DELAY)
