import svgwrite
import cairosvg
import cv2
import numpy as np
from math import pi, sin, cos
from svg_path_parse import scale_and_offset_svg
from tqdm import tqdm


def create_speed_svg(curr_speed, max_speed):
    # 创建一个SVG绘图
    dwg = svgwrite.Drawing('test.svg', size=(300, 200), profile='tiny')

    center_x = 100  # 弧形中心的X坐标
    center_y = 100  # 弧形中心的Y坐标
    radius = 50  # 弧形半径

    # 画出圆心
    solid_circle = dwg.circle(center=(center_x, center_y), r=5, fill='white')
    dwg.add(solid_circle)
    # 画出圆弧
    start_angle = -120  # 弧形开始的角度（单位为度）
    end_angle = 120  # 弧形结束的角度（单位为度）
    start_rad = start_angle * pi / 180
    end_rad = end_angle * pi / 180
    start_x = center_x + radius * sin(start_rad)
    start_y = center_y - radius * cos(start_rad)
    end_x = center_x + radius * sin(end_rad)
    end_y = center_y - radius * cos(end_rad)
    path = dwg.path(d=('M', start_x, start_y), stroke='white', fill='none', stroke_width=2)
    path.push('A', radius, radius, 0, 1, 1, end_x, end_y)
    dwg.add(path)
    # 画出指针
    if curr_speed is None:
        angle = -120
    else:
        angle = -120 + curr_speed / max_speed * 240
    rad = angle * pi / 180
    end_x = center_x + (radius - 5) * sin(rad)
    end_y = center_y - (radius - 5) * cos(rad)
    line = dwg.line(start=(center_x, center_y), end=(end_x, end_y), stroke='white', stroke_width=3)
    dwg.add(line)
    # 加入速度
    text = dwg.text("速度", insert=(160, 65), font_size="25px", font_family="新宋体", fill='white')
    dwg.add(text)
    # 加入当前速度
    if curr_speed is None:
        curr_speed = '-- km/h'
    else:
        curr_speed = f"{curr_speed:.2f} km/h"
    text = dwg.text(curr_speed, insert=(180, 110), font_size="30px", font_family="新宋体", fill='white')
    dwg.add(text)
    # 保存文件
    # dwg.save()
    svg_data = dwg.tostring()
    return svg_data


def create_power_svg(curr_power):
    dwg = svgwrite.Drawing('test.svg', size=(250, 100))
    svg_string = scale_and_offset_svg('imgs/哑铃1.svg', 0.18, (0, 0))
    path = dwg.path(d=svg_string, fill='white')
    dwg.add(path)
    # 加入速度
    text = dwg.text("功率", insert=(105, 25), font_size="25px", font_family="新宋体", fill='white')
    dwg.add(text)
    # 加入当前速度
    if curr_power is None:
        curr_power = '--'
    text = dwg.text(f"{curr_power} w", insert=(135, 70), font_size="30px", font_family="新宋体", fill='white')
    dwg.add(text)
    # dwg.save()
    svg_data = dwg.tostring()
    return svg_data


def create_heart_rate_svg(curr_heart_rate):
    pass


def create_track_svg(curr_gps):
    pass


def create_cadence_svg(curr_cadence):
    pass


def convert_svg_to_png(svg_data):
    png_image = cairosvg.svg2png(bytestring=svg_data)
    return png_image


def add_png_to_frame(png_bytes, frame, x, y):
    # 将字节数据转换为numpy数组
    png_array = np.frombuffer(png_bytes, dtype=np.uint8)
    # 通过cv2.imdecode读取数组，得到图像
    png_img = cv2.imdecode(png_array, cv2.IMREAD_UNCHANGED)
    # 获取png图片的宽高
    png_height, png_width = png_img.shape[:2]

    # 如果png图片有透明度通道，则分离它和彩色通道
    if png_img.shape[2] == 4:
        # 分离颜色通道和alpha通道
        png_color = png_img[:, :, :3]
        alpha_mask = png_img[:, :, 3] / 255.0
    else:
        # 如果没有alpha通道，默认不透明
        png_color = png_img
        alpha_mask = np.ones((png_height, png_width))

    # 计算叠加区域的坐标
    y1, y2 = y, y + png_height
    x1, x2 = x, x + png_width

    # 叠加区域的ROI
    roi = frame[y1:y2, x1:x2]

    # 根据alpha值混合图片
    for c in range(0, 3):
        roi[:, :, c] = (alpha_mask * png_color[:, :, c] +
                        (1 - alpha_mask) * roi[:, :, c])

    # 将修改后的ROI放回原视频帧
    frame[y1:y2, x1:x2] = roi
    return frame


def align_video_frame_and_fit(aligned_video_position, aligned_fit_position, curr_video_frame_num, fit_gap, fps):
    """
    对齐video的帧和fit中的数据点
    计算过程中单位统一为s
    :return:
    """
    curr_frame_time = curr_video_frame_num / fps
    frame_time_gap = curr_frame_time - aligned_video_position / 1000
    curr_fit_time = aligned_fit_position * fit_gap + frame_time_gap
    curr_fit_point = int(curr_fit_time / fit_gap)
    return curr_fit_point


def align_video_positoin_and_fit(aligned_video_position, aligned_fit_position, curr_video_position, fit_gap, fps):
    """
    对齐video的帧和fit中的数据点
    计算过程中单位统一为s
    :return:
    """
    curr_frame_time = curr_video_position / 1000
    frame_time_gap = curr_frame_time - aligned_video_position / 1000
    curr_fit_time = aligned_fit_position * fit_gap + frame_time_gap
    curr_fit_point = int(curr_fit_time / fit_gap)
    return curr_fit_point


def generate_fit_png(fit_data, frame):
    # Index(['altitude', 'cadence', 'distance', 'enhanced_altitude',
    #        'enhanced_speed', 'heart_rate', 'position_lat', 'position_long',
    #        'power', 'speed', 'temperature', 'timestamp'],
    #       dtype='object')
    speed = fit_data['speed']
    max_speed = 60
    power = fit_data['power']
    speed_svg_string = create_speed_svg(speed, max_speed)
    power_svg_string = create_power_svg(power)
    speed_png = convert_svg_to_png(speed_svg_string)
    power_png = convert_svg_to_png(power_svg_string)
    return speed_png, power_png


def add_fit_svg_to_frame(speed_png, power_png, frame):
    frame = add_png_to_frame(speed_png, frame, 100, 600)
    frame = add_png_to_frame(power_png, frame, 150, 700)
    return frame


def add_fit_data_to_video(input_video_path, fit_data, output_video_path, aligned_video_position, aligned_fit_position,
                          fit_gap):
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        exit()
    # 获取视频的帧率
    fps = cap.get(cv2.CAP_PROP_FPS)
    # 获取视频的大小（宽度和高度）
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # 获取视频总帧数
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # 定义视频编码器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 或者使用 'XVID' 根据文件扩展名
    # 创建视频写入对象
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

    frame_number = 0
    fit_row_preview = -1
    for frame_number in tqdm(range(total_frames), desc="Processing video"):
        ret, frame = cap.read()
        if not ret:
            print("Reached the end of the video or an error occurred.")
            break
        # 先要计算一下当前帧对应fit_data的第几行
        fit_row = align_video_frame_and_fit(aligned_video_position=aligned_video_position,
                                            aligned_fit_position=aligned_fit_position,
                                            fit_gap=fit_gap,
                                            fps=fps,
                                            curr_video_frame_num=frame_number)

        if fit_row != fit_row_preview:
            fit_row_preview = fit_row
            if fit_row < 0 or fit_row >= len(fit_data) - 1:
                speed_png, power_png = generate_fit_png({"speed": None, "power": None}, frame)
            else:
                speed_png, power_png = generate_fit_png(dict(fit_data.loc[fit_row, :]), frame)

        frame = add_fit_svg_to_frame(speed_png, power_png, frame)

        out.write(frame)
        # 更新帧号
        frame_number += 1
    cap.release()

# from load_fit import load_fit, get_gps_data
#
# fit_data = load_fit('data/Lunch_Ride.fit')
# fit_data['speed'] = fit_data['speed'] * 3.6
# fit_data.to_csv('data/data.csv')
#
# add_fit_data_to_video(input_video_path='video/GH010288.mp4',
#                       fit_data=fit_data,
#                       output_video_path='video/output.mp4',
#                       aligned_fit_time=500,
#                       aligned_video_time=424.913,
#                       fit_gap=1)
