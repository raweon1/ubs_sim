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
        :param mode: should be "lrq", "tbe", "shapeless"; lrq is selected when mode is neither
        :param monitor:
        """
        super(UBSScheduler, self).__init__(env, bandwidth, priority_map, monitor)
        self.mode = mode

        self.data = dict()
        self.shaped_queue_data = list()
        self.pseudo_queue_data = list()

        self.sleep_event = env.event()

        self.pseudo_queues = defaultdict(deque)
        self.shaped_queues = defaultdict(deque)
        self.process_shaped_queues = dict()
        # shaped queue sleeping or not
        self.process_shaped_queues_state = dict()

    def get_data(self) -> (list, list):
        result = list()
        for frame_id, frame_dict in self.data.items():
            result.append(frame_dict)
        return result, self.shaped_queue_data + self.pseudo_queue_data

    def end_transmission(self, frame: Frame):
        for traffic_class, pseudo_queue in reversed(sorted(self.pseudo_queues.items())):
            if frame in pseudo_queue:
                pseudo_queue.remove(frame)
                if self.monitor:
                    frame_dict = self.data[frame.id]
                    frame_dict["forwarding_time"] = self.env.now
                    frame_dict["nodal_delay"] = self.env.now - frame_dict["arrival_time"]
                    frame_dict["queue_delay"] = frame_dict["nodal_delay"] - frame_dict["transmission_time"]
                    frame_dict["shaped_queue_delay"] = frame_dict["pseudo_queue_time"] - frame_dict["arrival_time"]
                    frame_dict["pseudo_queue_delay"] = frame_dict["queue_delay"] - frame_dict["shaped_queue_delay"]

                    since = 0 if self.pseudo_queue_data.__len__() == 0 else self.pseudo_queue_data[-1]["until"]
                    self.pseudo_queue_data.append({"queue_type": "pseudo", "queue": traffic_class,
                                                   "since": since, "until": self.env.now,
                                                   "frames": pseudo_queue.__len__(),
                                                   "byte_length": self.get_queue_byte_len(pseudo_queue)})
                break

    def peek_frame(self):
        for traffic_class, queue in reversed(sorted(self.pseudo_queues.items())):
            if queue.__len__() > 0:
                return queue[0]
        return None

    @staticmethod
    def get_shaped_queue_index(frame: Frame, traffic_class: int, egress_address: str) -> str:
        # frame not used here
        return "-".join((str(traffic_class), egress_address))

    @staticmethod
    def get_queue_byte_len(queue: deque):
        byte_len = 0
        for frame in queue:
            byte_len += frame.__len__()
        return byte_len

    def append_frame(self, frame: Frame, sender: Node):
        # each traffic class has a set of shaped queues for each ingress port
        # each traffic class has one pseudo queue
        traffic_class: int = self.priority_map[frame.priority]
        shaped_queue_index: str = self.get_shaped_queue_index(frame, traffic_class, sender.address)

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
                          "frame_priority": frame.priority, "shaped_queue": shaped_queue_index,
                          "arrival_time": self.env.now, "pseudo_queue_time": "", "forwarding_time": "",
                          "transmission_time": frame.__len__() * 8 / self.bandwidth,
                          "nodal_delay": "", "queue_delay": "", "shaped_queue_delay": "", "pseudo_queue_delay": ""}
            if frame.id in self.data:
                raise RuntimeError("frame id not unique")
            self.data[frame.id] = frame_dict

            since = 0 if self.shaped_queue_data.__len__() == 0 else self.shaped_queue_data[-1]["until"]
            self.shaped_queue_data.append({"queue_type": "shaped", "queue": shaped_queue_index,
                                           "since": since, "until": self.env.now, "frames": shaped_queue.__len__(),
                                           "byte_length": self.get_queue_byte_len(shaped_queue)})

        # if there is no process for this shaped_queue, create one
        if shaped_queue_index not in self.process_shaped_queues:
            if self.mode == "tbe":
                self.process_shaped_queues[shaped_queue_index] = self.env.process(
                    self.process_shaped_queue_tbe(shaped_queue, pseudo_queue, shaped_queue_index,
                                                  str(traffic_class)))
            elif self.mode == "shapeless":
                self.process_shaped_queues[shaped_queue_index] = self.env.process(
                    self.process_shaped_queue_shapeless(shaped_queue, pseudo_queue, shaped_queue_index,
                                                        str(traffic_class)))
            else:
                self.process_shaped_queues[shaped_queue_index] = self.env.process(
                    self.process_shaped_queue_lrq(shaped_queue, pseudo_queue, shaped_queue_index,
                                                  str(traffic_class)))
            # state of this process, True = sleeping, False = not sleeping
            self.process_shaped_queues_state[shaped_queue_index] = False

        # if process is sleeping, interrupt
        if self.process_shaped_queues_state[shaped_queue_index]:
            self.process_shaped_queues[shaped_queue_index].interrupt("new frame")

    def pseudo_queue_append(self, shaped_queue_index: str, shaped_queue: deque,
                            pseudo_queue: deque, pseudo_queue_index: str, frame: Frame):
        pseudo_queue.append(frame)
        if self.monitor:
            self.data[frame.id]["pseudo_queue_time"] = self.env.now

            since = 0 if self.shaped_queue_data.__len__() == 0 else self.shaped_queue_data[-1]["until"]
            self.shaped_queue_data.append({"queue_type": "shaped", "queue": shaped_queue_index,
                                           "since": since, "until": self.env.now, "frames": shaped_queue.__len__(),
                                           "byte_length": self.get_queue_byte_len(shaped_queue)})

            since = 0 if self.pseudo_queue_data.__len__() == 0 else self.pseudo_queue_data[-1]["until"]
            self.pseudo_queue_data.append({"queue_type": "pseudo", "queue": pseudo_queue_index,
                                           "since": since, "until": self.env.now, "frames": pseudo_queue.__len__(),
                                           "byte_length": self.get_queue_byte_len(pseudo_queue)})
        self.egress_process.interrupt("new frame")

    def process_shaped_queue_lrq(self, shaped_queue: deque, pseudo_queue: deque,
                                 shaped_queue_index: str, pseudo_queue_index: str):
        state = defaultdict(int)
        while True:
            if shaped_queue.__len__() > 0:
                frame: Frame = shaped_queue.popleft()
                frame_bit_len = frame.__len__() * 8
                flow_index = frame.flow.id
                time = state[flow_index]
                if not self.env.now >= time:
                    yield self.env.timeout(time - self.env.now)
                self.pseudo_queue_append(shaped_queue_index, shaped_queue, pseudo_queue, pseudo_queue_index, frame)
                state[flow_index] = self.env.now + (frame_bit_len / frame.flow.leaky_rate)
            else:
                try:
                    self.process_shaped_queues_state[shaped_queue_index] = True
                    yield self.sleep_event
                except Interrupt:
                    self.process_shaped_queues_state[shaped_queue_index] = False

    def process_shaped_queue_tbe(self, shaped_queue: deque, pseudo_queue: deque,
                                 shaped_queue_index: str, pseudo_queue_index: str):
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
                    # print((frame_bit_len - (burst + (self.env.now - time) * leaky_rate)) / leaky_rate)
                    yield self.env.timeout((frame_bit_len - (burst + (self.env.now - time) * leaky_rate)) / leaky_rate)
                self.pseudo_queue_append(shaped_queue_index, shaped_queue, pseudo_queue, pseudo_queue_index, frame)
                burst_state[flow_index] = min(burstiness, burst + (self.env.now - time) * leaky_rate) - frame_bit_len
                # if burst_state[flow_index] < -10:
                #   print(round(burst_state[flow_index], 2))
                #   print("%f %f %f %f" % (burst, (self.env.now - time) * leaky_rate, frame_bit_len, frame_bit_len / 8))
                time_state[flow_index] = self.env.now
            else:
                try:
                    self.process_shaped_queues_state[shaped_queue_index] = True
                    yield self.sleep_event
                except Interrupt:
                    self.process_shaped_queues_state[shaped_queue_index] = False

    def process_shaped_queue_shapeless(self, shaped_queue: deque, pseudo_queue: deque,
                                       shaped_queue_index: str, pseudo_queue_index: str):
        # no shaping, frame is directly send to the pseudo_queue
        while True:
            if shaped_queue.__len__() > 0:
                frame: Frame = shaped_queue.popleft()
                self.pseudo_queue_append(shaped_queue_index, shaped_queue, pseudo_queue, pseudo_queue_index, frame)
            else:
                try:
                    self.process_shaped_queues_state[shaped_queue_index] = True
                    yield self.sleep_event
                except Interrupt:
                    self.process_shaped_queues_state[shaped_queue_index] = False

    def __len__(self):
        length = 0
        for queue in self.pseudo_queues:
            length += queue.__len__()
        for queue in self.shaped_queues:
            length += queue.__len__()
        return length


class UBSScheduler2(UBSScheduler):
    def __init__(self, env: SimulationEnvironment, bandwidth: int,
                 priority_map: PriorityMap, mode: str, monitor: bool = False):
        """
        undlike UBSScheduler UBSScheduler2 also uses the traffic class of the ingress node for the shaped_queue_index.
        this results in potentially more shaped queues
        """
        super(UBSScheduler2, self).__init__(env, bandwidth, priority_map, mode, monitor)

    @staticmethod
    def get_shaped_queue_index(frame: Frame, traffic_class: int, egress_address: str):
        return "-".join((str(traffic_class), egress_address, str(frame.traffic_class)))
