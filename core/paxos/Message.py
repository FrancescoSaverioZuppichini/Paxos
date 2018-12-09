import pickle

class Message:
    """
    This class represent a message that can be send from a worker to another one.
    It uses `pickle` module from python to serialise itself.
    """
    SUBMIT = 'SUBMIT'

    PHASE_1A = 'PHASE_1A'
    PHASE_1B = 'PHASE_1B'
    PHASE_2A = 'PHASE_2A'
    PHASE_2B = 'PHASE_2B'

    PHASE_1L = 'PHASE_1L'
    PHASE_2L = 'PHASE_2L'

    DECIDE = 'DECIDE'

    SPAWN = 'SPAWN'
    SHARE_STATE = 'SHARE_STATE'

    PING_FROM_LEADER = 'PING_FROM_LEADER'
    PONG = 'PONG'
    PING = 'PING'
    LEADER_DEAD = 'LEADER_DEAD'

    def __init__(self, phase, data, instance=None, by=None, to=None):
        """
        :param phase: One identifier for this messages. All phases are in the class fields
        :param data: What you want to exchange
        :param instance: Unique identifier of a instance (aka a room)
        :param by: sender signature
        :param to: receiver signature
        """
        super().__init__()
        self.phase = phase
        self.data = data
        self.instance = instance
        self.by = by
        self.to = to

    def encode(self):
        return pickle.dumps(self)

    @classmethod
    def from_enc(self, enc):
        m = pickle.loads(enc)
        return m

    @classmethod
    def make_spawn(cls, *args, **kwargs):
        return cls(Message.SPAWN, [], *args, **kwargs)

    @classmethod
    def make_share_state(cls, state, *args, **kwargs):
        return cls(Message.SHARE_STATE, [state], *args, **kwargs)

    @classmethod
    def make_submit(cls, v, leader_id=0, *args, **kwargs):
        return cls(cls.SUBMIT, [v, leader_id],  *args, **kwargs)

    @classmethod
    def make_phase_1a(cls, c_rnd,  *args, **kwargs):
        return cls(cls.PHASE_1A, [c_rnd],  *args, **kwargs)

    @classmethod
    def make_phase_1b(cls, rnd, v_rnd, v_val,  *args, **kwargs):
        return cls(cls.PHASE_1B, [rnd, v_rnd, v_val],  *args, **kwargs)

    @classmethod
    def make_phase_2a(cls, c_rnd, c_val,  *args, **kwargs):
        return cls(cls.PHASE_2A, [c_rnd, c_val],  *args, **kwargs)

    @classmethod
    def make_phase_2b(cls, v_rnd, v_val,  *args, **kwargs):
        return cls(cls.PHASE_2B, [v_rnd, v_val],  *args, **kwargs)

    @classmethod
    def make_decide(cls, v_val,  *args, **kwargs):
        return cls(cls.DECIDE, [v_val],  *args, **kwargs)

    @classmethod
    def ping_from_leader(cls, leader_id, *args, **kwargs):
        return cls(cls.PING_FROM_LEADER, [leader_id], *args, **kwargs)

    @classmethod
    def make_ping(cls, *args, **kwargs):
        return cls(cls.PING, [], *args, **kwargs)

    @classmethod
    def make_pong(cls, *args, **kwargs):
        return cls(cls.PONG, [], *args, **kwargs)

    @classmethod
    def make_phase_1l(cls, leader_id, *args, **kwargs):
        return cls(cls.PHASE_1L, [leader_id], *args, **kwargs)

    @classmethod
    def make_phase_2l(cls, leader_id, *args, **kwargs):
        return cls(cls.PHASE_2L, [leader_id], *args, **kwargs)

    @classmethod
    def make_leader_dead(cls, *args, **kwargs):
        return cls(cls.LEADER_DEAD, [], *args, **kwargs)

    def __str__(self):
        return self.phase