import os
import re
import clingo

def run_clingo(input_file, semantics_file):
    """Runs Clingo on the given input file with a semantics specification."""
    ctl = clingo.Control(["-n", "1"])
    ctl.load(semantics_file)
    ctl.load(input_file)
    ctl.load("config/background_knowledge.lp")
    ctl.ground()
    models = []
    
    def on_model(model):
        models.append(model.symbols(shown=True))
    
    ctl.solve(on_model=on_model)
    return models

def check_satisfaction(input_dir, semantics_file, output_file):
    """Checks all files in a directory for satisfaction of a given semantics."""
    results = []
    n_satisfied = 0
    n_no_satisfied = 0
    
    for filename in os.listdir(input_dir):
        if not filename.endswith(".lp"):
            continue
        
        input_path = os.path.join(input_dir, filename)
        models = run_clingo(input_path, semantics_file)
        
        if models:
            n_satisfied = n_satisfied + 1
            results.append(f"{filename}: SATISFIES {semantics_file}")
        else:
            n_no_satisfied = n_no_satisfied + 1
            results.append(f"{filename}: DOES NOT SATISFY {semantics_file}")
    
    with open(output_file, "w") as f:
        f.write("\n".join(results) + "\n")
    
    print(f"Results saved to {output_file}")
    print(f"Satisfaction rate: {n_satisfied/(n_satisfied+n_no_satisfied)} on a total of {n_satisfied+n_no_satisfied} AAFs.")

if __name__ == "__main__":
    input_directory = "Real_World_Examples/asp_files/versionE/pos/"  # Change this to the target directory
    #semantics_file = "config/ASPARTIX/admissible.lp"  # Change this to the desired semantics file
    semantics_file = "Real_World_Examples/learned_encodings/versionE_special_neg.lp"  # Change this to the desired semantics file
    output_filename = "satisfaction_results.txt"
    
    check_satisfaction(input_directory, semantics_file, output_filename)
