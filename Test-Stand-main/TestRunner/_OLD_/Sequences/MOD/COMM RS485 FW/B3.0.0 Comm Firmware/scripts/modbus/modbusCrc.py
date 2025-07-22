from .endian import endian_little_append

def ModbusRtuCrcCalc(data):

    crc = 0xFFFF
    for pos in data:
        crc ^= pos 
        for i in range(8):
            if ((crc & 1) != 0):
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc
    
def modbusCRCAppend(data):

    crc = ModbusRtuCrcCalc(data)

    endian_little_append(data,crc,2)

    return data