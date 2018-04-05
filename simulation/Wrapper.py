from simulation.Core import SimulationEnvironment

import csv
import os

from collections import defaultdict


def mk_result_dir(filename: str, offset: int = 0):
    try:
        path = os.path.join("results", "%s_%s" % (filename, str(offset)))
        os.mkdir(path)
        return offset
    except FileExistsError:
        return mk_result_dir(filename, offset + 1)


def write_to_csv(result: dict, filename: str, offset: int):
    print("Writing to CSV")
    for dict_format, frame_list in result.items():
        path = os.path.join("results", "%s_%s" % (filename, str(offset)), "%s.csv" % dict_format)
        with open(path, "a", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=frame_list[0].keys(), delimiter=",", lineterminator="\n")
            if os.stat(path).st_size == 0:
                writer.writeheader()
            for frame_dict in frame_list:
                writer.writerow(frame_dict)
    print("Done")


def simulate_multiple(sim_generator, count: int, runtime: int, filename: str = None, offset: int = None):
    result = defaultdict(list)
    for i in range(0, count):
        sim_env: SimulationEnvironment = sim_generator.__next__()
        sim_env.run(runtime)
        sim_result: dict = sim_env.get_data()
        print("Simulation %d/%d done" % (i + 1, count))
        for dict_format, frame_list in sim_result.items():
            result[dict_format] += frame_list
    if filename is not None:
        if offset is None:
            try:
                os.mkdir("results")
            except FileExistsError:
                pass
            offset = mk_result_dir(filename)
        write_to_csv(result, filename, offset)
    return result


def simulate_multiple_multiple(sim_generator_list: list, count: int, runtime: int, filename: str = None):
    try:
        os.mkdir("results")
    except FileExistsError:
        pass
    offset = mk_result_dir(filename)
    i = 1
    for sim_generator in sim_generator_list:
        simulate_multiple(sim_generator, count, runtime, filename, offset)
        print("Simulation %d done" % i)
        i += 1
