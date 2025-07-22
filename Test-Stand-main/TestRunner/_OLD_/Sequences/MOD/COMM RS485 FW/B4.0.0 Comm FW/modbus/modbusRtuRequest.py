from .modbusCrc import modbusCRCAppend
from .modbusCommon import ModbusRtuFCodes
from .endian import endian_big_append
from .endian import endian_big_append_bits
class ModbusRtuRequest:
    
    def __init__(self, id:int, func_code:int, address:int, value1, value2 = 0):
        addss_bytes = address.to_bytes(2,'big')
        self.packet = bytearray()
        self.packet.append(id)
        self.packet.append(func_code)
        self.packet.append(addss_bytes[0])
        self.packet.append(addss_bytes[1])
        
        if func_code & 0xf0 == 0x80:

            self.packet.append(value1)
             
        elif func_code == ModbusRtuFCodes.WRITE_MULTIPLE_REGISTERS:
            
            self.packet.append(0)
            self.packet.append(value1)
            self.packet.append(value1*2)

            endian_big_append(self.packet,value2,2 * value1)

        elif func_code == ModbusRtuFCodes.WRITE_SINGLE_COIL:
            if value1:
                self.packet.append(0xFF)
            else:
                self.packet.append(0)
            self.packet.append(0)

        elif func_code == ModbusRtuFCodes.WRITE_SINGLE_REGISTER:
            
            endian_big_append(self.packet,value1,2)

        else:

            endian_big_append(self.packet,value1,2)

            if func_code == ModbusRtuFCodes.WRITE_MULTIPLE_COILS:

                self.packet.append(int(value1/8)+1)
                endian_big_append_bits(self.packet,value2,value1)

        self.packet = modbusCRCAppend(self.packet)

