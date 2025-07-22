import argparse
import sys
import serial
from modbus.modbus_rtu import ModbusRtuClient
from device_map.MOD_map import enable_switching_via_input, enable_switching_via_communication, update_initialize, update_run, update_block_data_upload
import time

IMAGE_CHUNK_SIZE = 128

def update_comm_app(com,id,update_file_name):

    client = ModbusRtuClient(com,30)
    
    # print("disable external switching")
    # client.write_holding_registers(id, enable_switching_via_input, 2, 0x0000)

    print("initialize")
    response = client.write_single_register(id, update_initialize, 0xF5F5)

    print(response)

    #TODO: nbr of bytes in response is not correct
    #TODO: add checking of CRC

    update_file = open(update_file_name, "rb")
    print(update_file_name + "\n")
    if update_file == None:
        print("file not opened")

    block_number = 0
    
    buffer = update_file.read()
    buffer_offset = 0

    file_size = len(buffer)

    buffer_step = IMAGE_CHUNK_SIZE

    print("send chunks")
    while True:

        if file_size - buffer_offset >= buffer_step:
            pass
        elif file_size - buffer_offset > 0:
            padding_size = IMAGE_CHUNK_SIZE - (file_size - buffer_offset) % IMAGE_CHUNK_SIZE
            buffer += bytearray(b'\xff') * padding_size
        else:
            break

        block_number += 1

        image_chunk = int.from_bytes(buffer[buffer_offset:buffer_offset+IMAGE_CHUNK_SIZE],'big')

        response = client.write_holding_registers(id, update_block_data_upload, int(buffer_step / 2), image_chunk)
        if(len(response) != 8):
            print("false response " + str(response) + " real length " + str(len(response)) + " expected 8")
            break

        buffer_offset += buffer_step

        print("transfer progress: " + str(buffer_offset) + "/" + str(file_size) + " package size: " + str(buffer_step) )
    
    print("start update")
    time_start = time.time()
    resp = client.write_single_register(id, update_run, 0xF5F5)
    print("decrypt time: " + str(time.time() - time_start) + " s")

    print(resp)

if __name__ == '__main__':  
    
    parser = argparse.ArgumentParser()

    parser.add_argument("ID", type=int,
        help='modbus ID of target module.')

    parser.add_argument("P", type=str,   metavar="COMX",
        help='Serial port name.')

    parser.add_argument("F", type=str,
        help='update file name')
        
    parser.add_argument("-B", required = False, type=int, default = 19200, help='baudrate setup (default 19200)')

    args = parser.parse_args(sys.argv[1:])

    client = serial.Serial(args.P,args.B,serial.EIGHTBITS,serial.PARITY_EVEN,serial.STOPBITS_ONE,timeout=0.2)

    time_start = time.time()

    update_comm_app(client, args.ID, args.F)

    print("elapsed time: " + str(time.time() - time_start) + " s")
