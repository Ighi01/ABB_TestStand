using System;
using System.IO;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace TestStandJsonParser
{
    public class Config
    {
        public int typeOfTesting { get; set; }
        public string TestName { get; set; }
        public string TestTypeName { get; set; }
        public List<Meter> Meters { get; set; }
        public List<MBusMeter> MBusMeters { get; set; }
        public bool CloseWinSam { get; set; }
        public string VisaNameInput { get; set; }

        public void GetConfigInfo(out int typeOfTesting, out string testName, out string testTypeName)
        {
            typeOfTesting = this.typeOfTesting;
            testName = this.TestName;
            testTypeName = this.TestTypeName;
        }

        public int GetICTSlots()
        {
            return Meters.Count;
        }

	public int GetICTSlotsMBus()
        {
            return MBusMeters.Count;
        }
    }

    public class Meter
    {
        public int Protocol { get; set; }  // Modbus = 0, TCP/IP = 1
        public string Port { get; set; }
        public int SlaveAddress { get; set; }
        public string IP { get; set; }
        public string PortTCP { get; set; }
        public int BaudRate { get; set; }  // 9600 = 0, 19200 = 1, 38400 = 2, 57600 = 3, 115200 = 4
        public int Parity { get; set; }    // None = 0, Odd = 1, Even = 2
	public int InputChannel { get; set; }

        public void GetMeterInfo(out int protocol, out string port, out int slaveAddress, out string ip, out string portTCP, out int baudRate, out int parity, out int inputChannel)
        {
            protocol = this.Protocol;
            port = this.Port;
            slaveAddress = this.SlaveAddress;
            ip = this.IP;
            portTCP = this.PortTCP;
            baudRate = this.BaudRate;
            parity = this.Parity;
            inputChannel = this.InputChannel;
        }
    }

    public class MBusMeter
    {
        public string Port { get; set; }
        public int MeterAddress { get; set; }
        public int BaudRate { get; set; }
        public int InputChannel { get; set; }

        public void GetMeterInfo(out string port, out int meterAddress, out int baudRate, out int inputChannel)
        {
            port = this.Port;
            meterAddress = this.MeterAddress;
            baudRate = this.BaudRate;
            inputChannel = this.InputChannel;
        }
    }

    public static class JsonParser
    {
        public static Config ReadConfig(string path)
        {
            string json = File.ReadAllText(path);
            var config = JsonConvert.DeserializeObject<Config>(json);
            return config;
        }
    } 
} 