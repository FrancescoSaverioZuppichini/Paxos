
# Paxos
## Distributed algorithm project USI - 2018
*Francesco Saverio Zuppichini*

Paxos is a protocol used to solve consensus in asynchronous systems. Simply put, consensus can be used by a set of processes that need to agree on a single value. More commonly though, processes need to agree on a sequence of totally ordered values - a problem known as atomic broadcast. 

In this project, I used the Paxos protocol to implement atomic broadcast.

Let's see some code. The **learnes** will output the learned value


```python
import pprint

from paxos import from_network, make_logger

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
workers = from_network(network, logger=logger)

pprint.pprint(network)
# start the server in each worker. Each worker spawns a thread to listen for incoming msgs.
[w.start() for w in workers]
# get the client
workers[0].submit('Hello world!\n')
```

    {'acceptors': (('239.0.0.1', 7000), 5),
     'clients': (('239.0.0.1', 5000), 1),
     'learners': (('239.0.0.1', 8000), 2),
     'proposers': (('239.0.0.1', 6000), 1)}
   Hello world!
    
   Hello world!
    


To see all the messages types and useful informations you can enable the debug mode by calling `logger = make_logger(debug=True`)

## Implementation
 Project structure
```
 .
├── core // all the code here
│   ├── cl.py
│   ├── config.txt
│   ├── example.ipynb
│   ├── __init__.py
│   ├── main.py
│   ├── paxos // paxos implementation
│   │   ├── Acceptor.py
│   │   ├── Client.py
│   │   ├── __init__.py 
│   │   ├── Learner.py
│   │   ├── Message.py
│   │   ├── Proposer.py
│   │   ├── utils.py 
│   │   └── Worker.py
│   ├── paxos-tests // tests from the TA
│   ├── scripts // scripts to run paxos from command line
│   │   ├── acceptor.sh
│   │   ├── client.sh
│   │   ├── learner.sh
│   │   └── proposer.sh
│   └── test.sh
├── project.pdf
└── README.md
```
The core implementation can be found at `./core/paxos` 

## Tests

I used the provided tests. It follows the outputs of each one of them

### Paxos
*The test file was no modified and after 5 seconds all the workes are killed*

```
$ ./run.sh paxos 3000 && ./check_all.sh 
starting acceptors...
starting learners...
starting proposers...
waiting to start clients
starting clients...
./acceptor.sh: line 1: 12155 Terminated              python3 ../../cl.py acceptors $1 $2
./learner.sh: line 1: 12207 Terminated              python3 ../../cl.py learners $1 $2
./acceptor.sh: line 1: 12153 Terminated              python3 ../../cl.py acceptors $1 $2
./acceptor.sh: line 1: 12154 Terminated              python3 ../../cl.py acceptors $1 $2
./proposer.sh: line 1: 12248 Terminated              python3 ../../cl.py proposers $1 $2
./client.sh: line 1: 12603 Terminated              python3 ../../cl.py clients $1 $2
./client.sh: line 1: 12611 Terminated              python3 ../../cl.py clients $1 $2
./proposer.sh: line 1: 12247 Terminated              python3 ../../cl.py proposers $1 $2
./learner.sh: line 1: 12208 Terminated              python3 ../../cl.py learners $1 $2
Test 1 - Learners learned the same set of values in total order
  > OK
Test 2 - Values learned were actually proposed
  > OK
Test 3 - Learners learned every value that was sent by some client
  > OK

```
### Catch up

```
$ ./run_catch_up.sh paxos 3000 && ./check_all.sh 
starting acceptors...
starting learner 1...
starting proposers...
waiting to start clients
starting client 1...
starting learners 2...
starting client 2...
./acceptor.sh: line 1: 13404 Terminated              python3 ../../cl.py acceptors $1 $2
./client.sh: line 1: 13880 Terminated              python3 ../../cl.py clients $1 $2
./learner.sh: line 1: 13861 Terminated              python3 ../../cl.py learners $1 $2
./client.sh: line 1: 13841 Terminated              python3 ../../cl.py clients $1 $2
./acceptor.sh: line 1: 13406 Terminated              python3 ../../cl.py acceptors $1 $2
./acceptor.sh: line 1: 13407 Terminated              python3 ../../cl.py acceptors $1 $2
./learner.sh: line 1: 13458 Terminated              python3 ../../cl.py learners $1 $2
./proposer.sh: line 1: 13540 Terminated              python3 ../../cl.py proposers $1 $2
./proposer.sh: line 1: 13541 Terminated              python3 ../../cl.py proposers $1 $2
Test 1 - Learners learned the same set of values in total order
  > OK
Test 2 - Values learned were actually proposed
  > OK
Test 3 - Learners learned every value that was sent by some client
  > OK

```
### 2 acceptors
```
$  ./run_2acceptor.sh paxos 3000 && ./check_all.sh 
starting acceptors...
starting learners...
starting proposers...
waiting to start clients
starting clients...
./learner.sh: line 1: 20559 Terminated              python3 ../../cl.py learners $1 $2
./acceptor.sh: line 1: 20520 Terminated              python3 ../../cl.py acceptors $1 $2
./client.sh: line 1: 20792 Terminated              python3 ../../cl.py clients $1 $2
./acceptor.sh: line 1: 20521 Terminated              python3 ../../cl.py acceptors $1 $2
./client.sh: line 1: 20791 Terminated              python3 ../../cl.py clients $1 $2
./learner.sh: line 1: 20558 Terminated              python3 ../../cl.py learners $1 $2
./proposer.sh: line 1: 20595 Terminated              python3 ../../cl.py proposers $1 $2
./proposer.sh: line 1: 20596 Terminated              python3 ../../cl.py proposers $1 $2
Test 1 - Learners learned the same set of values in total order
  > OK
Test 2 - Values learned were actually proposed
  > OK
Test 3 - Learners learned every value that was sent by some client
  > OK

```
Everything good!


### 1 acceptor

```
$ ./run_1acceptor.sh paxos 3000 && ./check_all.sh 
starting acceptors...
starting learners...
starting proposers...
waiting to start clients
starting clients...
./learner.sh: line 1: 16621 Terminated              python3 ../../cl.py learners $1 $2
./learner.sh: line 1: 16622 Terminated              python3 ../../cl.py learners $1 $2
./acceptor.sh: line 1: 16598 Terminated              python3 ../../cl.py acceptors $1 $2
./client.sh: line 1: 16872 Terminated              python3 ../../cl.py clients $1 $2
./client.sh: line 1: 16873 Terminated              python3 ../../cl.py clients $1 $2
./proposer.sh: line 1: 16669 Terminated              python3 ../../cl.py proposers $1 $2
./proposer.sh: line 1: 16668 Terminated              python3 ../../cl.py proposers $1 $2
Test 1 - Learners learned the same set of values in total order
  > OK
Test 2 - Values learned were actually proposed
  > OK
Test 3 - Learners learned every value that was sent by some client
  > Failed!
```
If `Failed` since there is no quorum, as double check it follows the output from the two learners

```
//learn1
```
```
//learn2
```
Booth are empty, as expected

### Leader Election
This is how my leader election protocols work:

- in the beginning, each `Proposers` elect itself as a leader and send `PHASE_1L` with their id as `leader_id`
- upon received `PHASE_1L`, a proposer checks if the received id is bigger than it's `leader_id`, if so it updates it. In this way the proposer with the biggest `id` will be always the leader

In the meantime, each `leader` pings the other proposers. They keep tracks of the last time they receive a ping and if enough time is elapsed the leader is considered dead and a new one is elected.

Since it may happen that two or more proposers think they are the leader at the same time, the `c_rnd` of `PHASE_1A` directly depends on the proposer `id` so only the biggest one will eventually decide.

When a proposer is a leader it starts proposing from instance `1`, the first one. If in that instance a value was already decided then the current `c_rnd` will be smaller or equal to the proposers' instance `v_rnd`. With normal paxos, there is nothing we can do.

In my protocol, when a proposer sees that a received `PHASE_1A` `c_rnd` is not bigger than the current `rnd` it sends a message, `PHASE_1C`, back to the proposers with the current instance `v_rnd`. In this way, the leader knows which `c_rnd` should use, obviously `v_rnd + 1`, to trigger the paxos instance.

This will continue until no `PHASE_1C` from the acceptors is received, meaning we have finally reached a new instance.

### Catch up
Catch up is super easy thanks to the previous implementation. When a `Learner` spawns it asks all the decided values to the leader and it prints them again while keeping them ordered by the instance id. 
