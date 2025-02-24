import random
import string
import uuid
import argparse
import hashlib
import os
import tempfile
import configparser
import re
import ast


# --- 配置文件读取和处理 ---
config_file = 'rget.ini'
config = configparser.ConfigParser(interpolation=None)  # 禁用插值

# 检查配置文件是否存在，如果不存在，则创建
if not os.path.exists(config_file):
    config['Settings'] = {'min_length': '1', 'max_length': '32767'}
    with open(config_file, 'w') as configfile:
        config.write(configfile)

config.read(config_file)

def get_config_value(section, key, default_value):
    """获取配置值，根据 key 决定是否转换为整数"""
    try:
        value = config.get(section, key)
        if key in ('min_length', 'max_length'):
            return int(value)  # 将字符串转换为整数
        elif key == 'value':
            return value.replace('%', '%%')  # 处理%
        else:
            return value  # 其他情况直接返回字符串
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
        return default_value


def set_config_value(section, key, value):
    """设置配置值，如果 section 不存在则创建"""
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, key, value)
    with open(config_file, 'w') as configfile:
        config.write(configfile)


def apply_operation(value, operation, operand):
    try:
        operand = int(operand)
        if operation == '+':
            return value + operand
        elif operation == '-':
            return value - operand
        elif operation == '*':
            return value * operand
        elif operation == '/':
            if operand == 0:
                raise ValueError("Cannot divide by zero.")
            return value / operand
        else:
            raise ValueError("Unsupported operation.")
    except ValueError:
        print(f"Error applying operation {operation} with operand {operand}.")
        return value

# --- 生成函数 ---

def generate_uuid(count):
    return [str(uuid.uuid4()) for _ in range(count)]

def generate_numeric(min_length, max_length, count, no_repeat=False):
    result = []
    for _ in range(count):
        if no_repeat:
            max_possible_length = 10
            length = random.randint(min_length, min(max_length, max_possible_length))
            result.append("".join(random.sample(string.digits, length)))
        else:
            length = random.randint(min_length, max_length)
            result.append("".join(random.choices(string.digits, k=length)))
    return result

def generate_alpha(min_length, max_length, count, case_sensitive='', no_repeat=False):
    if case_sensitive == 'lower':
        charset = string.ascii_lowercase
    elif case_sensitive == 'upper':
        charset = string.ascii_uppercase
    else:
        charset = string.ascii_letters

    result = []
    for _ in range(count):
        if no_repeat:
            max_possible_length = len(set(charset))
            length = random.randint(min_length, min(max_length, max_possible_length))
            result.append("".join(random.sample(charset, length)))
        else:
            length = random.randint(min_length, max_length)
            result.append("".join(random.choices(charset, k=length)))
    return result

def generate_alphanumeric(min_length, max_length, count, case_sensitive='', no_repeat=False):
    if case_sensitive == 'lower':
        charset = string.ascii_lowercase + string.digits
    elif case_sensitive == 'upper':
        charset = string.ascii_uppercase + string.digits
    else:
        charset = string.ascii_letters + string.digits

    result = []
    for _ in range(count):
        if no_repeat:
            max_possible_length = len(set(charset))
            length = random.randint(min_length, min(max_length, max_possible_length))
            result.append("".join(random.sample(charset, length)))
        else:
            length = random.randint(min_length, max_length)
            result.append("".join(random.choices(charset, k=length)))
    return result

def generate_from_charset(charset, min_length, max_length, count, no_repeat=False):
    """从给定字符集生成随机字符串"""
    if no_repeat:
        max_possible_length = len(set(charset))
        if min_length > max_possible_length:
            raise ValueError(f"当不重复时，长度不能超过字符集的唯一字符数 ({max_possible_length})")
        length = random.randint(min_length, min(max_possible_length, max_length))
    else:
        length = random.randint(min_length, max_length)

    if not charset:
        return [''] * count

    result = []
    for _ in range(count):
        if no_repeat:
            result.append("".join(random.sample(charset, length)))
        else:
            result.append("".join(random.choices(charset, k=length)))

    return result

def generate_hash(file_path, hash_algorithm):
    hash_obj = hashlib.new(hash_algorithm)
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def parse_hashes(hash_string):
    """解析哈希算法字符串，支持 'n' 和 'a'"""
    if hash_string == 'n':
        return ['md5', 'sha1', 'sha256', 'sha512']
    elif hash_string == 'a':
        return ['md5', 'sha1', 'sha256', 'sha512', 'sha3_224', 'sha3_256', 'sha3_384', 'sha3_512']
    else:
        algorithms = hash_string.split(',')
        valid_algorithms = []
        for algo in algorithms:
            algo = algo.lower().strip()  # 统一转为小写并去除空格
            if algo in hashlib.algorithms_available:
                valid_algorithms.append(algo)
            else:
                print(f"警告: 不支持的哈希算法 '{algo}'，已忽略")
        return valid_algorithms
# --- 表达式解析 ---

def parse_expression(expression):
    """
    将表达式字符串解析为一个列表，列表中的每个元素都是一个 (mode, params) 元组。
    """
    parts = []
    i = 0
    while i < len(expression):
        char = expression[i]
        if char.isalpha():
            j = i + 1
            while j < len(expression) and expression[j].isalnum():
                j += 1
            mode = expression[i:j]
            i = j
            if i < len(expression) and expression[i] == '(':
                j = i + 1
                while j < len(expression) and expression[j] != ')':
                    j += 1
                if j < len(expression):
                    param_str = expression[i + 1:j]
                    params = param_str.split(';')
                    parts.append((mode, params))
                    i = j + 1
                else:
                    print("错误: 表达式语法错误，缺少右括号")
                    return []
            else:
                # 对于没有括号的 n, a, an, u，params 设置为空列表
                parts.append((mode, []))
        elif char in ("'", '"'):
            j = i + 1
            while j < len(expression) and expression[j] != char:
                j += 1
            if j < len(expression):
                parts.append(('str', [expression[i + 1:j]]))  # 使用 'str' 作为字符串字面量的模式
                i = j + 1
            else:
                print("错误: 表达式语法错误，缺少结束引号")
                return []
        elif char.isspace() or char == ',' or char == '[' or char == ']':
            i += 1
        else:
            parts.append(('str', [char])) #直接当做字符串处理
            i += 1
    return parts


def generate_from_expression(expression, min_length, max_length, args):
    """解析表达式并生成字符串"""
    try:
        parsed_parts = parse_expression(expression)  # 先解析表达式
    except (SyntaxError, ValueError) as e:
        print(f"表达式解析错误: {e}")
        return []

    if not parsed_parts:
        return []

    result = []
    for _ in range(args.count):
        generated_string = ""
        for mode, params in parsed_parts:  # 遍历解析后的部分
            if mode == 'str':
                generated_string += params[0]  # 直接拼接字符串字面量
            else:
                length_param = params[0] if params else ''
                no_repeat = 'nr' in params
                case = next((p for p in params if p in ('s', 'S')), None)
                case_sensitive = 'lower' if case == 's' else 'upper' if case == 'S' else ''
                length = 0

                if length_param.isdigit():
                    length = int(length_param)
                elif length_param == 'r':
                    length = args.length or random.randint(min_length, max_length)
                else:
                    length = args.length or 8

                try:
                    if mode == 'n':
                        generated_string += generate_numeric(length, length, 1, no_repeat)[0]
                    elif mode == 'a':
                        generated_string += generate_alpha(length, length, 1, case_sensitive, no_repeat)[0]
                    elif mode == 'an':
                        generated_string += generate_alphanumeric(length, length, 1, case_sensitive, no_repeat)[0]
                    elif mode == 'cc':
                        custom_charset = "".join(params[1:]) if len(params) > 1 else ""
                        if args.input:  # 优先使用 -i 参数
                            custom_charset = args.input
                        if no_repeat and length > len(set(custom_charset)):
                            print(f"错误：在表达式 {expression} 的 cc 模式中，指定长度 {length} 大于唯一字符数 {len(set(custom_charset))}（不重复模式）")
                            return []
                        generated_string += generate_from_charset(custom_charset, length, length, 1, no_repeat)[0]
                    elif mode == 'u':
                        generated_string += generate_uuid(1)[0]
                except ValueError as e:
                    print(f"生成字符串时出错 (表达式: {expression}): {e}")
                    return []

        result.append(generated_string)
    return result


# --- 主函数 ---

def main():
    parser = argparse.ArgumentParser(description="随机字符串生成", usage="""
usage: rget.py [-h] [-l LENGTH | -r] [-c COUNT] [-s] [-S] [-nr] [-i INPUT] [-o OUTPUT] [-hash ALGORITHMS] [-nv] [-set SET] [-add [ADD ...]] [-rm REMOVE] [-up [UP ...]] [-list] -m MODE

随机字符串生成

    使用示例:
    rget -m u --count 5
    rget -m n -l 6 --count 10 -nr
    rget -m a -l 8 -s
    rget -m an -l 12 -c 3 -S -nr
    rget -m "[an(10;nr),@test.com]"
    rget -m "['1',n(10;nr),'K']"
    rget -m "[n(5;nr;r)]"
    rget -m w -add re aa '[W,n(10)]'
    rget -m w -add cc bb abcde
    rget -m w -rm aa
    rget -m w -up re aa '[W,n(12)]'
    rget -m w -list
    rget -m $aa

参数:
  -m MODE, --mode MODE  模式: u, n, a, an, cc, w, 或表达式, 或 $引用
  -l LENGTH, --length LENGTH
                        字符串长度 (与 -r 互斥)
  -r, --random-length   使用配置的最小和最大长度之间的随机长度 (与 -l 互斥)
  -c COUNT, --count COUNT
                        生成数量 (默认: 1)
  -s, --lower           仅小写 (仅适用于 a, an 模式)
  -S, --upper           仅大写 (仅适用于 a, an 模式)
  -nr, --no-repeat      不重复字符 (部分模式下可能导致长度受限)
  -i INPUT, --input INPUT
                        自定义字符集 (用于 cc 模式, 也可用于表达式中的 cc 函数)
  -o OUTPUT, --output OUTPUT
                        导出到文件
  -hash ALGORITHMS, --hash_algorithms ALGORITHMS
                        计算哈希值。支持的算法: md5, sha1, sha256, sha512,
                        sha3_224, sha3_256, sha3_384, sha3_512。
                        可以使用逗号分隔多个算法, 例如: -hash md5,sha256。
                        特殊值: 'n' (常用算法), 'a' (所有可用算法)。
  -nv                   不输出到控制台
  -add [ADD ...]        添加配置项 (仅在 -m w 时使用): 类型(re/cc) 名称 '值(表达式用双引号)'
  -rm REMOVE, --remove REMOVE  删除配置项 (仅在 -m w 时使用): 名称
  -up [UP ...]          更新配置项 (仅在 -m w 时使用): 类型(re/cc) 名称 '值(表达式用双引号)'
  -list, --list         列出所有配置 (仅在 -m w 时使用)

注意:
  - 表达式模式下，字符串字面量用单引号或双引号括起来, 例如:  ['123', n(5)]
  - w 模式用于管理自定义配置 (存储在 rget.ini 文件中)
  - 使用 $引用 模式引用自定义配置, 例如: rget -m $myconfig
  - 当使用-add和-up添加表达式的时候，表达式务必使用双引号。
    """)
    parser.add_argument('-m', '--mode', type=str, required=True, help="模式或表达式")
    length_group = parser.add_mutually_exclusive_group()
    length_group.add_argument('-l', '--length', type=int, help="字符串长度")
    length_group.add_argument('-r', '--random-length', action='store_true', help="随机长度")
    parser.add_argument('-c', '--count', type=int, default=1, help="生成数量")
    parser.add_argument('-s', '--lower', action='store_true', help="仅小写")
    parser.add_argument('-S', '--upper', action='store_true', help="仅大写")
    parser.add_argument('-nr', '--no-repeat', action='store_true', help="不重复字符")
    parser.add_argument('-i', '--input', type=str, help="自定义字符集")
    parser.add_argument('-o', '--output', type=str, help="导出到文件")
    parser.add_argument('-hash', help="哈希算法", dest='hash_algorithms', metavar='ALGORITHMS', type=parse_hashes)
    parser.add_argument('-nv', action='store_true', help="不输出到控制台")
    parser.add_argument('-set', help="设置配置")

    # -m w 的子命令 (直接添加到主解析器)
    parser.add_argument('-add', nargs=3, help='添加配置: 类型(re/cc) 名称 值')  # 使用 nargs=3
    parser.add_argument('-rm', dest='remove', type=str, help='删除配置: 名称')
    parser.add_argument('-up', nargs=3, help='更新配置: 类型(re/cc) 名称 值')  # 使用 nargs=3
    parser.add_argument('-list', action='store_true', help='列出所有配置')

    args = parser.parse_args()

    min_length = get_config_value('Settings',"min_length", 1)
    max_length = get_config_value('Settings','max_length', 32767)

    if args.set:
        try:
            key, operation = args.set.split('=', 1)
            key = key.strip()
            operation = operation.strip()
            if key == "min_length":
                min_length = int(get_config_value('Settings',"min_length", 1))
                new_value = apply_operation(min_length, *operation.split())
                set_config_value('Settings',"min_length", new_value)
                print(f"min_length 设置为 {new_value}")
            elif key == "max_length":
                max_length = int(get_config_value('Settings','max_length', 32767))
                new_value = apply_operation(max_length, *operation.split())
                set_config_value('Settings','max_length', new_value)
                print(f"max_length 设置为 {new_value}")
            else:
                print("无效的配置键，请使用 min_length 或 max_length。")
        except Exception as e:
            print(f"设置错误：{e}")
        return
    if args.mode == 'w':
        if args.add:
            config_type, config_name, config_value = args.add  # 直接解包

            if config_type not in ('re', 'cc'):
                print("错误: 配置类型必须是 're' (表达式) 或 'cc' (自定义字符集)")
                return
            if config.has_section(config_name):
                print("错误，配置已存在")
                return

            set_config_value(config_name, 'type', config_type)
            set_config_value(config_name, 'value', config_value)
            print(f"已添加配置: {config_name}")



        elif args.remove:  # 使用 args.remove
            config_name = args.remove
            if config.has_section(config_name):
                config.remove_section(config_name)
                with open(config_file, 'w') as configfile:
                    config.write(configfile)
                print(f"已删除配置: {config_name}")
            else:
                print(f"配置 '{config_name}' 不存在")

        elif args.up:
            config_type, config_name, config_value = args.up  # 直接解包

            if config_type not in ('re', 'cc'):
                print("错误: 配置类型必须是 're' (表达式) 或 'cc' (自定义字符集)")
                return

            if config.has_section(config_name):
                set_config_value(config_name, 'type', config_type)
                set_config_value(config_name, 'value', config_value)
                print(f"已更新配置: {config_name}")
            else:
                print(f"配置 '{config_name}' 不存在")

        elif args.list:
            if len(config.sections()) > 1:
                print("自定义配置:")
                for section in config.sections():
                    if section != 'Settings':
                        config_type = config.get(section, 'type')
                        config_value = config.get(section, 'value')
                        print(f"  {section}: 类型={config_type}, 值={config_value}")
            else:
                print("没有自定义配置")
        else:
            print("错误：在 -m w 模式下，必须指定 -add, -del, -up 或 -list 中的一个")  # 更正此处的错误消息
        return
    # --- 处理 $ 引用 ---
    if args.mode.startswith('$'):
        config_name = args.mode[1:]  # 去掉 $
        if config.has_section(config_name):
            config_type = get_config_value(config_name, 'type', '')
            config_value = get_config_value(config_name, 'value', '')
            if config_type == 're':
                # config_value = config_value.replace("'", '"')  # 不需要了
                try:
                    result = generate_from_expression(config_value, min_length, max_length, args)
                except ValueError as e:
                    print(e)
                    return
                except Exception as e:
                    print(f"出了点问题: {e}")
                    return
            elif config_type == 'cc':
                if isinstance(config_value, int):  # 检查是否为整数（可能是默认值）
                    print(f"配置错误：值不能为空")
                    return
                else:
                    if args.length is not None:
                        result = generate_from_charset(str(config_value),  args.length, args.length, args.count,
                                                        args.no_repeat)  # config_value转字符串
                    else:
                        result = generate_from_charset(str(config_value), min_length, max_length, args.count, args.no_repeat)  # config_value转字符串
            else:
                print(f"错误: 配置 '{config_name}' 的类型无效")
                return
        else:
            print(f"错误: 配置 '{config_name}' 不存在")
            return



    elif args.mode.startswith('[') and args.mode.endswith(']'):
        result = generate_from_expression(args.mode, min_length, max_length, args)
    elif args.mode == 'u':
        result = generate_uuid(args.count)
    else:  # 单一模式
        current_min_length = min_length
        current_max_length = max_length

        if args.length is not None:  # 指定了 -l
            current_min_length = args.length
            current_max_length = args.length
        elif args.random_length:  # 指定了 -r
            # -r 时不需要特别设置，使用配置文件中的 min_length 和 max_length
            pass
        else: #没有指定-r或-l
            current_min_length = 8
            current_max_length = 8

        # 不重复字符检查 (只在指定了 -l 时检查)
        if args.no_repeat and args.length:
            max_possible_length = 0
            if args.mode == 'n':
                max_possible_length = 10
            elif args.mode == 'a':
                max_possible_length = 26 if args.lower or args.upper else 52
            elif args.mode == 'an':
                max_possible_length = 36 if args.lower or args.upper else 62
            elif args.mode == 'cc':
                max_possible_length = len(set(args.input)) if args.input else 0

            if args.length > max_possible_length:
                raise ValueError(
                    f"对于模式 '{args.mode}'，使用 '-nr' 时的最大长度为 {max_possible_length}。"
                )

        # 生成
        if args.mode == 'n':
            result = generate_numeric(current_min_length, current_max_length, args.count, args.no_repeat)
        elif args.mode == 'a':
            result = generate_alpha(current_min_length, current_max_length, args.count,
                                     'lower' if args.lower else 'upper' if args.upper else '', args.no_repeat)
        elif args.mode == 'an':
            result = generate_alphanumeric(current_min_length, current_max_length, args.count,
                                            'lower' if args.lower else 'upper' if args.upper else '', args.no_repeat)
        elif args.mode == 'cc':
            if not args.input:
                raise ValueError("cc 模式需要使用 -i 参数指定字符集")
            result = generate_from_charset(args.input, current_min_length, current_max_length, args.count,
                                             args.no_repeat)

    if not args.nv:
        for item in result:
            print(item)

    if args.output:
        output_file_path = args.output
        with open(output_file_path, 'w') as file:
            for item in result:
                file.write(f"{item}\n")
        print(f"字符串已导出到: {output_file_path}")
    else:
        temp_dir = tempfile.gettempdir()
        output_file_path = os.path.join(temp_dir, "generated_strings.txt")
        with open(output_file_path, 'w') as file:
            for item in result:
                file.write(f"{item}\n")

    if args.hash_algorithms:
        print("\n" + "-" * 50)
        for hash_algorithm in args.hash_algorithms:
            hash_value = generate_hash(output_file_path, hash_algorithm)
            print(f"{hash_algorithm.upper()}: {hash_value}")

if __name__ == '__main__':
    main()
