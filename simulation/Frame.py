from simulation import Flow


class Frame(object):
    def __init__(self, frame_id: int, flow: Flow, payload: int, priority: int, header: int = 26):
        """
        :param frame_id:
        :param flow:
        :param payload: in byte
        :param priority: 0-7
        :param header:
        """
        self.id = frame_id
        self.payload = payload
        self.priority = priority
        self.header = header
        self.flow = flow

        # value which stores the last traffic class used to send this frame (UBS needs this)
        self.traffic_class = priority
        self.start_time = -1
        self.delays = dict()

    def on_hop(self, sender_address: str, receiver_address: str, time: int):
        # last receiver
        if receiver_address not in self.flow.path.path_dict:
            self.delays[receiver_address] = time - self.start_time

    def __len__(self):
        return self.payload + self.header

    def __str__(self):
        return "_".join(("frame", str(self.id), str(self.__len__()), "flow", str(self.flow.id)))
