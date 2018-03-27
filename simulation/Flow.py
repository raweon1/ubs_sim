from simulation import Path


class Flow(object):
    def __init__(self, flow_id: int, path: Path, leaky_rate: float, burstiness: float = 0):
        """
        :param flow_id: id/index of this flow, this has to be unique
        :param path: Path for this flow
        :param leaky_rate: in bit / micro second = MegaBit / second
        :param burstiness: in byte
        """
        self.id = flow_id
        self.path = path
        self.leaky_rate = leaky_rate
        self.burstiness = burstiness
