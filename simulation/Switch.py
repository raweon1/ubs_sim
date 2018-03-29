from simulation.Frame import Frame
from simulation.Path import Path
from simulation.Node import Node
from simulation.Core import SimulationEnvironment, Sending
from simulation.Scheduler import UBSScheduler, UBSScheduler2, Scheduler
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

    def get_data(self) -> list((list, str)):
        if self.monitor:
            frame_result = list()
            queue_result = list()
            for receiver_address, scheduler in self.schedulers.items():
                frame_data, queue_data = scheduler.get_data()
                for frame_dict in frame_data:
                    tmp_dict = {"switch_address": self.address, "egress_address": receiver_address}
                    tmp_dict.update(frame_dict)
                    frame_result.append(tmp_dict)
                for queue_dict in queue_data:
                    tmp_dict = {"switch_address": self.address, "egress_address": receiver_address}
                    tmp_dict.update(queue_dict)
                    queue_result.append(tmp_dict)
            return [(frame_result, "UBS_Switch_Frame"), (queue_result, "UBS_Switch_Queue")]
        else:
            return None

    def egress_append_frame(self, frame: Frame, sender: Node, scheduler_class: Scheduler.__class__):
        path: Path = frame.flow.path
        # multicast, frame might need to be added to multiple egress schedulers
        receiver_addresses: list = path[self.address]

        for receiver_address in receiver_addresses:
            # egress does not exist: create scheduler for that egress port
            if receiver_address not in self.schedulers:
                bandwidth = self.env.topology.bandwidth(self.address, receiver_address)
                scheduler = scheduler_class(self.env, bandwidth, self.priority_map, self.mode, self.monitor)
                process = self.env.process(self.process_send(scheduler, receiver_address))
                scheduler.egress_process = process
                self.schedulers[receiver_address] = scheduler
                self.processes[receiver_address] = process
            # add frame to the scheduler of that egress port
            self.schedulers[receiver_address].append_frame(frame, sender)

    def on_frame_received(self, frame: Frame, sender: Node):
        self.egress_append_frame(frame, sender, UBSScheduler)

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
                        sending_object = self.send_frame(
                            receiver_address, frame, traffic_class=self.priority_map[frame.priority])
            except Interrupt:
                pass


class UBSSwitch2(UBSSwitch):
    def __init__(self, env: SimulationEnvironment, address: str, priority_map: PriorityMap, mode: str = "lrq",
                 monitor: bool = False):
        super(UBSSwitch2, self).__init__(env, address, priority_map, mode, monitor)

    def on_frame_received(self, frame: Frame, sender: Node):
        self.egress_append_frame(frame, sender, UBSScheduler2)
