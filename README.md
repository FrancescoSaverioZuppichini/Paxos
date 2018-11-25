
# Paxos
## Distributed algorithm project USI - 2018
*Francesco Saverio Zuppichini*

Paxos is a protocol used to solve consensus in asynchronous systems. Simply put, consensus can be used by a set of processes that need to agree on a single value. More commonly though, processes need to agree on a sequence of totally ordered values - a problem known as atomic broadcast. 

In this project, I used the Paxos protocol to implement atomic broadcast.

Let's see some code. The **learnes** will output the learned value


```python
import pprint

from paxos import Worker
from utils import make_network, make_logger

# define the topology
# key = ((ip, port), n)
network = {
    'clients': (('239.0.0.1', 5000), 1),
    'proposers': (('239.0.0.1', 6000), 1),
    'acceptors': (('239.0.0.1', 7000), 5),
    'learners': (('239.0.0.1', 8000), 2)
}
# optionally create a logger function. e.g. lambda x: print(x)
logger = make_logger(debug=False)
# creates all the workers from the network dictionary
workers = Worker.from_network(network, logger=logger)

pprint.pprint(network)
# start the server in each workers. Each worker spawns a thread to listn for incoming msgs.
[w.start() for w in workers]
# get the client
workers[0].submit('Hello world!\n')
```

    {'acceptors': (('239.0.0.1', 7000), 5),
     'clients': (('239.0.0.1', 5000), 1),
     'learners': (('239.0.0.1', 8000), 2),
     'proposers': (('239.0.0.1', 6000), 1)}
    value Hello world!
    
    value Hello world!
    


To see all the messages types and useful informations you can enable the debug mode by calling `logger = make_logger(debug=True`)

