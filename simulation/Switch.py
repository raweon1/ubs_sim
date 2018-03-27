from simulation.Frame import Frame
from simulation.Path import Path
from simulation.Node import Node
from simulation.Core import SimulationEnvironment, Sending
from simulation.Scheduler import UBSScheduler
from simulation.PriorityMap import PriorityMap

from simpy import Interrupt


class Switch(Node):
    def __init__(self, env: SimulationEnvironment, address: str, priority_map: PriorityMap, monitor: bool = False):
        super(Switch, self).__init__(env, address, monitor)
        self.priority_map = priority_map

    def on_frame_received(self, frame: Frame, sender: Node):
        path: Path = frame.flow.path
        receiver_addresses: list = path[self.address]


class UBSSwitch(Switch):
    def __init__(self, env: SimulationEnvironment, address: str, priority_map: PriorityMap, mode: str = "lrq",
                 monitor: bool = False):
        super(UBSSwitch, self).__init__(env, address, priority_map, monitor)
        self.mode = mode
        self.schedulers = dict()
        self.processes = dict()

        self.sleep_event = env.event()

    def get_data(self) -> (list, str):
        if self.monitor:
            result = list()
            for receiver_address, scheduler in self.schedulers.items():
                for frame_dict in scheduler.get_data():
                    tmp_dict = {"switch_address": self.address, "egress_address": receiver_address}
                    tmp_dict.update(frame_dict)
                    result.append(tmp_dict)
            return result, "switch"
        else:
            return None, None

    def on_frame_received(self, frame: Frame, sender: Node):
        path: Path = frame.flow.path
        receiver_addresses: list = path[self.address]

        for receiver_address in receiver_addresses:
            if receiver_address not in self.schedulers:
                bandwidth = self.env.topology.bandwidth(self.address, receiver_address)
                scheduler = UBSScheduler(self.env, bandwidth, self.priority_map, self.mode, self.monitor)
                process = self.env.process(self.process_send(scheduler, receiver_address))
                scheduler.egress_process = process
                self.schedulers[receiver_address] = scheduler
                self.processes[receiver_address] = process

            self.schedulers[receiver_address].append_frame(frame, sender)

    def process_send(self, scheduler: UBSScheduler, receiver_address: str):
        frame: Frame = None
        sending_object: Sending = None
        while True:
            try:
                if frame is not None:
                    if sending_object.process.processed:
                        frame = None
                        sending_object = None
                    else:
                        scheduler.start_transmission(frame)
                        yield sending_object.process
                        scheduler.end_transmission(frame)
                else:
                    frame = scheduler.peek_frame()
                    if frame is None:
                        yield self.sleep_event
                    else:
                        sending_object = self.send_frame(receiver_address, frame)
            except Interrupt:
                pass
