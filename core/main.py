from utils import Config

CONFIG_FILE = './config.txt'

configs = Config.from_file(CONFIG_FILE)

print(configs)