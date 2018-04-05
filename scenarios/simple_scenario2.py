from simulation.Core import SimulationEnvironment, Topology
from simulation.Talker import Talker, TokenBucketTalker, UnshapedTalker
from simulation.Switch import UBSSwitch, UBSSwitch2
from simulation.PriorityMap import PriorityMap
from simulation.Path import Path
from simulation.Flow import Flow
from simulation.Node import Listener
from simulation.Wrapper import simulate_multiple, simulate_multiple_multiple

import numpy as np
from sys import maxsize


def time_gen(leaky_rate, mean_frame_len, sim_env: SimulationEnvironment):
    rnd_state = sim_env.random
    mean = mean_frame_len * 8 / leaky_rate
    while True:
        yield rnd_state.exponential(mean)


def payload_gen(sim_env: SimulationEnvironment, mean):
    rnd = sim_env.random
    while True:
        yield round(rnd.uniform(2, mean * 2 - 2))


def foo(interleaved: bool, high_priority_leaky_rate, switch_mode):
    """
    Two Talker, three Flows. One Talker has 2 Flows with leaky_rate = high_priority_leaky_rate / 2 each
    Second Talker has 1 Flow with a lower priority and leaky_rate = 1 - high_priority_leaky_rate
    switch_mode = "lrq", "tbe", "shapeless"

    Creating a Scenario in a while True loop:
    1. Create SimulationEnvironment instance
    2. Define Path(s)
    3. Define Flow(s)
    4. Define Nodes
    5. Create Topology instance
    6. Set SimulationEnvironment.topology to Topology (5.)
    7. yield SimulationEnvironment

    optional: use a specific seed and change it before yield statement
    """

    seed = np.random.randint(maxsize)
    while True:
        # 1.
        sim_env = SimulationEnvironment("%s-%0.2f-%s" % (str(interleaved), high_priority_leaky_rate, switch_mode), seed)

        # 2.
        path1 = Path("talker1", "switch", "listener")
        path1.append_path("talker12", "switch", "listener")
        path2 = Path("talker2", "switch", "listener")
        # 3.
        bandwidth = 1000
        burstiness = 3000

        leaky_rate_high = (bandwidth * (high_priority_leaky_rate - 0)) / 2
        leaky_rate_low = bandwidth * ((1 - high_priority_leaky_rate) - 0)
        flow_high1 = Flow(1, path1, leaky_rate_high, burstiness)
        flow_high2 = Flow(2, path1, leaky_rate_high, burstiness)
        flow_low = Flow(3, path2, leaky_rate_low, burstiness)

        # 4.
        mean_payload = 750
        payload_generator = payload_gen(sim_env, mean_payload)

        talker1 = Talker(sim_env, "talker1", True)
        talker12 = Talker(sim_env, "talker12", True)
        if interleaved:
            if leaky_rate_high > 0:
                talker1.add_flow(flow_high1, 3, payload_generator)
                talker1.add_flow(flow_high2, 3, payload_generator)
        else:
            if leaky_rate_high > 0:
                talker1.add_flow(flow_high1, 3, payload_generator)
                talker12.add_flow(flow_high2, 3, payload_generator)
        talker2 = Talker(sim_env, "talker2", True)
        if leaky_rate_low > 0:
            talker2.add_flow(flow_low, 2, payload_generator)

        priority_map = PriorityMap(8)
        switch = UBSSwitch(sim_env, "switch", priority_map, switch_mode, True)

        listener = Listener(sim_env, "listener")

        # 5.
        topology = Topology(talker1, talker2, talker12, switch, listener)
        topology.multi_connect("switch", bandwidth, "talker1", "talker12", "talker2", "listener")

        # 6.
        sim_env.topology = topology

        # optional
        seed = np.random.randint(maxsize)

        # 7.
        yield sim_env


#simulate_multiple(foo("shapeless", 0.5, "tbe"), 15, 100000, "simple")

arr_mode = "lrq"
simulate_multiple_multiple([foo(True, 0.5, "lrq"),
                            foo(False, 0.5, "lrq")], 10, 100000, "simple2_%s" % arr_mode)

#simulate_multiple_multiple([foo("tbe", 0.1, "lrq"),
#                            foo("tbe", 0.2, "lrq"),
#                            foo("tbe", 0.3, "lrq"),
#                            foo("tbe", 0.4, "lrq"),
#                            foo("tbe", 0.5, "lrq"),
#                            foo("tbe", 0.6, "lrq"),
#                            foo("tbe", 0.7, "lrq"),
#                            foo("tbe", 0.8, "lrq"),
#                            foo("tbe", 0.9, "lrq"),
#                            foo("tbe", 1, "lrq")], 10, 100000, "simple_tbe_lrq_row")
