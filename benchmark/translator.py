import os

def process_file(input_file_path, output_file_path):
    with open(input_file_path, 'r') as file:
        lines = file.readlines()
    
    arguments = []
    attacks = []

    for line in lines:
        if line.startswith('p af'):
            # Extract the number of arguments from the p-line
            parts = line.split()
            n = int(parts[2])
            arguments = [f"arg(a{i})." for i in range(1, n + 1)]
        elif line.startswith('#'):
            continue
        else:
            # Process attack lines
            parts = line.strip().split()
            if len(parts) == 2:
                a, b = parts
                attacks.append(f"att(a{a},a{b}).")
    
    # Write to the output file
    with open(output_file_path, 'w') as file:
        file.write('\n'.join(arguments) + '\n')
        file.write('\n'.join(attacks) + '\n')

def main(input_dir, output_dir):
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Process each .af file in the input directory
    for filename in os.listdir(input_dir):
        if filename.endswith('.af'):
            input_file_path = os.path.join(input_dir, filename)
            output_file_path = os.path.join(output_dir, filename.replace('.af', '.apx'))
            process_file(input_file_path, output_file_path)

# Define input and output directories
input_dir = '/Users/dasaro/Desktop/Zlatina/supplementary_code/benchmark/ICCMA_original/main'
output_dir = '/Users/dasaro/Desktop/Zlatina/supplementary_code/benchmark/ICCMA23_apx'

# Run the main function
main(input_dir, output_dir)
