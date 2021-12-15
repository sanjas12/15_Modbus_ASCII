file_in = 'torque'
file_out = 'bytes'

with open(file_in, 'r') as f:
    data_in = f.readlines()


for line in data_in:
    if line:
        data_byte = bytes.fromhex(line.strip().replace('.', ''))
        print(bytes.fromhex(line.strip().replace('.', '')))
        with open(file_out, 'a') as f:
            f.write(str(bytes.fromhex(line.strip().replace('.', '')))+'\n')
