import pyvisa
import time
import sys

class Instrument:
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.instrument = None

    def connect(self, instrument_visa_name):
        try:
            available_resources = self.rm.list_resources()
            for resource in available_resources:
                if resource == instrument_visa_name:
                    self.instrument = self.rm.open_resource(resource)
                    try:
                        self.instrument.query('*IDN?')
                        return True
                    except pyvisa.VisaIOError:
                        self.instrument = None
                        return False
            return False
        except pyvisa.VisaIOError:
            return False

    def close_output(self, ch_number=1):
        if self.instrument:
            command = (
		f'SOURce{ch_number}:OUTPut:STATe OFF\n'
	    )
            self.instrument.write(command)
            return True
        else:
            return False

    def send_pulse(self, ch_number=1, num_pulse=1, frequency_hz="1", amplitude="MAX", offset="0", width_ms="30"):
        if self.instrument is None:
            return False
        try:
            command = (
                f'SOURce{ch_number}:FUNCtion:SHAPe PULSe\n'
                f'SOURce{ch_number}:FREQuency {frequency_hz}\n'
                f'SOURce{ch_number}:VOLTage:AMPLitude {amplitude}\n'
                f'SOURce{ch_number}:VOLTage:OFFSet {offset}\n'
                f'SOURce{ch_number}:FUNCtion:PULSe:WIDTh {float(width_ms)/1000}\n'
                f'SOURce{ch_number}:OUTPut:STATe ON\n'
            )
            self.instrument.write(command)
            time.sleep(num_pulse / float(frequency_hz) + 0.05/ float(frequency_hz))
            self.close_output(ch_number)
            return True
        except pyvisa.VisaIOError:
            return False

    def send_dc(self, ch_number=1, dc_offset=5):
        if self.instrument is None:
            return False
        try:
            command = (
                f'SOURce{ch_number}:FUNCtion:SHAPe SIN\n'                    
                f'SOURce{ch_number}:VOLTage:AMPLitude 0.001\n'     
                f'SOURce{ch_number}:VOLTage:OFFSet {dc_offset}\n'    
                f'SOURce{ch_number}:OUTPut:STATe ON\n'                      
            )
            self.instrument.write(command)
            return True
        except pyvisa.VisaIOError:
            return False

    def disconnect(self):
        if self.instrument:
            self.instrument.close()
            self.instrument = None

def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    visa_name = sys.argv[1]
    ch_number = int(sys.argv[2])

    if len(sys.argv) == 3:
        instrument = Instrument()
        if instrument.connect(visa_name):
            instrument.close_output(ch_number)
            instrument.disconnect()
        else:
            print("Connection failed.")
        sys.exit(1)

    elif len(sys.argv) == 4:
        offset = sys.argv[3]
        instrument = Instrument()
        if instrument.connect(visa_name):
            instrument.send_dc(ch_number, offset)
            instrument.disconnect()
        else:
            print("Connection failed.")
        sys.exit(1)

    ch_number = int(sys.argv[2])
    num_pulse = int(sys.argv[3])
    frequency_hz = sys.argv[4]
    amplitude = sys.argv[5]
    offset = sys.argv[6]
    width_ms = int(sys.argv[7])

    instrument = Instrument()
    if instrument.connect(visa_name):
        instrument.send_pulse(ch_number, num_pulse, frequency_hz, amplitude, offset, width_ms)
        instrument.disconnect()
    else:
        print("Connection failed.")

if __name__ == "__main__":
    main()