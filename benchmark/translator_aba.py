import os
import subprocess
import tempfile

def process_aba_file(input_file_path, output_file_path):
    with open(input_file_path, 'r') as input_file:
        lines = input_file.readlines()

    with open(output_file_path, 'w') as output_file:
        for line in lines:
            line = line.strip()
            if line.startswith('#') or line == '':
                continue
            elif line.startswith('p'):
                continue
            elif line.startswith('a'):
                _, index = line.split()
                output_file.write(f"as(a{index}).\n")
            elif line.startswith('c'):
                _, first_index, second_index = line.split()
                output_file.write(f"contr(a{first_index},a{second_index}).\n")
            elif line.startswith('r'):
                parts = line.split()
                head = parts[1]
                if len(parts) > 2:
                    body = ', '.join(f"holds(a{x})" for x in parts[2:])
                    output_file.write(f"holds(a{head}) :- {body}.\n")
                else:
                    output_file.write(f"holds(a{head}).\n")

def parse_clingo_output(clingo_output, output_file_path):
    lines = clingo_output.split('\n')
    current_answer = 0
    first_answer_contraries = []
    results = []

    for line in lines:
        line = line.strip()
        if line.startswith("Answer:"):
            current_answer = int(line.split()[1])
        elif line.startswith("assume(") or line.startswith("root(") or line.startswith("contr("):
            elements = line.split()
            assumptions = []
            roots = []
            for element in elements:
                if element.startswith("assume("):
                    atom = element.split('(')[1].rstrip(')')
                    assumptions.append(atom)
                    results.append(f"as({current_answer}, {atom}).")
                elif element.startswith("root("):
                    atom = element.split('(')[1].rstrip(')')
                    if atom not in assumptions:
                        roots.append(atom)
                        results.append(f"root({current_answer}, {atom}).")
                elif element.startswith("contr(") and current_answer == 1:
                    first_answer_contraries.append(element + '.')

    with open(output_file_path, 'w') as output_file:
        for contr in first_answer_contraries:
            output_file.write(contr + '\n')
        for result in results:
            output_file.write(result + '\n')

def main(directory):
    for file in os.listdir(directory):
        if file.endswith(".aba"):
            aba_file_path = os.path.join(directory, file)
            temp_output = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.lp')
            
            process_aba_file(aba_file_path, temp_output.name)
            print(temp_output.name)

            cmd = f"clingo -n 0 --heuristic=domain --enum=domrec /Users/dasaro/Desktop/Zlatina/supplementary_code/transform_ABA_to_AAF/construct_args.lp {temp_output.name}"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                print(f"Error processing file {aba_file_path}: {stderr.decode('utf-8')}")
                apx_filename = file.replace('.aba', '.apx')
                apx_file_path = os.path.join(directory, apx_filename)
                parse_clingo_output(stdout.decode('utf-8'), apx_file_path)

            
            temp_output.close()
            os.unlink(temp_output.name)

if __name__ == "__main__":
    directory_path = '/Users/dasaro/Desktop/Zlatina/supplementary_code/benchmark/ICCMA_original/aba/'
    main(directory_path)
