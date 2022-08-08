def parse_data(read_data):
    cavity_data_1 = []
    cavity_data_2 = []
    cavity_data_3 = []
    cavity_data_4 = []
    for data in read_data:
        cavity_data_1.append(float(data[0:8]))
        try:
            if data[10:18] != '':
                cavity_data_2.append(float(data[10:18]))
            if data[20:28] != '':
                cavity_data_3.append(float(data[20:28]))
            if data[30:38] != '':
                cavity_data_4.append(float(data[30:38]))
        except:
            pass
    # print(cavity_data_1)
    return [cavity_data_1, cavity_data_2, cavity_data_3, cavity_data_4]
