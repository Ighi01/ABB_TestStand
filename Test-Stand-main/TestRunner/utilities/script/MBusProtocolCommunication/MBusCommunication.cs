using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO.Ports;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace MbusLibrary
{

    public enum LogType
    {
        Error = 0x2E,
        Alarm = 0x30,
        Warning = 0x32
    }

    public class MbusLogEvent
    {
        public LogType Type { get; set; }
        public int RecordNumber { get; set; }
        public int EventId { get; set; }
        public string EventDescription { get; set; }
        public string Timestamp { get; set; }
        public int DurationSeconds { get; set; }

        public override string ToString()
        {
            return $"Log Event [{Type} - Record {RecordNumber}] - ID: {EventId} ({EventDescription}), Timestamp: {Timestamp}, Duration: {DurationSeconds}s";
        }
    }

    public class MbusTelegram
    {
        public byte FrameType { get; set; }
        public byte ControlField { get; set; }
        public byte AddressField { get; set; }
        public byte ControlInformationField { get; set; }
        public byte[] UserData { get; set; }
        public bool IsMoreDataFollow { get; set; }
        public MbusFixedDataHeader FixedHeader { get; set; }
        public List<MbusDataRecord> DataRecords { get; set; }
        public bool IsAcknowledgement => FrameType == MbusMaster.MBUS_ACK;
        public bool IsLongFrame => FrameType == MbusMaster.MBUS_START_LONG_FRAME;
        public bool IsShortFrame => FrameType == MbusMaster.MBUS_START_SHORT_FRAME;

        public MbusTelegram()
        {
            UserData = Array.Empty<byte>();
            FixedHeader = new MbusFixedDataHeader();
            DataRecords = new List<MbusDataRecord>();
        }
    }

    public class MbusFixedDataHeader
    {
        public uint IdentificationNumber { get; set; }
        public string IdentificationNumberStr { get; set; }
        public ushort Manufacturer { get; set; }
        public byte Version { get; set; }
        public byte Medium { get; set; }
        public byte AccessNumber { get; set; }
        public byte Status { get; set; }
        public ushort Signature { get; set; }
        public byte ActualFrameAddress { get; set; }

        public override string ToString()
        {
            return $"ID: {IdentificationNumberStr} ({IdentificationNumber}), Manu: {Manufacturer:X4}, Ver: {Version:X2}, Medium: {Medium:X2}, Access#: {AccessNumber}, Status: {Status:X2}";
        }
    }

    public class MbusDataRecord
    {
        public byte DIF { get; set; }
        public List<byte> DIFEs { get; private set; } = new List<byte>();
        public byte VIF { get; set; }
        public List<byte> VIFEs { get; private set; } = new List<byte>();
        public byte[] RawDataValue { get; set; } = Array.Empty<byte>();

        public override string ToString()
        {
            var sb = new StringBuilder();
            sb.Append($"DIF=0x{DIF:X2}");
            if (DIFEs.Count > 0) sb.Append($", DIFEs=[{string.Join(",", DIFEs.Select(b => $"0x{b:X2}"))}]");
            sb.Append($", VIF=0x{VIF:X2}");
            if (VIFEs.Count > 0) sb.Append($", VIFEs=[{string.Join(",", VIFEs.Select(b => $"0x{b:X2}"))}]");
            sb.Append($", Data=[{BitConverter.ToString(RawDataValue).Replace("-", " ")}]");
            return sb.ToString();
        }
    }

    public class MbusReadResult
    {
        public bool Found { get; set; } = false;
        public object Value { get; set; }
        public string Unit { get; set; } = string.Empty;
        public string ErrorMessage { get; set; }
        public byte? LastVife { get; set; }

        public override string ToString()
        {
            if (!string.IsNullOrEmpty(ErrorMessage)) return ErrorMessage;
            if (!Found) return "Value not found or could not be interpreted.";
            if (LastVife.HasValue)
            {
                return $"Value = {Value}, Unit = {Unit}, Last VIFE = 0x{LastVife.Value:X2}";
            }
            return $"Value = {Value}, Unit = {Unit}";
        }
    }

    public class ReadableFixedHeader
    {
        public string SerialNumber { get; set; }
        public double SerialNumberNumeric { get; set; }
        public string ManufacturerCode { get; set; }
        public string ManufacturerName { get; set; }
        public double Version { get; set; }
        public double MediumCode { get; set; }
        public string MediumType { get; set; }
        public double AccessNumber { get; set; }
        public string StatusRawHex { get; set; }
        public List<string> StatusDecoded { get; set; }
        public double Signature { get; set; }
	public double FrameAddress { get; set; }

        public ReadableFixedHeader()
        {
            StatusDecoded = new List<string>();
        }

        public override string ToString()
        {
            var sb = new StringBuilder();
            sb.AppendLine($"Serial Number: {SerialNumber} (Numeric: {SerialNumberNumeric})");
            sb.AppendLine($"Manufacturer: {ManufacturerName} (Code: {ManufacturerCode})");
            sb.AppendLine($"Version: {Version}");
            sb.AppendLine($"Medium: {MediumType} (Code: {MediumCode})");
            sb.AppendLine($"Access Number: {AccessNumber}");
            sb.AppendLine($"Status Byte (Hex): {StatusRawHex}");
            if (StatusDecoded.Any())
            {
                sb.AppendLine("Decoded Status:");
                foreach (var status in StatusDecoded)
                {
                    sb.AppendLine($"  - {status}");
                }
            }
            else if (StatusRawHex == "0x00")
            {
                 sb.AppendLine("Decoded Status: No errors or specific status active");
            }
            sb.AppendLine($"Signature: 0x{((ushort)Signature):X4}");
            return sb.ToString();
        }
    }

    public class MbusMaster : IDisposable
    {
        private SerialPort _serialPort;
        private string _portName;
        private int _baudRate = 2400;
        private Parity _parity = Parity.Even;
        private int _dataBits = 8;
        private StopBits _stopBits = StopBits.One;
        private int _readTimeout = 5000;
        private int _interTelegramDelay = 200;
        private byte _fcb = 0;

        private MbusFixedDataHeader _cachedFixedHeader;
        private List<MbusDataRecord> _cachedDataRecords;
        private byte _lastCachedAddress = 0xFF;
        private bool _isDataCached = false;

        internal const byte MBUS_START_LONG_FRAME = 0x68;
        internal const byte MBUS_START_SHORT_FRAME = 0x10;
        internal const byte MBUS_STOP = 0x16;
        internal const byte MBUS_ACK = 0xE5;

        private const byte C_SND_NKE = 0x40;
        private const byte C_SND_UD_FCB0 = 0x53;
        private const byte C_SND_UD_FCB1 = 0x73;
        private const byte C_REQ_UD2_FCB0 = 0x5B;
        private const byte C_REQ_UD2_FCB1 = 0x7B;
        private const byte C_RSP_UD = 0x08;
        private const byte CI_RSP_VARIABLE = 0x72;

        public MbusMaster(string portName, int baudRate = 2400, int readTimeout = 5000)
        {
            _portName = portName;
            _baudRate = baudRate;
            _serialPort = new SerialPort();
            _readTimeout = readTimeout;
            _cachedDataRecords = new List<MbusDataRecord>();
        }
        
        public static int SumArray(byte[] array)
        {
            int sum = 0;
            foreach (int el in array)
            {
                sum += el;
            }
            return sum;
        }

        public bool Open()
        {
            try
            {
                if (_serialPort != null && !_serialPort.IsOpen)
                {
                    _serialPort.PortName = _portName;
                    _serialPort.BaudRate = _baudRate;
                    _serialPort.Parity = _parity;
                    _serialPort.DataBits = _dataBits;
                    _serialPort.StopBits = _stopBits;
                    _serialPort.Handshake = Handshake.None;
                    _serialPort.ReadTimeout = _readTimeout;
                    _serialPort.WriteTimeout = 500;
                    _serialPort.Open();
                    _serialPort.DiscardInBuffer();
                    _serialPort.DiscardOutBuffer();
                    InvalidateCache();
                }
                return _serialPort?.IsOpen ?? false;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error opening M-Bus port {_portName}: {ex.Message}");
                return false;
            }
        }

        public void Close()
        {
            try
            {
                if (_serialPort != null && _serialPort.IsOpen)
                {
                    _serialPort.Close();
                }
                InvalidateCache(); 
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error closing M-Bus port {_portName}: {ex.Message}");
            }
        }
        
        public void InvalidateCache()
        {
            _cachedFixedHeader = null;
            _cachedDataRecords.Clear();
            _isDataCached = false;
            _lastCachedAddress = 0xFF;
        }

        public async Task<bool> InitializeDeviceAsync(byte address, int maxAttempts = 3, int ackTimeoutMilliseconds = 250, int delayBetweenAttemptsMilliseconds = 300)
        {
            InvalidateCache();
            byte[] frame = new byte[5];
            frame[0] = MBUS_START_SHORT_FRAME;
            frame[1] = C_SND_NKE;
            frame[2] = address;
            frame[3] = CalculateMbusChecksum(frame, 1, 2);
            frame[4] = MBUS_STOP;

            if (maxAttempts <= 0) maxAttempts = 1;

            for (int attempt = 0; attempt < maxAttempts; attempt++)
            {
                try
                {
                    await SendFrameAsync(frame);
                    _fcb = 1;

                    byte[] ackResponse = await ReceiveFrameRawAsync(ackTimeoutMilliseconds);

                    if (ackResponse != null && ackResponse.Length == 1 && ackResponse[0] == MBUS_ACK)
                    {
                        return true;
                    }
                }
                catch (MbusException) { }
                catch (InvalidOperationException) { return false; }
                catch (Exception) { }

                if (attempt < maxAttempts - 1)
                {
                    await Task.Delay(delayBetweenAttemptsMilliseconds);
                }
            }
            return false;
        }

        public bool InitializeDevice(byte address, int maxAttempts = 3, int ackTimeoutMilliseconds = 250, int delayBetweenAttemptsMilliseconds = 300)
        {
            try
            {
                return InitializeDeviceAsync(address, maxAttempts, ackTimeoutMilliseconds, delayBetweenAttemptsMilliseconds).GetAwaiter().GetResult();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"InitializeDevice (sync wrapper) Exception: {ex.Message}");
                return false;
            }
        }
        
        private async Task<Tuple<MbusFixedDataHeader, List<MbusDataRecord>, int>> FetchAndParseAllDeviceDataAsync(byte address)
        {
            MbusFixedDataHeader fixedHeader = null;
            var allRecords = new List<MbusDataRecord>();
            bool moreDataExpected = true;
            int telegramCount = 0;
            int maxTelegramsToRequest = 100;
            int totalChecksum = 0;

            while (moreDataExpected && telegramCount < maxTelegramsToRequest)
            {
                telegramCount++;

                var result = await RequestDataInternalAsync(address);
                MbusTelegram response = result.Item1;
                byte[] rawResponse = result.Item2;

                if (response == null)
                {
                    moreDataExpected = false;
                    if (telegramCount == 1 && allRecords.Count == 0) return null;
                    break;
                }

                if (rawResponse != null && rawResponse.Length > 2)
                {
                    totalChecksum += (int)(SumArray(rawResponse)- rawResponse[rawResponse.Length - 2] - rawResponse[15]);
                }

                if (response.IsAcknowledgement) { moreDataExpected = false; break; }
                if (!response.IsLongFrame || response.UserData == null || response.UserData.Length == 0)
                {
                    moreDataExpected = false;
                    if (telegramCount == 1 && allRecords.Count == 0) return null;
                    break;
                }
                bool isSlaveResponse = (response.ControlField & 0x20) == 0;
                if (!isSlaveResponse || (response.ControlField & 0x0F) != (C_RSP_UD & 0x0F) || response.ControlInformationField != CI_RSP_VARIABLE)
                {
                    moreDataExpected = false;
                    break;
                }
                if (fixedHeader == null && response.FixedHeader != null && !string.IsNullOrEmpty(response.FixedHeader.IdentificationNumberStr) && response.FixedHeader.IdentificationNumber != 0)
                {
                    fixedHeader = response.FixedHeader;
                }
                if (response.DataRecords != null)
                {
                    allRecords.AddRange(response.DataRecords);
                }
                moreDataExpected = response.IsMoreDataFollow;
                if (moreDataExpected)
                {
                    await Task.Delay(_interTelegramDelay);
                }
            }
            if (fixedHeader == null && allRecords.Count == 0 && telegramCount > 0 && telegramCount < maxTelegramsToRequest) return null;
            if (fixedHeader == null && allRecords.Count > 0)
            {
                fixedHeader = new MbusFixedDataHeader { IdentificationNumberStr = "Unknown (Header Missing from primary)" };
            }
            return Tuple.Create(fixedHeader, allRecords, totalChecksum);
        }

        public async Task<Tuple<bool, int>> RequestAndCacheAllTelegramsAsync(byte address)
        {
            InvalidateCache(); 

            _fcb = 1;
            
            var fetchedData = await FetchAndParseAllDeviceDataAsync(address);

            if (fetchedData != null)
            {
                _cachedFixedHeader = fetchedData.Item1;
                if (fetchedData.Item2 != null)
                {
                    _cachedDataRecords.AddRange(fetchedData.Item2);
                }
                _lastCachedAddress = address;
                _isDataCached = true;
                return Tuple.Create(true, fetchedData.Item3);
            }
            _isDataCached = false; 
            return Tuple.Create(false, (int)0);
        }

        public bool RequestAndCacheAllTelegrams(byte address, out int totalChecksum)
        {
            try
            {
                var result = RequestAndCacheAllTelegramsAsync(address).GetAwaiter().GetResult();
                totalChecksum = result.Item2;
                return result.Item1;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"RequestAndCacheAllTelegrams (sync wrapper) Exception: {ex.Message}");
		totalChecksum = 0;                
		return false;
            }
        }
        
        public async Task<Tuple<List<MbusLogEvent>, int>> ReadAllLogsAsync(byte address, LogType logType)
        {
            byte[] logRequestPayload = new byte[] { 0xC0, 0xC0, 0x80, 0x80, 0x00, 0xFF, 0xF9, (byte)logType };

            bool commandSent = await SendUserDataAsync(address, 0x51, logRequestPayload);
            if (!commandSent)
            {
                throw new MbusException("Failed to send log read request to the meter. The meter did not acknowledge the command.");
            }

            var allLogs = new List<MbusLogEvent>();
            bool moreDataExpected = true;
            int telegramCount = 0;
            int maxTelegramsToRequest = 100;
            int totalChecksum = 0;

            while (moreDataExpected && telegramCount < maxTelegramsToRequest)
            {
                telegramCount++;

                var result = await RequestDataInternalAsync(address);
                MbusTelegram response = result.Item1;
                byte[] rawResponse = result.Item2;

                if (rawResponse != null && rawResponse.Length > 2)
                {
                    totalChecksum += (int)(SumArray(rawResponse)- rawResponse[rawResponse.Length - 2] - rawResponse[15]);
                }

                if (response == null || response.IsAcknowledgement || !response.IsLongFrame)
                {
                    moreDataExpected = false;
                    break;
                }

                if (response.DataRecords != null && response.DataRecords.Any())
                {
                    allLogs.AddRange(ParseLogRecords(response.DataRecords, logType));
                }

                moreDataExpected = response.IsMoreDataFollow;
                await Task.Delay(_interTelegramDelay);
            }

            return Tuple.Create(allLogs, totalChecksum);
        }

        public List<MbusLogEvent> ReadAllLogs(byte address, LogType logType, out int totalChecksum)
        {
            try
            {
                var result = ReadAllLogsAsync(address, logType).GetAwaiter().GetResult();
                totalChecksum = result.Item2;
                return result.Item1;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"ReadAllLogs (sync wrapper) Exception: {ex.Message}");
                totalChecksum = 0;
                return new List<MbusLogEvent>();
            }
        }

        private List<MbusLogEvent> ParseLogRecords(List<MbusDataRecord> records, LogType logType)
        {
            var parsedEvents = new List<MbusLogEvent>();
            if (records == null) return parsedEvents;

            for (int i = 0; i <= records.Count - 3; i += 3)
            {
                var idRecord = records[i];
                var timeRecord = records[i + 1];
                var durationRecord = records[i + 2];

                bool isIdRecord = idRecord.DIF == 0x02 && idRecord.VIF == 0xFF && idRecord.VIFEs.Count > 0 && idRecord.VIFEs[0] == 0xF9;
                bool isTimeRecord = timeRecord.DIF == 0x0E && timeRecord.VIF == 0xED;
                bool isDurationRecord = durationRecord.DIF == 0x04 && durationRecord.VIF == 0xA0;

                if (isIdRecord && isTimeRecord && isDurationRecord)
                {
                    var logEvent = new MbusLogEvent { Type = logType };

                    var idValueResult = InterpretDataRecord(idRecord);
                    if(idRecord.VIFEs.Count > 4) {
                         logEvent.RecordNumber = idRecord.VIFEs[4];
                    }

                    if (idValueResult.Found)
                    {
                        try 
                        { 
                            logEvent.EventId = Convert.ToInt32(idValueResult.Value);
                            if (logEvent.EventId >= 2013 && logEvent.EventId <= 2043)
                                logEvent.EventDescription = $"ALARM (ID: {logEvent.EventId})";
                            else if (logEvent.EventId >= 1000 && logEvent.EventId <= 1030)
                                logEvent.EventDescription = $"WARNING (ID: {logEvent.EventId})";
                            else if (logEvent.EventId >= 40 && logEvent.EventId <= 53)
                                logEvent.EventDescription = $"ERROR (ID: {logEvent.EventId})";
                            else
                                logEvent.EventDescription = "Unknown Event";
                        }
                        catch { logEvent.EventId = -1; logEvent.EventDescription = "Invalid ID"; }
                    } else {
                        break;
                    }

                    var timeValueResult = InterpretDataRecord(timeRecord);
                    if (timeValueResult.Found && timeValueResult.Value is long bcdTime && bcdTime > 0)
                    {
                        logEvent.Timestamp = bcdTime.ToString("X12");
                    }
                    else
                    {
                        logEvent.Timestamp = "Not available";
                    }

                    var durationValueResult = InterpretDataRecord(durationRecord);
                     if (durationValueResult.Found)
                    {
                         try { logEvent.DurationSeconds = Convert.ToInt32(durationValueResult.Value); }
                         catch { logEvent.DurationSeconds = -1; }
                    } else {
                        logEvent.DurationSeconds = 0;
                    }

                    if(logEvent.EventId != -1)
                    {
                        parsedEvents.Add(logEvent);
                    }
                }
            }
            return parsedEvents;
        }

        public async Task<bool> SendUserDataAsync(byte address, byte ciField, byte[] userDataPayload)
        {
            if (userDataPayload == null) userDataPayload = Array.Empty<byte>();
            if (userDataPayload.Length > 252) throw new ArgumentException("User data payload too large (>252 bytes) for M-Bus long frame.");
            InvalidateCache();
            byte lField = (byte)(3 + userDataPayload.Length);
            byte[] frame = new byte[6 + lField];
            frame[0] = MBUS_START_LONG_FRAME;
            frame[1] = lField;
            frame[2] = lField;
            frame[3] = MBUS_START_LONG_FRAME;
            frame[4] = C_SND_UD_FCB1;
            frame[5] = address;
            frame[6] = ciField;
            if (userDataPayload.Length > 0)
            {
                Array.Copy(userDataPayload, 0, frame, 7, userDataPayload.Length);
            }
            frame[frame.Length - 2] = CalculateMbusChecksum(frame, 4, lField);
            frame[frame.Length - 1] = MBUS_STOP;

            await SendFrameAsync(frame);
            try
            {
                byte[] ackResponse = await ReceiveFrameRawAsync(10000);
                if (ackResponse != null && ackResponse.Length == 1 && ackResponse[0] == MBUS_ACK)
                {
                    ToggleFcb();
                    return true;
                }
                return false;
            }
            catch (MbusException) { return false; }
            catch (Exception) { return false; }
        }


        public bool SendUserData(byte address, byte ciField, byte[] userDataPayload)
        {
            try
            {
                return SendUserDataAsync(address, ciField, userDataPayload).GetAwaiter().GetResult();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"SendUserData (sync wrapper) Exception: {ex.Message}");
                return false;
            }
        }

        public Task<MbusReadResult> ReadValueAsync(byte address, byte targetDif, byte targetVif, byte[] targetDifes = null, byte[] targetVifes = null)
        {
            if (!_isDataCached || _lastCachedAddress != address)
            {
                return Task.FromResult(new MbusReadResult { Found = false, ErrorMessage = "Data not cached for address " + address + ". Call RequestAndCacheAllTelegramsAsync first." });
            }

            var result = new MbusReadResult();
            MbusDataRecord foundRecord = null;
            
            var targetVifesPrefix = targetVifes ?? Array.Empty<byte>();

            foreach (var record in _cachedDataRecords)
            {
                bool difMatch = record.DIF == targetDif;
                bool vifMatch = record.VIF == targetVif;
                bool difeMatch = ArrayEquals(record.DIFEs?.ToArray(), targetDifes);
                
                bool vifeMatch = false;
                if (record.VIFEs != null && record.VIFEs.Count == targetVifesPrefix.Length + 1)
                {
                    if (record.VIFEs.Take(targetVifesPrefix.Length).SequenceEqual(targetVifesPrefix))
                    {
                        vifeMatch = true;
                    }
                }

                if (difMatch && vifMatch && difeMatch && vifeMatch)
                {
                    foundRecord = record;
                    break;
                }
            }

            if (foundRecord != null)
            {
                try
                {
                    result = InterpretDataRecord(foundRecord);
                    if (result.Found) 
                    {
                        result.LastVife = foundRecord.VIFEs.Last();
                    }
                }
                catch (Exception ex)
                {
                    result.Found = false;
                    result.ErrorMessage = $"An error occurred while interpreting data: {ex.Message}";
                }
            } else {
                result.Found = false; 
                result.ErrorMessage = "Matching record not found in cached data.";
            }
            return Task.FromResult(result); 
        }

        public bool ReadValue(byte address, byte targetDif, byte targetVif, out object value, out string unit, out byte? lastVife, byte[] targetDifes = null, byte[] targetVifes = null)
        {
            value = 0.0;
            unit = string.Empty;
            lastVife = 0x01;

            try
            {
                MbusReadResult asyncResult = ReadValueAsync(address, targetDif, targetVif, targetDifes, targetVifes).GetAwaiter().GetResult();

                if (!string.IsNullOrEmpty(asyncResult.ErrorMessage))
                {
                    unit = asyncResult.ErrorMessage; 
                    lastVife = 0x02;
                    return false;
                }

                if (asyncResult.Found && asyncResult.Value != null)
                {
                    unit = asyncResult.Unit;
                    lastVife = asyncResult.LastVife;
                    object originalValue = asyncResult.Value;

                    if (originalValue is string stringVal)
                    {
                        value = stringVal.TrimStart('\0');
                        return true;
                    }
                    else
                    {
                        value = Convert.ToDouble(originalValue);
                        return true;
                    }
                }
                return false;
            }
            catch (Exception ex)
            {
                value = null;
                unit = $"Error in ReadValue: {ex.Message}";
                lastVife = 0x05;
                return false;
            }
        }

        private List<string> DecodeStatusByte(byte statusByte)
        {
            var decodedStatuses = new List<string>();
            if ((statusByte & 0x01) != 0) decodedStatuses.Add("Meter busy");
            if ((statusByte & 0x02) != 0) decodedStatuses.Add("Internal error");
            if ((statusByte & 0x04) != 0) decodedStatuses.Add("Power low");
            if ((statusByte & 0x08) != 0) decodedStatuses.Add("Permanent error");
            if ((statusByte & 0x10) != 0) decodedStatuses.Add("Temporary error");
            if ((statusByte & 0x20) != 0) decodedStatuses.Add("Installation error");
            if (decodedStatuses.Count == 0 && statusByte != 0) decodedStatuses.Add("Unknown status bits set");
            return decodedStatuses;
        }

        public Task<ReadableFixedHeader> GetReadableFixedHeaderAsync(byte address)
        {
            if (!_isDataCached || _lastCachedAddress != address || _cachedFixedHeader == null)
            {
                return Task.FromResult<ReadableFixedHeader>(null);
            }

            MbusFixedDataHeader rawHeader = _cachedFixedHeader;
            var readableHeader = new ReadableFixedHeader
            {
                SerialNumber = rawHeader.IdentificationNumberStr,
                SerialNumberNumeric = rawHeader.IdentificationNumber,
                ManufacturerCode = $"{rawHeader.Manufacturer:X4}",
                Version = rawHeader.Version,
                MediumCode = rawHeader.Medium,
                AccessNumber = rawHeader.AccessNumber,
                StatusRawHex = $"0x{rawHeader.Status:X2}",
                StatusDecoded = DecodeStatusByte(rawHeader.Status),
                Signature = rawHeader.Signature,
	        FrameAddress = rawHeader.ActualFrameAddress
            };

            if (rawHeader.Manufacturer == 0x4204)
            {
                readableHeader.ManufacturerName = "ABB";
            }
            else
            {
                readableHeader.ManufacturerName = $"Unknown (Code: {rawHeader.Manufacturer:X4})";
            }

            switch (rawHeader.Medium)
            {
                case 0x00: readableHeader.MediumType = "Other"; break;
                case 0x01: readableHeader.MediumType = "Oil"; break;
                case 0x02: readableHeader.MediumType = "Electricity"; break;
                case 0x03: readableHeader.MediumType = "Gas"; break;
                case 0x04: readableHeader.MediumType = "Heat (Outlet)"; break;
                case 0x05: readableHeader.MediumType = "Steam"; break;
                case 0x06: readableHeader.MediumType = "Hot Water"; break;
                case 0x07: readableHeader.MediumType = "Water"; break;
                case 0x08: readableHeader.MediumType = "Heat Cost Allocator"; break;
                default: readableHeader.MediumType = $"Unknown (Code: 0x{rawHeader.Medium:X2})"; break;
            }
            return Task.FromResult(readableHeader);
        }

        public ReadableFixedHeader GetReadableFixedHeader(byte address)
        {
            try
            {
                return GetReadableFixedHeaderAsync(address).GetAwaiter().GetResult();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error in GetReadableFixedHeader (sync wrapper): {ex.Message}");
                return null;
            }
        }

        private byte CalculateMbusChecksum(byte[] buffer, int offset, int length)
        {
            byte checksum = 0;
            for (int i = 0; i < length; i++) checksum += buffer[offset + i];
            return checksum;
        }

        private async Task SendFrameAsync(byte[] frame)
        {
            if (_serialPort == null || !_serialPort.IsOpen) throw new InvalidOperationException("Serial port is not open.");
            await _serialPort.BaseStream.WriteAsync(frame, 0, frame.Length);
            await Task.Delay(_interTelegramDelay);
        }

        private Task<byte[]> ReceiveFrameRawAsync(int timeout)
        {
            if (_serialPort == null || !_serialPort.IsOpen) throw new InvalidOperationException("Serial port is not open.");
            var buffer = new byte[512];
            int bytesRead = 0;
            int originalReadTimeout = _serialPort.ReadTimeout;
            _serialPort.ReadTimeout = timeout;

            try
            {
                int firstByte = _serialPort.ReadByte();
                if (firstByte == -1) return Task.FromResult<byte[]>(null);

                buffer[bytesRead++] = (byte)firstByte;

                if (firstByte == MBUS_START_LONG_FRAME)
                {
                    for (int i = 0; i < 3; i++)
                    {
                        int nextByte = _serialPort.ReadByte();
                        if (nextByte == -1) throw new TimeoutException("Timeout during M-Bus long frame header reception.");
                        buffer[bytesRead++] = (byte)nextByte;
                    }
                    if (buffer[3] != MBUS_START_LONG_FRAME) throw new MbusException("Invalid M-Bus long frame: second start byte missing.");
                    int lengthL = buffer[1];
                    if (buffer[1] != buffer[2] && buffer[2] != 0x00) { }
                    if (lengthL == 0 && buffer[2] != 0) { lengthL = buffer[2]; }
                    if (lengthL < 3) throw new MbusException($"Invalid L-field value after checks: {lengthL}. Must be >= 3.");
                    int remainingBytes = lengthL + 2;
                    if (bytesRead + remainingBytes > buffer.Length) throw new MbusException($"Frame too large for buffer. L-field: {lengthL}");
                    for (int i = 0; i < remainingBytes; i++)
                    {
                        int nextByte = _serialPort.ReadByte();
                        if (nextByte == -1) throw new TimeoutException("Timeout during M-Bus long frame data reception.");
                        buffer[bytesRead++] = (byte)nextByte;
                    }
                }
                else if (firstByte == MBUS_START_SHORT_FRAME)
                {
                    for (int i = 0; i < 4; i++)
                    {
                         int nextByte = _serialPort.ReadByte();
                        if (nextByte == -1) throw new TimeoutException("Timeout during M-Bus short frame reception.");
                        buffer[bytesRead++] = (byte)nextByte;
                    }
                }
                else if (firstByte != MBUS_ACK)
                {
                    throw new MbusException($"Unexpected start byte: 0x{firstByte:X2}");
                }

                byte[] result = new byte[bytesRead];
                Array.Copy(buffer, 0, result, 0, bytesRead);
                return Task.FromResult(result);
            }
            catch (TimeoutException)
            {
                return Task.FromResult<byte[]>(null);
            }
            finally
            {
                 _serialPort.ReadTimeout = originalReadTimeout;
            }
        }

        private MbusTelegram ParseRawFrame(byte[] rawFrame)
        {
            if (rawFrame == null || rawFrame.Length == 0) return null;
            var telegram = new MbusTelegram { FrameType = rawFrame[0] };
            try
            {
                if (rawFrame[0] == MBUS_ACK && rawFrame.Length == 1) return telegram;
                if (rawFrame[0] == MBUS_START_SHORT_FRAME)
                {
                    if (rawFrame.Length != 5 || rawFrame[4] != MBUS_STOP) throw new MbusException("Invalid M-Bus short frame structure or length.");
                    telegram.ControlField = rawFrame[1];
                    telegram.AddressField = rawFrame[2];
                    if (rawFrame[3] != CalculateMbusChecksum(rawFrame, 1, 2)) throw new MbusException($"Short frame checksum error.");
                    return telegram;
                }
                if (rawFrame[0] == MBUS_START_LONG_FRAME)
                {
                    if (rawFrame.Length < 9) throw new MbusException("M-Bus long frame too short.");
                    if (rawFrame[3] != MBUS_START_LONG_FRAME) throw new MbusException("Invalid M-Bus long frame: second start byte missing.");
                    int lField = rawFrame[1];
                    if (rawFrame[1] != rawFrame[2] && rawFrame[2] != 0x00) { }
                    if (lField == 0 && rawFrame[2] != 0) { lField = rawFrame[2]; }
                    if (lField < 3) { throw new MbusException($"Invalid L-field value after checks: {lField}. L-field (content length) must be >= 3."); }

                    int expectedTotalFrameLength = 6 + lField;
                    if (rawFrame.Length != expectedTotalFrameLength) throw new MbusException($"M-Bus long frame length mismatch. L-field 0x{lField:X2} implies total frame length {expectedTotalFrameLength}, Got: {rawFrame.Length}");
                    if (rawFrame[rawFrame.Length - 1] != MBUS_STOP) throw new MbusException("M-Bus long frame missing stop byte.");

                    telegram.ControlField = rawFrame[4];
                    telegram.AddressField = rawFrame[5];
                    telegram.ControlInformationField = rawFrame[6];

                    if (rawFrame[expectedTotalFrameLength - 2] != CalculateMbusChecksum(rawFrame, 4, lField)) throw new MbusException($"Long frame checksum error. Expected 0x{CalculateMbusChecksum(rawFrame, 4, lField):X2}, Got 0x{rawFrame[expectedTotalFrameLength - 2]:X2}");

                    int userDataLength = lField - 3;
                    if (userDataLength > 0)
                    {
                        telegram.UserData = new byte[userDataLength];
                        Array.Copy(rawFrame, 7, telegram.UserData, 0, userDataLength);
                        bool isSlaveResponse = (telegram.ControlField & 0x20) == 0;
                        if (isSlaveResponse && (telegram.ControlField & 0x0F) == (C_RSP_UD & 0x0F) && telegram.ControlInformationField == CI_RSP_VARIABLE)
                        {
                            ParseRspUdUserData(telegram);
                        }
                    }
                    return telegram;
                }
                throw new MbusException($"Unknown frame type start byte: 0x{rawFrame[0]:X2}");
            }
            catch (Exception ex) 
            {
                Console.WriteLine($"Error parsing M-Bus frame: {ex.Message}");
                return null; 
            }
        }

        private void ParseRspUdUserData(MbusTelegram telegram)
        {
            telegram.FixedHeader = new MbusFixedDataHeader();
            telegram.DataRecords.Clear();
            if (telegram.UserData == null || telegram.UserData.Length == 0) return;

            byte[] ud = telegram.UserData;
            int offset = 0;

            if (ud.Length >= 12)
            {
                try
                {
                    telegram.FixedHeader.IdentificationNumberStr = ParseBcdToString(ud, offset, 4);
                    telegram.FixedHeader.IdentificationNumber = ParseBcdToUint(ud, offset, 4); offset += 4;
                    telegram.FixedHeader.Manufacturer = (ushort)((ud[offset++] << 8) | ud[offset++]);
                    telegram.FixedHeader.Version = ud[offset++];
                    telegram.FixedHeader.Medium = ud[offset++];
                    telegram.FixedHeader.AccessNumber = ud[offset++];
                    telegram.FixedHeader.Status = ud[offset++];
                    telegram.FixedHeader.Signature = (ushort)(ud[offset++] | (ud[offset++] << 8));
	            telegram.FixedHeader.ActualFrameAddress = telegram.AddressField;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error parsing M-Bus fixed data header: {ex.Message}");
                    telegram.FixedHeader = new MbusFixedDataHeader();
                    offset = 0; 
                }
            } else {
                 if (ud.Length > 0) telegram.IsMoreDataFollow = (ud[ud.Length - 1] == 0x1F);
                 return;
            }

            try
            {
                while (offset < ud.Length - 1) 
                {
                    if (ud[offset] == 0x0F || ud[offset] == 0x1F || ud[offset] == 0x2F)
                    {
                        break;
                    }
                    var record = new MbusDataRecord();
                    byte currentDIF = ud[offset++]; record.DIF = currentDIF;
                    while ((currentDIF & 0x80) != 0) 
                    {
                        if (offset >= ud.Length - 1) throw new MbusException("Unexpected end of frame while parsing DIFEs.");
                        currentDIF = ud[offset++]; record.DIFEs.Add(currentDIF);
                    }

                    if (offset >= ud.Length - 1 && !(ud[offset] == 0x0F || ud[offset] == 0x1F || ud[offset] == 0x2F) ) {
                         if (ud[offset] == 0x0F || ud[offset] == 0x1F || ud[offset] == 0x2F) break; 
                         throw new MbusException("Unexpected end of frame, expecting VIF or MDH.");
                    }
                     if (offset < ud.Length && (ud[offset] == 0x0F || ud[offset] == 0x1F || ud[offset] == 0x2F)) break;


                    byte currentVIF = ud[offset++]; record.VIF = currentVIF;
                    while ((currentVIF & 0x80) != 0) 
                    {
                        if (offset >= ud.Length - 1) throw new MbusException("Unexpected end of frame while parsing VIFEs.");
                        currentVIF = ud[offset++]; record.VIFEs.Add(currentVIF);
                    }
                     if (offset >= ud.Length && (record.DIF & 0x0F) != 0x00 && (record.DIF & 0x0F) != 0x08 && (record.DIF & 0x0F) != 0x0F) {
                        throw new MbusException("Unexpected end of frame, expecting data or MDH.");
                    }
                    if (offset < ud.Length && (ud[offset] == 0x0F || ud[offset] == 0x1F || ud[offset] == 0x2F) && (record.DIF & 0x0F) != 0x00 && (record.DIF & 0x0F) != 0x08 && (record.DIF & 0x0F) != 0x0F) {
                    } else if (offset >= ud.Length -1 && ((record.DIF & 0x0F) == 0x00 || (record.DIF & 0x0F) == 0x08 || (record.DIF & 0x0F) == 0x0F) ) {
                    } else if (offset >= ud.Length && !((record.DIF & 0x0F) == 0x00 || (record.DIF & 0x0F) == 0x08 || (record.DIF & 0x0F) == 0x0F) ){
                         throw new MbusException("Unexpected end of frame, expecting data for non-zero length DIF or MDH.");
                    }

                    int dataLen = GetDataLengthFromDIF(record.DIF);
                    if (dataLen > 0)
                    {
                        if (offset + dataLen > ud.Length - 1) throw new MbusException($"Data length ({dataLen}) for DIF 0x{record.DIF:X2} exceeds UserData boundary (ends before MDH). Offset: {offset}, Len: {dataLen}, UserDataLen: {ud.Length}");
                        record.RawDataValue = new byte[dataLen];
                        Array.Copy(ud, offset, record.RawDataValue, 0, dataLen);
                        offset += dataLen;
                    }
                    else if (dataLen == -1) 
                    {
                        if (offset >= ud.Length - 1) throw new MbusException("Expected LVAR byte for variable length data not found (before MDH).");
                        byte lvar = ud[offset++];
                        if (lvar > 0)
                        {
                            if (offset + lvar > ud.Length - 1) throw new MbusException($"Variable data length LVAR ({lvar}) for DIF 0x{record.DIF:X2} exceeds UserData boundary (ends before MDH). Offset: {offset}, LVAR: {lvar}, UserDataLen: {ud.Length}");
                            record.RawDataValue = new byte[lvar];
                            Array.Copy(ud, offset, record.RawDataValue, 0, lvar);
                            offset += lvar;
                        }
                        else record.RawDataValue = Array.Empty<byte>();
                    }
                    else 
                    {
                        record.RawDataValue = Array.Empty<byte>();
                    }
                    telegram.DataRecords.Add(record);
                }

                if (ud.Length > 0)
                {
                    telegram.IsMoreDataFollow = (ud[ud.Length - 1] == 0x1F);
                } else {
                    telegram.IsMoreDataFollow = false;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error parsing M-Bus data records: {ex.Message}");
                telegram.DataRecords.Clear();
                if (ud.Length > 0) telegram.IsMoreDataFollow = (ud[ud.Length - 1] == 0x1F); 
                else telegram.IsMoreDataFollow = false;
            }
        }

        private string ParseBcdToString(byte[] buffer, int offset, int length)
        {
            var sb = new StringBuilder(length * 2);
            for (int i = length - 1; i >= 0; i--) sb.AppendFormat("{0:X2}", buffer[offset + i]);
            return sb.ToString();
        }

        private uint ParseBcdToUint(byte[] buffer, int offset, int length)
        {
            uint result = 0; uint multiplier = 1;
            for (int i = 0; i < length; i++)
            {
                byte bcdByte = buffer[offset + i];
                uint val1 = (uint)(bcdByte & 0x0F); uint val2 = (uint)(bcdByte >> 4);
                if (val1 > 9 || val2 > 9) throw new FormatException("Invalid BCD byte encountered.");
                result += (val1 * multiplier); multiplier *= 10;
                result += (val2 * multiplier); multiplier *= 10;
            }
            return result;
        }

        private int GetDataLengthFromDIF(byte dif)
        {
            switch (dif & 0x0F)
            {
                case 0x00: return 0; case 0x01: return 1; case 0x02: return 2; case 0x03: return 3;
                case 0x04: return 4; case 0x05: return 4; case 0x06: return 6; case 0x07: return 8;
                case 0x08: return 0; case 0x09: return 1; case 0x0A: return 2; case 0x0B: return 3;
                case 0x0C: return 4; case 0x0D: return -1; case 0x0E: return 6; case 0x0F: return 0;
                default: return 0;
            }
        }

        private byte GetRequestControlField() => (_fcb == 0) ? C_REQ_UD2_FCB0 : C_REQ_UD2_FCB1;
        private byte GetSendCommandControlField() => (_fcb == 0) ? C_SND_UD_FCB0 : C_SND_UD_FCB1;
        private void ToggleFcb() => _fcb = (byte)(_fcb == 0 ? 1 : 0);

        public async Task<Tuple<MbusTelegram,byte[]>> RequestDataInternalAsync(byte address)
        {
            byte[] frame = new byte[5];
            frame[0] = MBUS_START_SHORT_FRAME;
            frame[1] = GetRequestControlField();
            frame[2] = address;
            frame[3] = CalculateMbusChecksum(frame, 1, 2);
            frame[4] = MBUS_STOP;
            await SendFrameAsync(frame);
            try
            {
                byte[] rawResponse = await ReceiveFrameRawAsync(_readTimeout);
                if (rawResponse == null) return null;
                MbusTelegram responseTelegram = ParseRawFrame(rawResponse);
                if (responseTelegram != null && responseTelegram.IsLongFrame && responseTelegram.FrameType != MBUS_ACK) 
                {
                    if ((responseTelegram.ControlField & 0x0F) == (C_RSP_UD & 0x0F))
                    {
                        ToggleFcb();
                    }
                }
                return Tuple.Create(responseTelegram, rawResponse);
            }
            catch (MbusException ex) 
            { 
                Console.WriteLine($"MbusException in RequestDataInternalAsync: {ex.Message}");
                return Tuple.Create<MbusTelegram, byte[]>(null, null);
            }
            catch (Exception ex) 
            { 
                Console.WriteLine($"Generic Exception in RequestDataInternalAsync: {ex.Message}");
                return Tuple.Create<MbusTelegram, byte[]>(null, null);
            }
        }

        public MbusReadResult InterpretDataRecord(MbusDataRecord record) 
        {
            var result = new MbusReadResult();
            object finalValue = null; string unit = ""; double multiplier = 1.0;
            int dataLength = record.RawDataValue.Length;

            if (record.VIF == 0x84) 
            {
                multiplier = 0.01; 
                unit = "kWh";
            }
            else if (record.VIF == 0xA9) { multiplier = 0.01; unit = "W"; }
            else if (record.VIF == 0xFD && record.VIFEs != null && record.VIFEs.Count >= 1)
            {
                if (record.VIFEs[0] == 0xC8) { multiplier = 0.1; unit = "V"; }
                else if (record.VIFEs[0] == 0xD9) { multiplier = 0.001; unit = "A"; }
                else if (record.VIFEs.FirstOrDefault() == 0x8E) { unit = ""; } 
            }
            else if (record.VIF == 0xFF && record.VIFEs != null && record.VIFEs.Count >= 1)
            {
                if (record.VIFEs[0] == 0xE0) { multiplier = 0.001; unit = ""; }
                else if (record.VIFEs[0] == 0xD9) { multiplier = 0.01; unit = "Hz"; }
                else if (record.VIFEs[0] == 0x98) { multiplier = 1; unit = ""; }
                else if (record.VIFEs[0] == 0xAA) { unit = ""; } 
            }

            byte dataTypeField = (byte)(record.DIF & 0x0F);
            bool isBcd = false; bool isAscii = false;

            switch (dataTypeField)
            {
                case 0x01: if (dataLength >= 1) finalValue = record.RawDataValue[0]; break;
                case 0x02: if (dataLength >= 2) finalValue = BitConverter.ToInt16(record.RawDataValue, 0); break;
                case 0x03: if (dataLength >= 3) { int val = record.RawDataValue[0] | (record.RawDataValue[1] << 8) | (record.RawDataValue[2] << 16); if ((record.RawDataValue[2] & 0x80) > 0) val |= (0xFF << 24); finalValue = val; } break;
                case 0x04: if (dataLength >= 4) finalValue = BitConverter.ToInt32(record.RawDataValue, 0); break;
                case 0x05: if (dataLength >= 4) finalValue = BitConverter.ToSingle(record.RawDataValue, 0); break;
                case 0x06: if (dataLength >= 6) { long val = 0; for (int i = 0; i < 6; ++i) val |= ((long)record.RawDataValue[i] << (i * 8)); if ((record.RawDataValue[5] & 0x80) > 0) val |= (-1L << 48); finalValue = val; } break;
                case 0x07: if (dataLength >= 8) finalValue = BitConverter.ToInt64(record.RawDataValue, 0); break;
                case 0x09: case 0x0A: case 0x0B: case 0x0C: case 0x0E:
                    isBcd = true;
                    if (dataLength > 0) try { finalValue = ParseBcdToLong(record.RawDataValue, 0, dataLength); } catch { finalValue = null; }
                    break;
                case 0x0D:
                    isAscii = true;
                    if (dataLength > 0)
                    {
                        try
                        {
                            byte[] asciiBytes = (byte[])record.RawDataValue.Clone();
                            Array.Reverse(asciiBytes);
                            finalValue = Encoding.ASCII.GetString(asciiBytes);
                        }
                        catch { finalValue = null; }
                    }
                    break;
                default:
                    if (dataLength >= 1) finalValue = record.RawDataValue[0];
                    break;
            }

            if (finalValue != null)
            {
                if (!isBcd && !isAscii && multiplier != 1.0)
                {
                    try { finalValue = Convert.ToDouble(finalValue, CultureInfo.InvariantCulture) * multiplier; }
                    catch { }
                }
                else if (isBcd && multiplier != 1.0)
                {
                    try { finalValue = (double)(long)finalValue * multiplier; } 
                    catch { }
                }
                result.Found = true; result.Value = finalValue; result.Unit = unit;
            }
            else { result.Found = false; }
            return result;
        }

        private static long ParseBcdToLong(byte[] buffer, int offset, int length)
        {
            long result = 0; ulong currentMultiplier = 1;
            for (int i = 0; i < length; i++)
            {
                byte bcdByte = buffer[offset + i];
                uint val1 = (uint)(bcdByte & 0x0F);
                uint val2 = (uint)(bcdByte >> 4);
                if (val1 > 9 || val2 > 9) throw new FormatException($"Invalid BCD byte 0x{bcdByte:X2} at index {offset + i}.");
                result += (long)(val1 * currentMultiplier); currentMultiplier *= 10;
                result += (long)(val2 * currentMultiplier); currentMultiplier *= 10;
            }
            return result;
        }
        
        private bool ArrayEquals(byte[] array1, byte[] array2)
        {
            var actualArray1 = array1 ?? Array.Empty<byte>();
            var actualArray2 = array2 ?? Array.Empty<byte>();
            return actualArray1.SequenceEqual(actualArray2);
        }

        private bool ListEquals(List<byte> list1, byte[] array2)
        {
            var actualList1 = list1 ?? new List<byte>();
            var actualArray2 = array2 ?? Array.Empty<byte>();
            return actualList1.SequenceEqual(actualArray2);
        }

        public void Dispose() { Dispose(true); GC.SuppressFinalize(this); }
        protected virtual void Dispose(bool disposing)
        {
            if (disposing)
            {
                if (_serialPort != null)
                {
                    if (_serialPort.IsOpen) _serialPort.Close();
                    _serialPort.Dispose(); _serialPort = null;
                }
            }
        }
        ~MbusMaster() { Dispose(false); }
    }

    public class MbusException : Exception
    {
        public MbusException(string message) : base(message) { }
        public MbusException(string message, Exception innerException) : base(message, innerException) { }
    }
}