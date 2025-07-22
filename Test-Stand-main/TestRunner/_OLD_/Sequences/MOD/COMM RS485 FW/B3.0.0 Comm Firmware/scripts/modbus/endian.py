def endian_big_append(frame:bytearray,value,size):

    if type(value) == list:
        for i in range(int(size/2)):
            value_bytes = value[i].to_bytes(2,'big')
            frame.append(value_bytes[0])
            frame.append(value_bytes[1])
            
    else:
        value_bytes = value.to_bytes(size,'big')
        for i in range(size):
            frame.append(value_bytes[i])
            
def endian_little_append(frame,value,size):
    
    for i in range(size):
        frame.append((value >> i * 8) & 0xff)
        
def endian_big_append_bits(frame,value,number):

    for i in range(number):

        if(i % 8 == 0):
            frame.append(0)

        if hasattr(value, "__len__"):
            frame[-1] |= value[i] << (i % 8)
        else:
            frame[-1] |= value << (i % 8)
         

        