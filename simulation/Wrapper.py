from simulation.Core import SimulationEnvironment

import csv
import json

from collections import defaultdict


def write_to_csv(result: dict, file_name: str):
    for dict_format, frame_list in result.items():
        with open("%s_%s.csv" % (file_name, dict_format), "w", encoding="utf-8") as file:
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
        for dict_format, frame_list in sim_result.items():
            result[dict_format] += frame_list
    if file_name is not None:
        write_to_csv(result, file_name)
    return result
