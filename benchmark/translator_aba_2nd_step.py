def parse_clingo_output(input_file_path, output_file_path):
    with open(input_file_path, 'r') as file:
        lines = file.readlines()
    
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
                    # Save contraries only from the first answer
                    first_answer_contraries.append(element + '.')

    with open(output_file_path, 'w') as output_file:
        # Write contraries from the first answer set
        for contr in first_answer_contraries:
            output_file.write(contr + '\n')
        # Write all other results
        for result in results:
            output_file.write(result + '\n')

if __name__ == "__main__":
    input_file_path = '/Users/dasaro/Desktop/Zlatina/supplementary_code/benchmark/ICCMA23_aba_apx/aba_25_0.1_5_5_0.apx.args'
    output_file_path = '/Users/dasaro/Desktop/Zlatina/supplementary_code/benchmark/ICCMA23_aba_apx/aba_25_0.1_5_5_0.apx.2nd.args'
    parse_clingo_output(input_file_path, output_file_path)
