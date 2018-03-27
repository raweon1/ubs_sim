from simulation.Core import SimulationEnvironment, Topology
from simulation.Talker import Talker
from simulation.Switch import UBSSwitch
from simulation.PriorityMap import PriorityMap
from simulation.Path import Path
from simulation.Flow import Flow
from simulation.Node import Listener
from simulation.Wrapper import simulate_multiple

import json


def foo():
    seed = 123456789
    while True:
        p = Path("talker", "switch", "listener")
        f = Flow(1, p, 500, 1500)
        f2 = Flow(2, p, 350, 1500)

        sim_env = SimulationEnvironment("test", seed)

        talker = Talker(sim_env, "talker", True)
        talker.add_flow(f, 1)
        talker.add_flow(f2, 5)

        p2 = Path("talker2", "switch", "listener")
        f3 = Flow(3, p2, 145, 1500)
        talker2 = Talker(sim_env, "talker2")
        talker2.add_flow(f3, 1)

        priority_map = PriorityMap(2)
        switch = UBSSwitch(sim_env, "switch", priority_map, "lrq", True)

        listener = Listener(sim_env, "listener")

        t = Topology(talker, talker2, switch, listener)
        sim_env.topology = t
        t.multi_connect("switch", 1000, "talker", "listener", "talker2")

        seed *= 2
        yield sim_env


simulate_multiple(foo(), 3, 100, "test")
