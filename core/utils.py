class Config:

    def __init__(self, role, ip, port):
        self.role, self.ip, self.port = role, ip, port

    @classmethod
    def from_file(cls, config_file):
        configs = []
        with open(config_file, 'r') as f:
            for line in f.readlines():
                role, ip, port = line.strip().split(' ')
                configs.append(cls(role, ip, int(port)))
        return configs



