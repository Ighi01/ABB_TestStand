using System;
using System.Collections.Generic;
using System.IO;
using OfficeOpenXml;

namespace ExcelTestLoader
{
    public class TestData
    {
        public string Name { get; set; }
        public string Path { get; set; }
        public bool IsAutomatic { get; set; }
        public string Typology { get; set; }
        public int TypeOfTest { get; set; }
        public int TypeOfErogation { get; set; }
        public int NumOfMeasurements { get; set; }
    }

    public static class TestReader
    {
        private static List<TestData> tests = new List<TestData>();

        private static readonly Dictionary<string, int> TypeOfTestMapping = new Dictionary<string, int>
        {
            { "Measurement", 1 },
            { "Measurement (Wiring Only)", 2 },
            { "Reset", 3 },
            { "Tariff", 4 },
            { "Tariff + Measurement", 5 },
            { "Others", 7 }
        };

        private static readonly Dictionary<string, int> TypeOfErogationMapping = new Dictionary<string, int>
        {
            { "Voltage Driven", 1 },
            { "Energy Driven", 2 }
        };

        public static void LoadExcel(string filePath)
        {
            tests.Clear();
            ExcelPackage.LicenseContext = LicenseContext.NonCommercial;
            using (var package = new ExcelPackage(new FileInfo(filePath)))
            {
                var worksheet = package.Workbook.Worksheets[0];
                int rowCount = worksheet.Dimension.Rows;
                for (int row = 2; row <= rowCount; row++)
                {
                    if (string.IsNullOrWhiteSpace(worksheet.Cells[row, 1].Text))
                        break;

                    var test = new TestData
                    {
                        Name = worksheet.Cells[row, 1].Text,
                        IsAutomatic = worksheet.Cells[row, 2].Text.Equals("true", StringComparison.OrdinalIgnoreCase),
                        Typology = worksheet.Cells[row, 4].Text,
                        TypeOfTest = TypeOfTestMapping.TryGetValue(worksheet.Cells[row, 5].Text, out int tval) ? tval : 0,
                        TypeOfErogation = TypeOfErogationMapping.TryGetValue(worksheet.Cells[row, 6].Text, out int eval) ? eval : 0,
                        NumOfMeasurements = int.TryParse(worksheet.Cells[row, 7].Text, out int n) ? n : 0,
                        Path = worksheet.Cells[row, 8].Text
                    };

                    tests.Add(test);
                }
            }
        }

        public static int GetTestCount()
        {
            return tests.Count;
        }

        public static bool GetTestInfo(int index, out string name, out string path, out bool isAutomatic,
                                       out string typology, out int typeOfTest, out int typeOfErogation, out int numOfMeasurements)
        {
            var test = tests[index];
            name = test.Name;
            path = test.Path;
            isAutomatic = test.IsAutomatic;
            typology = test.Typology;
            typeOfTest = test.TypeOfTest;
            typeOfErogation = test.TypeOfErogation;
            numOfMeasurements = test.NumOfMeasurements;
            return true;
        }
    }
}
