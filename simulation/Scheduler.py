from simulation.Core import SimulationEnvironment
from simulation.PriorityMap import PriorityMap
from simulation.Frame import Frame
from simulation.Node import Node
from simpy import Interrupt

from collections import deque, defaultdict


class Scheduler(object):
    def __init__(self, env: SimulationEnvironment, bandwidth: int, priority_map: PriorityMap, monitor: bool = False):
        self.env = env
        self.bandwidth = bandwidth
        self.egress_process = None
        self.priority_map = priority_map
        self.monitor = monitor

    def peek_frame(self):
        pass

    def append_frame(self, frame: Frame, sender: Node):
        pass

    def drop_frame(self, frame: Frame, sender: Node):
        pass

    def start_transmission(self, frame: Frame):
        pass

    def pause_transmission(self, frame: Frame):
        pass

    def end_transmission(self, frame: Frame):
        pass

    def get_data(self):
        pass


class UBSScheduler(Scheduler):
    def __init__(self, env: SimulationEnvironment, bandwidth: int,
                 priority_map: PriorityMap, mode: str, monitor: bool = False):
        """
        :param env:
        :param bandwidth:
        :param priority_map:
        :param mode: should be "LRQ" or "TBE"
        :param monitor:
        """
        super(UBSScheduler, self).__init__(env, bandwidth, priority_map, monitor)
        self.mode = mode

        self.data = dict()
        self.sleep_event = env.event()

        self.pseudo_queues = defaultdict(deque)
        self.shaped_queues = defaultdict(deque)
        self.process_shaped_queues = dict()
        self.process_shaped_queues_state = dict()

    def get_data(self) -> list:
        result = list()
        for frame_id, frame_dict in self.data.items():
            result.append(frame_dict)
        return result

    def end_transmission(self, frame: Frame):
        for traffic_class, queue in reversed(sorted(self.pseudo_queues.items())):
            if frame in queue:
                queue.remove(frame)
                if self.monitor:
                    self.data[frame.id]["forwarding_time"] = self.env.now
                    self.data[frame.id]["nodal_delay"] = self.env.now - self.data[frame.id]["arrival_time"]
                    self.data[frame.id]["queue_delay"] = self.data[frame.id]["nodal_delay"] - self.data[frame.id][
                        "transmission_time"]
                break

    def peek_frame(self):
        for traffic_class, queue in reversed(sorted(self.pseudo_queues.items())):
            if queue.__len__() > 0:
                return queue[0]
        return None

    def append_frame(self, frame: Frame, sender: Node):
        # each traffic class has a set of shaped queues for each ingress port
        # each traffic class has one pseudo queue
        traffic_class: int = self.priority_map[frame.priority]
        shaped_queue_index: str = "-".join((str(traffic_class), sender.address))

        # gets the pseudo_queue associated to this traffic_class; if there is none it is created
        pseudo_queue: deque = self.pseudo_queues[traffic_class]
        # gets the shaped_queue associated to this traffic_class and sender; if there is none it is created
        shaped_queue: deque = self.shaped_queues[shaped_queue_index]

        # add the frame to the shaped_queue
        shaped_queue.append(frame)
        # add frame to data
        if self.monitor:
            frame_dict = {"mode": self.mode,
                          "frame_id": frame.id, "flow_id": frame.flow.id, "frame_len": frame.__len__(),
                          "frame_priority": frame.priority,
                          "arrival_time": self.env.now, "shaped_queue": shaped_queue_index,
                          "transmission_time": frame.__len__() * 8 / self.bandwidth,
                          "forwarding_time": "", "nodal_delay": "", "queue_delay": ""}
            if frame.id in self.data:
                raise RuntimeError("frame id not unique")
            self.data[frame.id] = frame_dict

        # if there is no process for this shaped_queue, create one
        if shaped_queue_index not in self.process_shaped_queues:
            if self.mode == "tbe":
                self.process_shaped_queues[shaped_queue_index] = self.env.process(
                    self.process_shaped_queue_tbe(shaped_queue, pseudo_queue, shaped_queue_index))
            else:
                self.process_shaped_queues[shaped_queue_index] = self.env.process(
                    self.process_shaped_queue_lrq(shaped_queue, pseudo_queue, shaped_queue_index))
            # state of this process, True = sleeping, False = not sleeping
            self.process_shaped_queues_state[shaped_queue_index] = False

        # if process is sleeping, interrupt
        if self.process_shaped_queues_state[shaped_queue_index]:
            self.process_shaped_queues[shaped_queue_index].interrupt("new frame")

    def pseudo_queue_append(self, pseudo_queue: deque, frame: Frame):
        pseudo_queue.append(frame)
        self.egress_process.interrupt("new frame")

    def process_shaped_queue_lrq(self, shaped_queue: deque, pseudo_queue: deque, shaped_queue_index: str):
        state = defaultdict(int)
        while True:
            if shaped_queue.__len__() > 0:
                frame: Frame = shaped_queue.popleft()
                frame_bit_len = frame.__len__() * 8
                flow_index = frame.flow.id
                time = state[flow_index]
                if not self.env.now >= time:
                    yield self.env.timeout(time - self.env.now)
                self.pseudo_queue_append(pseudo_queue, frame)
                state[flow_index] = self.env.now + (frame_bit_len / frame.flow.leaky_rate)
            else:
                try:
                    self.process_shaped_queues_state[shaped_queue_index] = True
                    yield self.sleep_event
                except Interrupt:
                    self.process_shaped_queues_state[shaped_queue_index] = False

    def process_shaped_queue_tbe(self, shaped_queue: deque, pseudo_queue: deque, pseudo_queue_index: str):
        time_state = defaultdict(int)
        burst_state = dict()
        while True:
            if shaped_queue.__len__() > 0:
                frame: Frame = shaped_queue.popleft()
                frame_bit_len = frame.__len__() * 8
                flow_index = frame.flow.id
                leaky_rate = frame.flow.leaky_rate
                burstiness = frame.flow.burstiness * 8
                time = time_state[flow_index]
                try:
                    burst = burst_state[flow_index]
                except KeyError:
                    burst_state[flow_index] = burstiness
                    burst = burst_state[flow_index]
                if not burst + (self.env.now - time) * leaky_rate >= frame_bit_len:
                    yield self.env.timeout((frame_bit_len - (burst + (self.env.now - time) * leaky_rate)) / leaky_rate)
                self.pseudo_queue_append(pseudo_queue, frame)
                burst_state[flow_index] = min(burstiness, burst + (self.env.now - time) * leaky_rate) - frame_bit_len
                time_state[flow_index] = self.env.now
            else:
                try:
                    self.process_shaped_queues_state[pseudo_queue_index] = True
                    yield self.sleep_event
                except Interrupt:
                    self.process_shaped_queues_state[pseudo_queue_index] = False
