import xml.etree.ElementTree as ET
import re
import os
from lxml import etree


def extract_path_d_attribute(svg_file_path):
    """
    读取SVG文件并提取第一个<path>元素的 'd' 属性
    """
    tree = ET.parse(svg_file_path)
    root = tree.getroot()
    path_d_attributes = [
        path.attrib['d'] for path in root.findall('.//{http://www.w3.org/2000/svg}path')
    ]
    return path_d_attributes[0]





def convert_str_to_num(s):
    try:
        # 首先尝试转换为整数
        return int(s)
    except ValueError:
        # 如果失败了，说明不是整数，再尝试转换为浮点数
        try:
            return float(s)
        except ValueError:
            # 如果浮点数也转换失败，那么可能不是数字
            raise ValueError(f"无法将字符串'{s}'转换为数字")


def parse_svg_path_data(svg_file_path):
    """
    将svg中的path转换为符合svgwrite的字符串
    :param svg_file_path:
    :return:
    """
    path_data = extract_path_d_attribute(svg_file_path)

    parsed_data = ''
    for index, char in enumerate(path_data):
        if char in 'MmLlHhVvCcSsQqTtAaZz':
            parsed_data += f' {char} '
        elif char == '-' and path_data[index - 1] not in 'MmLlHhVvCcSsQqTtAa':
            parsed_data += ',-'
        else:
            parsed_data += char
    return parsed_data.strip()


def scale_and_offset_svg(input_data, scale_factor=1, offset_vector=(0, 0)):
    path_data = extract_path_d_attribute(input_data)  # input_data 是文件路径
    path_segments = re.findall('[MmLlHhVvCcSsQqTtAa][^MmLlHhVvCcSsQqTtAaZz]*|Z', path_data)
    svg_string = ''
    for segment in path_segments:
        segment_params = parse_single_path(segment)
        params_groups = split_multiple_params(segment_params)
        for params in params_groups:
            params = apply_scale_and_offset(params, scale_factor, offset_vector)
            svg_string = convert_params_to_svg(params, svg_string)
    return svg_string.strip()


def apply_scale_and_offset(params, scale, offset):
    command_to_function = {
        'M': svg_scale_and_offset_MLT,
        'm': svg_scale_and_offset_mlt,
        'L': svg_scale_and_offset_MLT,
        'l': svg_scale_and_offset_mlt,
        'T': svg_scale_and_offset_MLT,
        't': svg_scale_and_offset_mlt,
        'H': svg_scale_and_offset_HhVv,
        'h': svg_scale_and_offset_HhVv,
        'V': svg_scale_and_offset_HhVv,
        'v': svg_scale_and_offset_HhVv,
        'S': svg_scale_and_offset_SQ,
        's': svg_scale_and_offset_sq,
        'Q': svg_scale_and_offset_SQ,
        'q': svg_scale_and_offset_sq,
        'A': svg_scale_and_offset_A,
        'a': svg_scale_and_offset_a,
        'C': svg_scale_and_offset_C,
        'c': svg_scale_and_offset_c,
        'Z': svg_scale_and_offset_Zz,
        'z': svg_scale_and_offset_Zz
    }
    command = params[0]
    return command_to_function[command](params, scale, offset)


def split_multiple_params(params):
    svg_commands = {
        'M': 2,  # M x y - 移动到指定的绝对坐标
        'm': 2,  # m dx dy - 移动到指定的相对坐标
        'L': 2,  # L x y - 画线到指定的绝对坐标
        'l': 2,  # l dx dy - 画线到指定的相对坐标
        'H': 1,  # H x - 水平线到指定的绝对 x 坐标
        'h': 1,  # h dx - 水平线到指定的相对 x 坐标
        'V': 1,  # V y - 垂直线到指定的绝对 y 坐标
        'v': 1,  # v dy - 垂直线到指定的相对 y 坐标
        'C': 6,  # C x1 y1 x2 y2 x y - 三次贝塞尔曲线到指定的绝对坐标
        'c': 6,  # c dx1 dy1 dx2 dy2 dx dy - 三次贝塞尔曲线到指定的相对坐标
        'S': 4,  # S x2 y2 x y - 平滑的三次贝塞尔曲线到指定的绝对坐标
        's': 4,  # s dx2 dy2 dx dy - 平滑的三次贝塞尔曲线到指定的相对坐标
        'Q': 4,  # Q x1 y1 x y - 二次贝塞尔曲线到指定的绝对坐标
        'q': 4,  # q dx1 dy1 dx dy - 二次贝塞尔曲线到指定的相对坐标
        'T': 2,  # T x y - 平滑的二次贝塞尔曲线到指定的绝对坐标
        't': 2,  # t dx dy - 平滑的二次贝塞尔曲线到指定的相对坐标
        'A': 7,  # A rx ry rotation large-arc-flag sweep-flag x y - 弧线到指定的绝对坐标
        'a': 7,  # a rx ry rotation large-arc-flag sweep-flag dx dy - 弧线到指定的相对坐标
        'Z': 0,  # Z - 关闭路径
        'z': 0  # z - 关闭路径（与大写 Z 相同效果）
    }
    command = params[0]
    if svg_commands[command] == 0:
        return [[command]]
    k = svg_commands[command]

    segments = [params[:k + 1]]
    # 剩余的元素开始分割
    remaining = params[k + 1:]
    # 每 k 个元素分割剩余部分
    for i in range(0, len(remaining), k):
        temp = remaining[i:i + k]
        temp.insert(0, command)
        segments.append(temp)
    return segments


def svg_scale_and_offset_MLT(params, scale, offset):
    assert len(params) == 3
    params[1] = params[1] * scale + offset[0]
    params[2] = params[2] * scale + offset[1]
    return params


def svg_scale_and_offset_A(params, scale, offset):
    assert len(params) == 8
    params[1] *= scale
    params[2] *= scale
    params[6] = params[6] * scale + offset[0]
    params[7] = params[7] * scale + offset[1]
    return params


def svg_scale_and_offset_a(params, scale, offset):
    assert len(params) == 8
    params[1] *= scale
    params[2] *= scale
    params[6] = params[6] * scale
    params[7] = params[7] * scale
    return params


def svg_scale_and_offset_mlt(params, scale, offset):
    assert len(params) == 3
    params[1] *= scale
    params[2] *= scale
    return params


def svg_scale_and_offset_SQ(params, scale, offset):
    assert len(params) == 5
    params[1] *= scale + offset[0]
    params[2] *= scale + offset[1]
    params[3] *= scale + offset[0]
    params[4] *= scale + offset[1]
    return params


def svg_scale_and_offset_sq(params, scale, offset):
    assert len(params) == 5
    params[1] *= scale
    params[2] *= scale
    params[3] *= scale
    params[4] *= scale
    return params


def svg_scale_and_offset_C(params, scale, offset):
    assert len(params) == 7
    params[1] *= scale + offset[0]
    params[2] *= scale + offset[1]
    params[3] *= scale + offset[0]
    params[4] *= scale + offset[1]
    params[5] *= scale + offset[0]
    params[6] *= scale + offset[1]
    return params


def svg_scale_and_offset_c(params, scale, offset):
    assert len(params) == 7
    params[1] *= scale
    params[2] *= scale
    params[3] *= scale
    params[4] *= scale
    params[5] *= scale
    params[6] *= scale
    return params


def svg_scale_and_offset_HhVv(params, scale, offset):
    assert len(params) == 2
    params[1] *= scale
    return params


def svg_scale_and_offset_Zz(params, scale, offset):
    return params


def parse_single_path(p):
    params = p[1:]
    params = params.replace(',', ' ')
    params = params.replace('-', ' -')
    params = [convert_str_to_num(param) for param in params.split()]
    params.insert(0, p[0])
    return params


def convert_params_to_svg(params, string=''):
    string += f' {params[0]} '
    string += ','.join(str(param) for param in params[1:])
    return string
