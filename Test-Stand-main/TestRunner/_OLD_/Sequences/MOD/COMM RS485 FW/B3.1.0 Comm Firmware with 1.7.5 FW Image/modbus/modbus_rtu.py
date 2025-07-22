import time
from .modbusCommon import ModbusRtuFCodes
from .modbusRtuRequest import ModbusRtuRequest
VERSION = '1.0.1'

DELAY = 0.05

class ModbusRtuCommError(Exception):
    pass

class ModbusRtuClient:
    def __init__(self, comx, timeout = 1):
        self.comx = comx
        self.resp_timeout = timeout

    def read_frame_timeout(self, count):

        start = time.time()
        res = []

        while 1:
            res = self.comx.read(count)

            if count == len(res):
                break

            if time.time() - start > self.resp_timeout:
                res = []
                break
        return res


    def read_holding_registers(self, id, address, count = 1):

        request = ModbusRtuRequest(id, ModbusRtuFCodes.READ_HOLDING_REGISTERS, address, count)

        self.comx.write(request.packet)

        #expected replay length should be id*1+func_code*1+length*1+count*2+crc*2=count*2+5

        if id != 0:

            res = self.read_frame_timeout(count*2+5)

        else:

            res = []

        time.sleep(DELAY)

        return res


    def write_holding_registers(self, id:int, address:int, count:int, data):
        
        request = ModbusRtuRequest(id, ModbusRtuFCodes.WRITE_MULTIPLE_REGISTERS, address, count, data)

        self.comx.write(request.packet)

        if id != 0:

            res = self.read_frame_timeout(8)

        else:

            res = []

        time.sleep(DELAY)

        return res

    def write_single_register(self, id, address, val):

        request = ModbusRtuRequest(id, ModbusRtuFCodes.WRITE_SINGLE_REGISTER, address, val)

        self.comx.write(request.packet)

        if id != 0:

            res = self.read_frame_timeout(8)

        else:

            res = []

        time.sleep(DELAY)

        return res


    def read_coils(self, id, address, count):

        request = ModbusRtuRequest(id, ModbusRtuFCodes.READ_COILS, address, count)

        self.comx.write(request.packet)

        res = self.read_frame_timeout(5 + count)

        time.sleep(DELAY)

        if res == b'':
            raise ModbusRtuCommError("no response read coil")

        return res


    def write_coils(self, id, address, count, data):

        request = ModbusRtuRequest(id, ModbusRtuFCodes.WRITE_MULTIPLE_COILS, address, count, data)

        self.comx.write(request.packet)

        res = self.read_frame_timeout(8)

        time.sleep(DELAY)

        if res == b'':
            raise ModbusRtuCommError("no response write coll")

        return res


    def write_single_coil(self, id, address, state):

        request = ModbusRtuRequest(id, ModbusRtuFCodes.WRITE_SINGLE_COIL, address, state)

        self.comx.write(request.packet)

        res = self.read_frame_timeout(8)

        time.sleep(DELAY)

        if res == b'':
            raise ModbusRtuCommError("no response write coll")

        return res

