from simulation.Core import SimulationEnvironment, Topology
from simulation.Talker import Talker
from simulation.Switch import UBSSwitch, UBSSwitch2
from simulation.PriorityMap import PriorityMap
from simulation.Path import Path
from simulation.Flow import Flow
from simulation.Node import Listener
from simulation.Wrapper import simulate_multiple


def payload_gen(sim_env: SimulationEnvironment, mean):
    rnd = sim_env.random
    while True:
        yield rnd.uniform(0, mean * 2)


def foo():
    offset = 54321
    seed = 123456789
    while True:
        p1 = Path("talker1", "switch1", "switch2", "listener")
        p2 = Path("talker2", "switch1", "switch2", "listener")
        p3 = Path("talker3", "switch1", "switch2", "listener")
        p4 = Path("talker4", "switch1", "switch2", "listener")

        flow_rates = [0.06, 0.06, 0.06, 0.06,
                      0.06, 0.06, 0.06, 0.06,
                      0.06, 0.06, 0.06, 0.06,
                      0.06, 0.06, 0.06, 0.06]

        flow_rates = [0.075, 0.025, 0.052, 0.07,
                      0.035, 0.095, 0.125, 0.013,
                      0.123, 0.036, 0.092, 0.027,
                      0.012, 0.098, 0.075, 0.046]

        burstiness = 3000

        f1 = Flow(1, p1, 1000 * flow_rates[0], burstiness)
        f2 = Flow(2, p1, 1000 * flow_rates[1], burstiness)
        f3 = Flow(3, p1, 1000 * flow_rates[2], burstiness)
        f4 = Flow(4, p1, 1000 * flow_rates[3], burstiness)

        f5 = Flow(5, p2, 1000 * flow_rates[4], burstiness)
        f6 = Flow(6, p2, 1000 * flow_rates[5], burstiness)
        f7 = Flow(7, p2, 1000 * flow_rates[6], burstiness)
        f8 = Flow(8, p2, 1000 * flow_rates[7], burstiness)

        f9 = Flow(9, p3, 1000 * flow_rates[8], burstiness)
        f10 = Flow(10, p3, 1000 * flow_rates[9], burstiness)
        f11 = Flow(11, p3, 1000 * flow_rates[10], burstiness)
        f12 = Flow(12, p3, 1000 * flow_rates[11], burstiness)

        f13 = Flow(13, p4, 1000 * flow_rates[12], burstiness)
        f14 = Flow(14, p4, 1000 * flow_rates[13], burstiness)
        f15 = Flow(15, p4, 1000 * flow_rates[14], burstiness)
        f16 = Flow(16, p4, 1000 * flow_rates[15], burstiness)

        sim_env = SimulationEnvironment("test", seed)

        payload_generator = payload_gen(sim_env, 750)

        talker1 = Talker(sim_env, "talker1", True)
        talker1.add_flow(f1, 5, payload_generator)
        talker1.add_flow(f2, 5, payload_generator)
        talker1.add_flow(f3, 0, payload_generator)
        talker1.add_flow(f4, 0, payload_generator)
        talker2 = Talker(sim_env, "talker2", True)
        talker2.add_flow(f5, 5, payload_generator)
        talker2.add_flow(f6, 5, payload_generator)
        talker2.add_flow(f7, 0, payload_generator)
        talker2.add_flow(f8, 0, payload_generator)
        talker3 = Talker(sim_env, "talker3", True)
        talker3.add_flow(f9, 5, payload_generator)
        talker3.add_flow(f10, 5, payload_generator)
        talker3.add_flow(f11, 0, payload_generator)
        talker3.add_flow(f12, 0, payload_generator)
        talker4 = Talker(sim_env, "talker4", True)
        talker4.add_flow(f13, 5, payload_generator)
        talker4.add_flow(f14, 5, payload_generator)
        talker4.add_flow(f15, 0, payload_generator)
        talker4.add_flow(f16, 0, payload_generator)

        priority_map = PriorityMap(1)
        switch1 = UBSSwitch(sim_env, "switch1", priority_map, "lrq", True)
        switch2 = UBSSwitch2(sim_env, "switch2", priority_map, "lrq", False)

        listener = Listener(sim_env, "listener")

        t = Topology(talker1, talker2, talker3, talker4, switch1, switch2, listener)
        sim_env.topology = t
        t.multi_connect("switch1", 1000, "talker1", "talker2", "talker3", "talker4", "switch2")
        t.connect("switch2", "listener", 1000)

        seed += offset
        yield sim_env


simulate_multiple(foo(), 16, 50000, "scenario1")
