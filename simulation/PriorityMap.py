
class PriorityMap(object):
    # number of available traffic classes x priority = traffic class
    # see 802.1Q page: 126
    map = [[0, 0, 0, 0, 0, 0, 0, 0],  # 1 traffic classes
           [0, 0, 0, 0, 1, 1, 1, 1],  # 2 traffic classes
           [0, 0, 0, 0, 1, 1, 2, 2],  # 3 traffic classes
           [0, 0, 1, 1, 2, 2, 3, 3],  # 4 traffic classes
           [0, 0, 1, 1, 2, 2, 3, 4],  # 5 traffic classes
           [1, 0, 2, 2, 3, 3, 4, 5],  # 6 traffic classes
           [1, 0, 2, 3, 4, 4, 5, 6],  # 7 traffic classes
           [1, 0, 2, 3, 4, 5, 6, 7]]  # 8 traffic classes

    def __init__(self, available_traffic_classes: int = 8):
        """
        Maps Frame priorities to traffic classes
        :param available_traffic_classes: how many traffic classes are supported. 1-8
        """
        self.available_traffic_classes = available_traffic_classes - 1

    # args = list of tuples of (priority, traffic_class)
    def map_priority_traffic_class(self, priority: int, traffic_class: int):
        """
        Maps a specific priority to a specific traffic class
        :param priority:
        :param traffic_class:
        """
        self.map[self.available_traffic_classes][priority] = traffic_class

    def get_traffic_class(self, priority):
        return self.map[self.available_traffic_classes][priority]

    def __getitem__(self, priority):
        """
        :param priority: priority
        :return: traffic class
        """
        return self.map[self.available_traffic_classes][priority]

    def __setitem__(self, priority_key, traffic_class_value):
        """
        Maps a specific priority to a specific traffic class
        :param priority_key:
        :param traffic_class_value:
        """
        self.map[self.available_traffic_classes][priority_key] = traffic_class_value
