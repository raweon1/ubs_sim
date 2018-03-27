from simulation.Frame import Frame
from simulation.Core import SimulationEnvironment, Sending


class Node(object):
    def __init__(self, env: SimulationEnvironment, address: str, monitor: bool = False):
        self.env = env
        self.address = address
        self.monitor = monitor

    def on_frame_received(self, frame: Frame, sender):
        """
        called when a node receives a frame
        :param frame:
        :param sender: Node which send the frame
        :type sender: Node
        """
        pass

    def push_frame(self, frame: Frame, sender):
        """
        called by SimulationEnvironment to push a frame to this node
        :param frame:
        :param sender: Node which send the frame
        :type sender: Node
        """
        self.on_frame_received(frame, sender)

    def send_frame(self, receiver_address: str, frame: Frame, extra_bits: int = 0) -> Sending:
        """
        call to send a frame from this node to receiver_address
        :param receiver_address:
        :param frame:
        :param extra_bits:
        :return: Sending object
        """
        # Zeitpunkt zu dem der Frame zum ersten mal gesendet wird
        if frame.start_time < 0:
            frame.start_time = self.env.now
        sending_object: Sending = self.env.send_frame(self.address, receiver_address, frame, extra_bits)
        return sending_object

    def get_data(self) -> (list, str):
        pass


class Listener(Node):
    def __init__(self, env: SimulationEnvironment, address: str, monitor: bool = False):
        super(Listener, self).__init__(env, address, False)

    def on_frame_received(self, frame: Frame, sender):
        self.env.sim_print("received frame")
