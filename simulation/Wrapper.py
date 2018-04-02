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


def write_to_csv(result: dict, filename: str):
    print("Writing CSV")
    try:
        os.mkdir("results")
    except FileExistsError:
        pass
    offset = mk_result_dir(filename)
    for dict_format, frame_list in result.items():
        path = os.path.join("results", "%s_%s" % (filename, str(offset)), "%s.csv" % dict_format)
        with open(path, "w", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=frame_list[0].keys(), delimiter=",", lineterminator="\n")
            writer.writeheader()
            for frame_dict in frame_list:
                writer.writerow(frame_dict)


def simulate_multiple(sim_generator, count: int, runtime: int, file_name: str = None):
    result = defaultdict(list)
    for i in range(0, count):
        sim_env: SimulationEnvironment = sim_generator.__next__()
        sim_env.run(runtime)
        sim_result: dict = sim_env.get_data()
        print("Simulation %d/%d done" % (i + 1, count))
        for dict_format, frame_list in sim_result.items():
            result[dict_format] += frame_list
    if file_name is not None:
        write_to_csv(result, file_name)
    return result


def simulate_multiple_multiple(sim_generator_list: list, count: int, runtime: int, file_name: str = None):
    result = defaultdict(list)
    i = 1
    for sim_generator in sim_generator_list:
        sim_result: dict = simulate_multiple(sim_generator, count, runtime)
        print("Simulation %d done" % i)
        i += 1
        for dict_format, frame_list in sim_result.items():
            result[dict_format] += frame_list
    if file_name is not None:
        write_to_csv(result, file_name)
    return result
