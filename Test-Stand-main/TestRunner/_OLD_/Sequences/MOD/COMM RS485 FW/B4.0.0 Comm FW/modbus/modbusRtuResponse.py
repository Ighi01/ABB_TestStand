from .modbusCrc import ModbusRtuCrcCalc

class ModbusRtuResponse:
    def __init__(self, _packet=bytearray()):
        self.packet = _packet

    def crc_ok(self):
        data = list(self.packet)
        crc_high = data.pop(-1)
        crc_low = data.pop(-1)
        crc = crc_low | crc_high << 8
        crc_calc = ModbusRtuCrcCalc(data)

        if crc == crc_calc:
            return True
        else:
            return False

    def function_code(self):
        return self.packet[1]

    def error_code(self):
        return self.packet[2]

    def byte_count(self):
        return self.packet[2]

    def length(self):
        return len(self.packet)

    def get_reg_data(self, address_start = 0, len = 1):
        data_block = []
        data_offset = 3
        data_block_offset = address_start*2+data_offset

        for i in range(data_block_offset,len*2+data_block_offset,2):
            data_block.append(int.from_bytes(self.packet[i:i+2], byteorder = 'big'))

        return data_block

    def get_coils_data(self, count = 1):
        coils_data = []
        data_offset = 3

        for i in range(count):
            coils_data.append(self.packet[data_offset+i])

        return coils_data
