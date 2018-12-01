from .Worker import Worker

from .Client import Client
from .Proposer import Proposer
from .Learner import Learner
from .Acceptor import Acceptor

from .utils import *

def from_role(role, *args, **kwargs):
    """
    Factory method to create the correct `Worker` instance based
    on the role
    :param role: 'clients', 'proposers', 'acceptors' and 'learners'
    :param args:
    :param kwargs:
    :return:
    """
    cls = Worker
    if role == 'proposers':
        cls = Proposer
    elif role == 'acceptors':
        cls = Acceptor
    elif role == 'learners':
        cls = Learner
    elif role == 'clients':
        cls = Client
    return cls(role, *args, **kwargs)

def from_network(network, logger=None, loss_prob=0):
    """
    Factory method to create multiples workers based on the network dict.
    :param network:
    :param logger:
    :param loss_prob:
    :return:
    """
    workers = []

    for role, ((ip, port), n) in network.items():
        for id in range(n):
            w = from_role(role, ip, port, id, logger=logger, loss_prob=loss_prob, network=network)
            workers.append(w)

    return workers