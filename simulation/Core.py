from simulation.Frame import Frame
from simpy import Environment, Process, Interrupt

from collections import defaultdict

import numpy as np


class Topology(object):
    def __init__(self, *nodes):
        """
        :type nodes: Node
        """
        self.nodes = dict()
        for node in nodes:
            self.nodes[node.address] = node
        self.link_dict = dict()

    def connect(self, address_a: str, address_b: str, bandwidth: int = 1000):
        """
        frames send between node address_a and node address_b are transmitted with bandwidth bandwidth
        :param address_a:
        :param address_b:
        :param bandwidth: in MegaBit / Second == Bit / MicroSecond; default = 1000 MegaBit / Second == 1 GigaBit/Second
        1 GigaBit / Second == 1000 MegaBit / Second == 1000 Bit / MicroSecond
        """
        self.link_dict[(address_a, address_b)] = bandwidth
        self.link_dict[(address_b, address_a)] = bandwidth

    def multi_connect(self, address_a: str, bandwidth: int = 1000, *address_bs: str):
        """
        connects address_a to all address_b with the same bandwidth bandwidth
        :param address_a:
        :param bandwidth: in MegaBit / Second == Bit / MicroSecond; default = 1000 MegaBit / Second == 1 GigaBit/Second
        1 GigaBit / Second == 1000 MegaBit / Second == 1000 Bit / MicroSecond
        :param address_bs:
        """
        for address_b in address_bs:
            self.connect(address_a, address_b, bandwidth)

    def bandwidth(self, address_a: str, address_b: str) -> int:
        """
        :param address_a:
        :param address_b:
        :return: bandwidth of the link between node address_a and node address_b
        in MegaBit / Second == Bit / MicroSecond
        """
        return self.link_dict[(address_a, address_b)]
            
    def __getitem__(self, address: str):
        """
        :param address: 
        :return: Node with address address
        """
        return self.nodes[address]


class Sending(object):
    def __init__(self, env, sender, receiver,
                 frame: Frame, extra_bits: int, bandwidth: int):
        """
        :type receiver: Node
        :type sender: Node
        :type env: SimulationEnvironment
        """
        self.env = env
        self.sender = sender
        self.receiver = receiver
        self.frame = frame
        self.bandwidth = bandwidth

        self.active = True
        self.start_time = env.now
        self.transmission_time = (frame.__len__() * 8 + extra_bits) / bandwidth

        self.process: Process = env.process(self.process_send_frame(sender, receiver, frame))

    def process_send_frame(self, sender, receiver, frame: Frame):
        while True:
            try:
                yield self.env.timeout(self.transmission_time)
                frame.on_hop(sender.address, receiver.address, self.env.now)
                receiver.push_frame(frame, sender)
                break
            except Interrupt:
                pass
            try:
                yield self.env.sleep_event
            except Interrupt:
                pass

    def interruptable(self) -> bool:
        remaining_time = self.env.now - self.start_time
        remaining_bits = remaining_time * self.bandwidth
        # todo replace 8 with min_preemption_bits/bytes
        if remaining_bits > 8:
            return True
        else:
            return False

    def pause(self):
        if self.active:
            remaining_time = self.env.now - self.start_time
            remaining_bits = remaining_time * self.bandwidth
            # todo replace 0 with preemption_penalty_bits/bytes
            remaining_bits += 0
            self.transmission_time = remaining_bits / self.bandwidth
            self.active = False
            self.process.interrupt("pause")

    def start(self):
        if not self.active:
            self.start_time = self.env.now
            self.active = True
            self.process.interrupt("start")


class SimulationEnvironment(Environment):

    id = dict()

    def __init__(self, name: str = "no_name", seed: int = None, verbose: bool = False, *args, **kwargs):
        """
        :param topology: Topology of the Network
        :param name: Name of this specific Simulation
        :param seed: Seed for the random generator
        """
        super(SimulationEnvironment, self).__init__(*args, **kwargs)
        self.topology = None

        self.verbose = verbose
        self.name = name
        try:
            self.id = SimulationEnvironment.id[name]
            SimulationEnvironment.id[name] += 1
        except KeyError:
            self.id = 1
            SimulationEnvironment.id[name] = 2
        self.random = np.random.RandomState(seed=seed)
        self.seed = seed if seed is not None else ""

        self.next_frame_id = 0

        self.sleep_event = self.event()

    def get_data(self) -> dict:
        results = defaultdict(list)
        for node_address, node in self.topology.nodes.items():
            if node.monitor:
                node_results = node.get_data()
                for node_result_list, dict_format in node_results:
                    for frame_dict in node_result_list:
                        tmp_dict = {"sim_name": self.name, "sim_id": self.id, "seed": self.seed}
                        tmp_dict.update(frame_dict)
                        results[dict_format].append(tmp_dict)
        return results

    def sim_print(self, msg):
        if self.verbose:
            print("%0.2f: %s" % (self.now, msg))

    def frame_id(self):
        """
        :return: unique id for a frame of this specific Simulation
        """
        self.next_frame_id += 1
        return self.next_frame_id - 1

    def send_frame(self, sender_address: str, receiver_address: str, frame: Frame, extra_bits: int = 0) -> Sending:
        """
        sends the frame from node sender_address to node receiver_address
        :param sender_address:
        :param receiver_address:
        :param frame: frame to send
        :param extra_bits: extra bits to send with the frame; increases the time needed to send the frame
        :return: Sending object for this sending operation
        """
        sender = self.topology[sender_address]
        receiver = self.topology[receiver_address]
        bandwidth = self.topology.bandwidth(sender_address, receiver_address)
        return Sending(self, sender, receiver, frame, extra_bits, bandwidth)
