import csv
import os
import subprocess
import time

# Define the directory containing the files and the output CSV file path
input_directory = '/Users/dasaro/Desktop/Zlatina/supplementary_code/benchmark/ICCMA23_apx/'
output_file = '/Users/dasaro/Desktop/Zlatina/supplementary_code/benchmark/benchmark_results_stable_comparison_ilasp.csv'

# Define the commands for each combination of reasoner and semantics
commands = {
    #"ilasp": {
        #"stable": "clingo -n 1 -q /Users/dasaro/Desktop/Zlatina/supplementary_code/ASP_learned_encodings/AAF_LP_encodings/stable.lp",
        #"new_stable": "clingo -n 1 -q /Users/dasaro/Desktop/Zlatina/supplementary_code/ASP_learned_encodings/AAF_LP_encodings/stable_new.lp",
        #"complete": "clingo -n 1 -q /Users/dasaro/Desktop/Zlatina/supplementary_code/ASP_learned_encodings/AAF_LP_encodings/complete.lp",
        #"preferred": "clingo -n 1 -q --heuristic=Domain --enum=domRec --out-hide /Users/dasaro/Desktop/Zlatina/supplementary_code/ASP_learned_encodings/AAF_LP_encodings/preferred.lp"
        #"admissible": "clingo -n 1 -q /Users/dasaro/Desktop/Zlatina/supplementary_code/ASP_learned_encodings/AAF_LP_encodings/admissible.lp",
        #"grounded": "clingo -n 1 -q --heuristic=Domain --enum=domRec --out-hide /Users/dasaro/Desktop/Zlatina/supplementary_code/ASP_learned_encodings/AAF_LP_encodings/grounded.lp"
    #},
    #"aspartix": {
        #"stable": "clingo -n 1 -q /Users/dasaro/Desktop/Zlatina/ASPARTIX/stable.lp",
        #"complete": "clingo -n 1 -q /Users/dasaro/Desktop/Zlatina/ASPARTIX/complete.lp",
        #"preferred": "clingo -n 1 -q --heuristic=Domain --enum=domRec --out-hide /Users/dasaro/Desktop/Zlatina/ASPARTIX/preferred.lp",
        #"admissible": "clingo -n 1 -q /Users/dasaro/Desktop/Zlatina/ASPARTIX/admissible.lp",
        #"grounded": "clingo -n 1 -q /Users/dasaro/Desktop/Zlatina/ASPARTIX/grounded.lp"
    #}#,
    "mu-toksia": {
    #    "stable": "mu-toksia -fo apx -p SE-ST -f",
    #    "complete": "mu-toksia -fo apx -p SE-CO -f",
    #    "preferred": "mu-toksia -fo apx -p SE-PR -f"
        "admissible": "mu-toksia -fo apx -p SE-AD -f"
    }
}

# Timeout setting in seconds
timeout_duration = 1200 # ICCMA23 limit
penalty_for_timeout = 2400 # PAR-2 score for timeout

def run_command(file_path, command):
    start_time = time.time()
    try:
        # Execute the command with the file path appended, with timeout
        subprocess.run(f"{command} {file_path}", shell=True, check=True, timeout=timeout_duration)
    except subprocess.TimeoutExpired:
        print("Command timed out.")
        #end_time = time.time()
        return 2400
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
    end_time = time.time()
    # Calculate execution time in seconds
    return end_time - start_time

# Open the CSV file for writing
with open(output_file, mode='a', newline='') as file:
    writer = csv.writer(file)
    # Iterate over each file in the directory
    for filename in os.listdir(input_directory):
        if filename.endswith('.apx'):  # Check for argumentation framework files
            file_path = os.path.join(input_directory, filename)
            for reasoner, semantics_commands in commands.items():
                for semantics, command in semantics_commands.items():
                    print(f"Running {reasoner} on {filename} looking for {semantics} extensions")
                    # Time the command execution
                    execution_time = run_command(file_path, command)
                    execution_time_str = f"{execution_time:.3f}" if isinstance(execution_time, float) else execution_time
                    print(f"Execution time: {execution_time_str} seconds")
                    # Write the results to the CSV file and flush the output
                    writer.writerow([filename[:-4], reasoner, semantics.capitalize(), execution_time_str])
                    file.flush()

print("Benchmarking complete.")

