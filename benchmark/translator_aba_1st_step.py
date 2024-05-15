def process_aba_file(input_file_path, output_file_path):
    with open(input_file_path, 'r') as input_file:
        lines = input_file.readlines()

    # Open the output file for writing
    with open(output_file_path, 'w') as output_file:
        for line in lines:
            line = line.strip()  # Remove leading and trailing whitespace

            if line.startswith('#') or line == '':
                # Skip comments and empty lines
                continue
            elif line.startswith('p'):
                # Skip the p-line as well
                continue
            elif line.startswith('a'):
                # Process assumptions
                _, index = line.split()
                output_file.write(f"as(a{index}).\n")
            elif line.startswith('c'):
                # Process contraries
                _, first_index, second_index = line.split()
                output_file.write(f"contr(a{first_index},a{second_index}).\n")
            elif line.startswith('r'):
                # Process rules
                parts = line.split()
                head = parts[1]
                if len(parts) > 2:
                    body = ', '.join(f"holds(a{x})" for x in parts[2:])
                    output_file.write(f"holds(a{head}) :- {body}.\n")
                else:
                    # Rule with empty body (fact)
                    output_file.write(f"holds(a{head}).\n")

if __name__ == "__main__":
    # Example usage
    input_file_path = '/Users/dasaro/Desktop/Zlatina/supplementary_code/benchmark/ICCMA_original/aba/aba_25_0.1_5_5_0.aba'
    output_file_path = '/Users/dasaro/Desktop/Zlatina/supplementary_code/benchmark/ICCMA23_aba_apx/aba_25_0.1_5_5_0.apx'
    process_aba_file(input_file_path, output_file_path)