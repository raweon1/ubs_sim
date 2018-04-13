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

    def send_frame(self, receiver_address: str, frame: Frame,
                   extra_bits: int = 0, traffic_class: int = None) -> Sending:
        """
        call to send a frame from this node to receiver_address
        :param receiver_address:
        :param frame:
        :param extra_bits:
        :param traffic_class: traffic class in which this frame is send (will be saved in frame), if not specified
        frame.priority is used. important for UBS
        :return: Sending object
        """
        frame.hop += 1
        # Zeitpunkt zu dem der Frame zum ersten mal gesendet wird
        if traffic_class is not None:
            frame.traffic_class = traffic_class
        else:
            frame.traffic_class = frame.priority
        sending_object: Sending = self.env.send_frame(self.address, receiver_address, frame, extra_bits)
        return sending_object

    def get_data(self) -> list((list, str)):
        """
        returns a list of 2 tuples. each tuple contains a list of dicts (table) and a str (name of the table)
        """
        pass


class Listener(Node):
    def __init__(self, env: SimulationEnvironment, address: str, monitor: bool = False):
        super(Listener, self).__init__(env, address, False)

    def on_frame_received(self, frame: Frame, sender):
        self.env.sim_print("received frame")
