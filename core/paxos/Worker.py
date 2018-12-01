import socket
import struct
import random

from threading import Thread

from paxos.utils import make_logger, Config

from .Message import Message

class Worker(Thread):
    """
    Basic class to handle all asynchronous operations. It provides a simple
    interface to communicate with other group by creating a 'client' socket and
    to listen to incoming messages by creating a 'server' socket. In order to avoid
    blocking this class implement `threading.Thread`. When calling the `.start` methods
    the server socket will start to listen.
    """
    def __init__(self, role, ip, port, id=None, logger=None, loss_prob=0, network=None):
        """

        :param role: 'clients', 'proposers', 'acceptors' and 'learners'
        :param ip: The current ip
        :param port: The current port
        :param id: The current id of the Worker
        :param logger: A function that prints the input
        :param loss_prob: (0,1) The probability for a message to be lost
        """
        super().__init__()
        self.role, self.ip, self.port, self.id = role, ip, port, int(id)
        self.make_server()
        self.make_client()

        self.logger = make_logger() if logger == None else logger
        self.loss_prob = loss_prob
        self.network = network
        self.state = {}
        self.current_msg = None

    def make_client(self):
        """
        Create a socket to send messages to other groups
        :return:
        """
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client.settimeout(0.2)
        self.client.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                               struct.pack('4sL', socket.inet_aton(self.ip),
                                           socket.INADDR_ANY))

    def make_server(self):
        """
        Create a multicast socket to listen to incoming group messages
        :return:
        """
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                        struct.pack('4sL', socket.inet_aton(self.ip),
                                    socket.INADDR_ANY))
    @property
    def addr(self):
        return (self.ip, self.port)

    def run(self):
        """
        Overrides `threading.Thread` `run`. This will bind the server socket
        to the current address and start listening. When a messages arrives
        it is decoded and the `on_rcv` function it is called.
        :return:
        """
        self.server.bind((self.ip, self.port))

        self.logger('{} listening'.format(self))

        while True:
            msg, address = self.server.recvfrom(1024)
            msg = Message.from_enc(msg)
            self.current_msg = msg
            self.logger('[{}] received {} data={}'.format(msg.instance, msg, msg.data))
            self.on_rcv(msg)

    def spawn(self):
        pass

    def on_rcv(self, msg):
        """
        This function must be implemented to correctly switch behavior based on
        the message
        :param msg: A Message instance
        :return:
        """
        raise NotImplementedError

    def get_state(self, instance_id):
        if instance_id not in self.state:
            self.state[instance_id] = self.make_state()
        return self.state[instance_id]

    def make_state(self):
        return {}

    def sendmsg(self, addr, msg, to=None):
        """
        This function uses the 'client' socket to send a messages to a group.
        If loss_prob is > 0 then the message can be lost.
        :param addr:
        :param msg:
        :return:
        """
        msg.by = self.id
        msg.to = to
        should_send = self.loss_prob <= random.random()
        if should_send:
            self.client.sendto(msg.encode(), addr)
            self.logger('[{}] sending {}'.format(msg.instance, msg))
        else: self.logger('{} loss msg={}'.format(self, msg.phase))


    def i_am_the_sender(self, msg):
        return self.id == msg.by

    def i_am_the_receiver(self, msg):
        return self.id == msg.to

    def __call__(self, network):
        self.network = network


    def __str__(self):
        return str(self.role) + ' ' + str(self.addr) + ' ' + str(self.id)