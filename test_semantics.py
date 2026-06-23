import os
import clingo

def run_clingo_with_api(semantics_file, test_file):
    """Runs Clingo using its API and returns multiple models."""
    ctl = clingo.Control(["-n", "0", "--warn=none"])
    ctl.load("background_knowledge.lp")
    ctl.load(semantics_file)
    ctl.load(test_file)
    ctl.add("#show in/1.")
    ctl.ground()
    
    models = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            models.append(set(model.__str__().split()))
    
    return models

def test_semantics(input_dir, custom_semantics, aspartix_semantics):
    """Compares custom semantics against ASPARTIX semantics for all files in a folder."""
    differing_files = []
    
    for test_file in os.listdir(input_dir):
        if test_file.endswith(".lp"):
            test_path = os.path.join(input_dir, test_file)
            
            custom_models = run_clingo_with_api(custom_semantics, test_path)
            aspartix_models = run_clingo_with_api(aspartix_semantics, test_path)
            
            if custom_models != aspartix_models:
                differing_files.append(test_file)
                print(f"Difference found in: {test_file}")
    
    if differing_files:
        print("\nSummary: Files with differing semantics:")
        for file in differing_files:
            print(file)
    else:
        print("All files produce identical results.")
    
    return differing_files

if __name__ == "__main__":
    input_directory = "STB_aafs_labelled/"  # Change to your folder
    custom_semantics_file = "STB_train_output/ilasp_task_50_0.lp"  # Change to your custom semantics file
    aspartix_semantics_file = "ASPARTIX/stable.lp"  # Change to the desired ASPARTIX semantics file
    
    test_semantics(input_directory, custom_semantics_file, aspartix_semantics_file)
