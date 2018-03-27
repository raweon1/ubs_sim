from collections import defaultdict


class Path(object):
    def __init__(self, *node_addresses: str):
        """
        important: a path has to be a tree structure.
        :param node_addresses: addresses of nodes on this path
        """
        self.path_dict = defaultdict(list)
        self.append_path(*node_addresses)

    def append_path(self, *node_addresses: str):
        """
        can be used to generate multiple paths - multicasting
        :param node_addresses: addresses of nodes on this path
        """
        current_node = None
        for node_address in node_addresses:
            if current_node is not None:
                if node_address not in self.path_dict[current_node]:
                    self.path_dict[current_node].append(node_address)
            current_node = node_address

    def __getitem__(self, node_address: str) -> list:
        """
        :param node_address: sending address to check
        :return: list of addresses of all following nodes on this path
        """
        return self.path_dict[node_address]

    def __str__(self):
        return str(self.path_dict)
