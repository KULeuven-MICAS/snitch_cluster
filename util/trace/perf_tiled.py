# Compare performance of tiled vs untiled layers on snitch/snax
import subprocess
import json
import itertools
"""
Does the following:
0. make -C target... clean-data
1. make -C target... all LENGTH=... TILE_SIZE=...
2. run bin/snitch_cluster.vlt something.elf
3. make traces
4. Process logs
5. TODO store logs somewhere
"""
def generate_data_points():
    all_combinations = list(itertools.product(range(16, 240, 16), range(4, 64, 4)))
    # Some combinations are not valid
    valid_combinations = []
    for combination in all_combinations:
       if combination[0] % combination[1] == 0:
          valid_combinations.append(combination)
    return valid_combinations


def compile_example(sizes, target_directory):
    """
    Build a tiled/untiled example with:
    * sizes = (length, tile_size)
    * target_directory = directory from which to invoke make
    """
    # Clean up the previous result, if any:
    subprocess.run(["make", "-C", target_directory, "clean-data"], stdout=subprocess.DEVNULL)
    # Run the compilation
    subprocess.run(["make", "-C", target_directory, "all", f"LENGTH={sizes[0]}",f"TILE_SIZE={sizes[1]}"], stdout=subprocess.DEVNULL)



if __name__ == "__main__":
    data_points = generate_data_points()
    target_directory = "sw/apps/snax-mac-simple/tiled"
    log_directory = "/repo/target/snitch_cluster"
    for sizes in data_points:
        compile_example(sizes, target_directory)
        try:
            subprocess.run(["bin/snitch_cluster.vlt", target_directory+"/build/tiled.elf"], check=True, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            # Skip post-processing if there was an error in running the example
            print(f"Failed for length={sizes[0]}, tile_size={sizes[1]}")
            continue
        subprocess.run(["make","-j","traces"], stdout=subprocess.DEVNULL)
        with open(log_directory+"/logs/hart_00000001_perf.json", "r") as file:
            json_object = json.load(file)
            print(f"LENGTH={sizes[0]:>7}, TILE_SIZE={sizes[1]:>7}: " + f"{int(json_object[1]['cycles']):>20} cycles")
