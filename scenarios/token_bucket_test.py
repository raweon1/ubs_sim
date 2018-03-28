from simulation.Core import SimulationEnvironment, Topology
from simulation.Talker import Talker, TokenBucketTalker
from simulation.Switch import UBSSwitch
from simulation.PriorityMap import PriorityMap
from simulation.Path import Path
from simulation.Flow import Flow
from simulation.Node import Listener
from simulation.Wrapper import simulate_multiple, simulate_multiple_multiple


def payload_gen(payload):
    while True:
        yield payload


def time_gen(mean, rnd_state):
    while True:
        yield rnd_state.exponential(mean)


def foo(exp_mean):
    offset = 987321
    seed = 123456789
    while True:
        sim_env = SimulationEnvironment("exp_mean=%d" % exp_mean, seed)
        seed += offset

        path = Path("talker", "listener")

        leaky_rate = 1000 * 0.05
        burstiness = 1500
        payload = 599
        # exp_mean = 500

        # print("frame_len = %d, bandwidth = 1GBit, transmission_time = %f" % (payload + 26, (payload + 26) * 8 / 1000))
        # print("time to leak one frame = %f" % ((payload + 26) * 8 / leaky_rate))
        # print("avg time to next frame = %d" % exp_mean)
        # print()

        flow = Flow(1, path, leaky_rate, burstiness)

        tbt = TokenBucketTalker(sim_env, "talker", flow, 0,
                                payload_gen(payload), time_gen(exp_mean, sim_env.random),
                                True)
        listener = Listener(sim_env, "listener")

        topology = Topology(tbt, listener)
        topology.connect("talker", "listener")
        sim_env.topology = topology
        yield sim_env


# simulate_multiple(foo(500), 3, 10000, "token_bucket_test")
simulate_multiple_multiple([foo(500), foo(300), foo(200), foo(125), foo(100), foo(75), foo(50)], 15, 1000000, "token_bucket_test")
