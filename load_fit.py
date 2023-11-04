from fitparse import FitFile
import pandas as pd


def load_fit(file_path):
    # 用你的FIT文件路径替换'your_file.fit'
    fitfile = FitFile(file_path)

    # 准备一个空的列表，用于存放每个记录的字典数据
    records = []

    # 获取所有的数据消息
    for record in fitfile.get_messages('record'):
        # 将记录数据存储到字典中
        record_dict = {}
        for record_data in record:
            # 将数据添加到字典中
            record_dict[record_data.name] = record_data.value
        # 将字典添加到记录列表中
        records.append(record_dict)

    # 将记录列表转换为DataFrame
    df = pd.DataFrame(records)
    print(df.columns)
    # 打印DataFrame
    return df


def get_gps_data(file_path):
    df = load_fit(file_path)
    gps_data = df[['position_lat', 'position_long']]
    print(gps_data)
    gps_list = []
    for i in range(len(gps_data)):
        gps_list.append((gps_data.loc[i, 'position_lat']/11930464.7, gps_data.loc[i, 'position_long']/11930464.7))
    return gps_list

# gps = get_gps_data('data/Lunch_Ride.fit')
# print(gps)
