"""
雪花ID算法实现
"""
import time
import threading


class Snowflake:
    """
    雪花算法生成唯一ID
    结构：符号位(1) + 时间戳(41) + 数据中心ID(5) + 机器ID(5) + 序列号(12)
    """

    def __init__(self, datacenter_id=1, machine_id=1):
        # 起始时间戳：2020-01-01
        self.epoch = 1577836800000

        # 各部分位数
        self.datacenter_id_bits = 5
        self.machine_id_bits = 5
        self.sequence_bits = 12

        # 各部分最大值
        self.max_datacenter_id = -1 ^ (-1 << self.datacenter_id_bits)
        self.max_machine_id = -1 ^ (-1 << self.machine_id_bits)

        # 各部分左移位数
        self.machine_id_shift = self.sequence_bits
        self.datacenter_id_shift = self.sequence_bits + self.machine_id_bits
        self.timestamp_left_shift = self.sequence_bits + self.machine_id_bits + self.datacenter_id_bits

        # 序列号掩码
        self.sequence_mask = -1 ^ (-1 << self.sequence_bits)

        # 初始化
        self.datacenter_id = datacenter_id
        self.machine_id = machine_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()

    def _til_next_millis(self, last_timestamp):
        """等待直到下一毫秒"""
        timestamp = self._get_current_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._get_current_timestamp()
        return timestamp

    def _get_current_timestamp(self):
        """获取当前时间戳（毫秒）"""
        return int(time.time() * 1000)

    def get_id(self):
        """获取下一个雪花ID"""
        with self.lock:
            timestamp = self._get_current_timestamp()

            # 如果当前时间小于上一时间戳，说明系统时钟回拨
            if timestamp < self.last_timestamp:
                raise Exception("Clock moved backwards. Refusing to generate ID.")

            # 如果是同一时间戳，则序列号+1
            if self.last_timestamp == timestamp:
                self.sequence = (self.sequence + 1) & self.sequence_mask
                # 如果序列号溢出，则等待下一毫秒
                if self.sequence == 0:
                    timestamp = self._til_next_millis(self.last_timestamp)
            else:
                # 不同时间戳，序列号从0开始
                self.sequence = 0

            self.last_timestamp = timestamp

            # 计算ID
            new_id = ((timestamp - self.epoch) << self.timestamp_left_shift) | \
                     (self.datacenter_id << self.datacenter_id_shift) | \
                     (self.machine_id << self.machine_id_shift) | \
                     self.sequence

            return new_id


# 全局雪花ID生成器
snowflake = Snowflake(datacenter_id=1, machine_id=1)


def generate_id():
    """生成一个新的雪花ID"""
    return snowflake.get_id()


if __name__ == '__main__':
    # 测试
    ids = [generate_id() for _ in range(10)]
    print("生成的雪花ID：")
    for i, id in enumerate(ids, 1):
        print(f"{i}. {id}")
