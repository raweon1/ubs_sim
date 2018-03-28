from simulation.Node import Node
from simulation.Flow import Flow
from simulation.Frame import Frame
from simulation.Core import SimulationEnvironment
from simpy import Event, Process, Interrupt
from collections import deque


class Talker(Node):
    def __init__(self, env: SimulationEnvironment, address: str, monitor: bool = False):
        """
        Talker which can hold multiple flows. Each flow will generate Frames in a leaky bucket pattern with
        leaky rate from the flow. These Frames are collected in a single queue and send into the network one at a time
        :param env:
        :param address:
        :param monitor:
        """
        super(Talker, self).__init__(env, address, monitor)
        self.queue = deque()
        self.sleeping: bool = False
        self.sleep_event: Event = env.event()
        self.send_process: Process = env.process(self.process_send_frame())

        self.data = list()

    def get_data(self) -> (list, str):
        if self.monitor:
            result = list()
            for frame in self.data:
                if frame.delays.__len__() == 0:
                    frame_dict = {"frame_id": frame.id, "flow_id": frame.flow.id,
                                  "frame_len": frame.__len__(), "frame_priority": frame.priority,
                                  "sender": self.address, "receiver": "",
                                  "start_time": frame.start_time, "arrival_time": "", "delay": ""}
                    result.append(frame_dict)
                else:
                    for receiver_address, delay in frame.delays.items():
                        frame_dict = {"frame_id": frame.id, "flow_id": frame.flow.id,
                                      "frame_len": frame.__len__(), "frame_priority": frame.priority,
                                      "sender": self.address, "receiver": receiver_address,
                                      "start_time": frame.start_time, "arrival_time": frame.start_time + delay,
                                      "delay": delay}
                        result.append(frame_dict)
            return result, "talker"
        else:
            return None, None

    def add_flow(self, flow: Flow, priority: int, payload_generator=None):
        """
        Adds a flow to this Talker. This will create a process which creates frames this talker will send
        :param flow: flow for which frames are generated, this also provides the leaky_rate for the frame generation
        :param priority: priority of the frames
        :param payload_generator: payload of the frames
        """
        self.env.process(self.process_flow_create_frame(flow, priority, payload_generator))

    def process_send_frame(self):
        """
        process which sends frames generated by process_flow_create_frame
        """
        while True:
            if self.queue.__len__() > 0:
                frame = self.queue.popleft()
                if self.monitor:
                    self.data.append(frame)
                receiver_address = frame.flow.path[self.address][0]
                sending_object = self.send_frame(receiver_address, frame)
                yield sending_object.process
                self.env.sim_print("send frame")
            else:
                self.sleeping = True
                try:
                    yield self.sleep_event
                except Interrupt:
                    self.sleeping = False

    def process_flow_create_frame(self, flow: Flow, priority: int, payload_generator):
        """
        process which creates frames in a leaky bucket pattern with leaky_rate from the flow
        :param flow:
        :param priority:
        :param payload_generator:
        """
        while True:
            frame = Frame(self.env.frame_id(), flow, payload_generator.__next__(), priority)
            # frame = Frame(self.env.frame_id(), flow, 1500, priority)
            self.queue.append(frame)
            if self.sleeping:
                self.sleeping = False
                self.send_process.interrupt("new frame")
            yield self.env.timeout(frame.__len__() * 8 / flow.leaky_rate)


class TokenBucketTalker(Node):
    def __init__(self, env: SimulationEnvironment, address: str, flow: Flow, priority: int,
                 payload_generator, time_generator, monitor: bool = False):
        """
        Talker which creates frames of a specified flow in a specific pattern (e.g. exp), puts them in a queue
        and sends them in to the network. The queue is Token Bucket shaped, leaky rate and burstiness are defined by
        the flow.
        """
        super(TokenBucketTalker, self).__init__(env, address, monitor)
        self.flow = flow
        self.priority = priority

        self.queue = deque()
        self.sleeping: bool = False
        self.sleep_event: Event = env.event()
        self.send_process: Process = env.process(self.process_send_frame())
        self.frame_process: Process = env.process(
            self.process_flow_create_frame(flow, priority, payload_generator, time_generator))
        self.data = list()

    def get_data(self) -> (list, str):
        if self.monitor:
            result = list()
            for frame in self.data:
                if frame.delays.__len__() == 0:
                    frame_dict = {"frame_id": frame.id, "flow_id": frame.flow.id,
                                  "frame_len": frame.__len__(), "frame_priority": frame.priority,
                                  "sender": self.address, "receiver": "",
                                  "start_time": frame.start_time, "arrival_time": "", "delay": ""}
                    result.append(frame_dict)
                else:
                    for receiver_address, delay in frame.delays.items():
                        frame_dict = {"frame_id": frame.id, "flow_id": frame.flow.id,
                                      "frame_len": frame.__len__(), "frame_priority": frame.priority,
                                      "sender": self.address, "receiver": receiver_address,
                                      "start_time": frame.start_time, "arrival_time": frame.start_time + delay,
                                      "delay": delay}
                        result.append(frame_dict)
            return result, "talker"
        else:
            return None, None

    def process_send_frame(self):
        """
        process which sends frames generated by process_flow_create_frame in a token bucket pattern.
        leaky rate and burstiness are defined by the flow
        """
        leaky_rate = self.flow.leaky_rate
        burstiness = self.flow.burstiness * 8
        # burst = remaining burst
        burst = burstiness

        time = self.env.now
        while True:
            if self.queue.__len__() > 0:
                frame = self.queue.popleft()
                frame_bit_len = frame.__len__() * 8
                if self.monitor:
                    self.data.append(frame)
                receiver_address = frame.flow.path[self.address][0]

                if not burst + (self.env.now - time) * leaky_rate >= frame_bit_len:
                    yield self.env.timeout((frame_bit_len - (burst + (self.env.now - time) * leaky_rate)) / leaky_rate)
                burst = min(burstiness, burst + (self.env.now - time) * leaky_rate) - frame_bit_len
                time = self.env.now

                sending_object = self.send_frame(receiver_address, frame)
                yield sending_object.process
                self.env.sim_print("send frame")
            else:
                self.sleeping = True
                try:
                    yield self.sleep_event
                except Interrupt:
                    self.sleeping = False

    def process_flow_create_frame(self, flow: Flow, priority: int, payload_generator, time_generator):
        """
        process which creates a frame, puts it in a token bucket shaped queue and waits time_generator.__next__() time
        until a new frame is created
        :param flow: flow for which frame are created, also used for the token bucket shaper in process_send_frame
        :param priority: priority for this flow
        :param payload_generator: generator which generates the size of frames (in byte),
            values created by this generator have to be > 0 and should be < flow.burstiness;
            values should not exceed ~1500 bytes (max. frame size in ethernet)
        :param time_generator: generator which generates the time until the next frame is created in microsecond,
            values created by this generator have to be > 0.

        Meine Gedanken, mögen falsch sein:
        NOTE: because send_frame_process is token bucket shaped with leaky_rate r,
            generating more bit (each frame can have different sizes) than can be transmitted via r will make this
            talker behave like a leaky bucket shaped talker.

        NOTE2: Assume we have a frame time distribution with an expected value of x
            and a frame size distribution with an expected value of y
            and a leaky_rate r:
            To leak a frame to the network we need (y * 8 / r)µs and the next frame arrives in x µs
            => x >= (y * 8 / r) ; otherwise the queue will overflow (frames come faster than we can send them)
            -> we send frames in a leaky bucket pattern
        """
        while True:
            frame = Frame(self.env.frame_id(), flow, payload_generator.__next__(), priority)
            # frame = Frame(self.env.frame_id(), flow, 1500, priority)
            self.queue.append(frame)
            if self.sleeping:
                self.sleeping = False
                self.send_process.interrupt("new frame")
            yield self.env.timeout(time_generator.__next__())
