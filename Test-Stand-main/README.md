# 🧪 TestStand Test Runner Setup

## ✅ Requirements

### 🧩 Software
- **NI TestStand**: version = 2020 (Ensure that is downloaded inside the **"C:\Program Files\National Instruments\"** folder)
- **NI LabVIEW**: version = 20.0  
- **NI VISA**, **NI MAX**: latest version
- **Python**: latest version (add it to PATH). The library needed to be installed: pip install requests, pip install beautifulsoup4, pip install pyvisa 
- **WinSAM**: latest version (Ensure that is downloaded inside the **"C:\"** folder)

> ℹ️ **Do not** have "spaces" in the path directory to the `Test-Stand` repository folder

---

## ⚙️ Test Stand Setup

### 1. Launch TestStand
Open **NI TestStand**.

### 2. Configure Search Directories
1. Unzip the `IPSES_Lib` in the `C:` folder
2. Navigate to `Configure > Search Directories`.
3. Add the `Test Runner` repository path:
- ✅ Enable **Search subdirectories**
- ✅ Enable the checkbox to the left of the path
4. Add the `IPSES_Lib` repository path:
- ✅ Enable **Search subdirectories**
- ✅ Enable the checkbox to the left of the path 

## 3. Configure Adapters
1. Navigate to `Configure > Adapters`.
2. Select LabVIEW, then configure:
- ✅ Enable the `LABVIEW Run-Time Engine` checkbox to the left.
- ✅ Select the `Auto detect using VI version` Version.
- ✅ Enable the `Execute 'Same as caller' VIs Using Multiple Threads` with `Default(8)` number of Threads.
- ✅ Leave the other setting unchecked.

### 4. Open Sequence File
Open the file `TestRunner.seq` from TestStand.

### 5. Open Main Sequence
Go to the **Sequences** panel and open the `MainSequence`.

### 6. Define Global Variables
1. Open the **Variables > StationGlobals** section.  
2. Ensure the following variables are defined; if not, add them:

| Name             | Type                |
|------------------|---------------------|
| `typeOfTesting`  | Number              |
| `TestTypology`   | String              |
| `TestName`       | String              |
| `jsonConfigPath` | String              |
| `RootTestPath`   | String              |
| `csvPath`        | String              |
| `Tests`          | Array of Containers |

> ℹ️ If `Tests` is missing, copy-paste it from the `Locals` section.

### 7. Configure the second Report
1. Go to `Configure > Result Processing ...`:
- ✅ Enable the **Show More Options** flag
3. Add a second report by clicking on the button `>` then `Generate Report`: 
- ✅ Enable the **Enable** flag for both the Reports
4. `Ok` to Save.

### 8. Enable Auto Login in TestStand
Follow this official guide from NI:  
[🔗 Auto Login Configuration Guide](https://knowledge.ni.com/KnowledgeArticleDetails?id=kA03q000000YINaCAO&l=it-IT)

### 9. Configure the Generator Options: ZERA
Navigate to the directory **".\TestRunner\sequences"** from the repository. 
For each of the folders containing `ZeraICT`:
1. Open the main sequence (the one ending with `ZeraICT`)
2. Edit the step `Setup Zera` with the actual generator configuration

---

## ⚙️ WinSam Setup

### 1. Launch WinSam
Open **WinSam**.

### 2. Configure WinSam
Ensure that the WinSam application is working correctly with the available Zera devices; if not, configure it accordingly.

### 3. Configure Test Stand Control Sequence
1. Unzip the folder `CEWE` inside the directory **"C:\Zera GmbH\WinSAM\Scripts\Special"**
2. Open `SKEditor` from WinSam
3. Click on `Import test sequence` and open the access file `WinSAM_ABB_TestStandRunner.mdb`
4. Click on the sequence `WinSAM_ABB_TestStandRunner`, then `OK`

### 4. Configure ICT
Open `Control` from WinSAM, then select the `WinSAM_ABB_TestStand_Runner` sequence:
- ✅ Enable the **Use ICT** flag, then save

### 5. Enable Auto Login in WinSAM
1. Open `Configuration` from WinSam logging with Administrator rights
2. Go to `General > User Manager ... > Connection to system users`:
- ✅ Enable the **Auto Login** flag
3. Add the user `EUROPE/(ABB user id)` as WinSam Admin
5. Log out and log back in to apply changes

---

## ⚙️ Input Setup

### 1. Configure the Script
Navigate to **".\TestRunner\utilities\script\SignalGenerator"** in the repository:
- Depending on the signal generator you're using, copy the corresponding `signalGenerator.py` script from its folder and substitute the one saved into the **".\SignalGenerator"** directory.

### 2. Configure the Signal Generator
Follow the instructions in the `readme.txt` file located in the folder of the selected signal generator to complete the setup.
 
---

## ⚙️ Polarion Setup

### 1. Configure the Page
Navigate to the `Test Run Planning` page from the repository you are interested in configuring:
1. Click the `Expand Tools` button, then `Edit`
2. Substitute the content of the script with the one saved inside the file `code_Polarion.txt`
3. Click the `Save & Close` button

---

## ▶️ Running a Test

### 1. Open the Application `TestStandRunner.exe`
> ℹ️ Available tests are inside the Excel file "Tests.xlsx" that will be opened automatically: check the tests marked as `Green`, those are the ones correctly implemented and validated

### 2. Configure the Hardware 
1. Make sure the generator and the meter are correctly configured and connected to the USB ports
2. If the test requires it, make sure the signal generator is correctly configured and connected to the USB port (check the Excel file "Tests.xlsx" test "Input" column for the Test for which the Input Signal Generator is required): check the readme inside **".\TestRunner\utilities\script\SignalGenerator\NAMEOFTHEGENERATOR"** for the physical setup

### 3. Insert the Meters configuration inside the Application
1. Check the USB COM Port of the meters from the Device Manager application
2. Check the other settings of the meters from their respective menus (NBus / ModbusTCP-IP, Baud Rate, Slave Address, etc.).
3. If the test requires it, set the input channel of each meter to the ones physically connected to the signal generator

### 4. (If the test requires it) Insert the VISA Resource Name of the Input Signal Generator
Check the name by doing these steps:
1. Open the `NI-MAX` application
2. Go to `MySystem\Device and Interfaces`
3. Open the COM corresponding to the Signal Generator (check the COM by using the Device Manager application)
4. Copy the Name in the `VISA Resource Name` section

### (Optional) 5. Save the configuration for the next usage of the application
- Click the button `Save Configuration` at the bottom of the application

### 6.1 Run a **Local Test**
1. Select `Test Type = Local`
2. Select the Test to be executed from the `Test Name` box: available Test information is inside the Excel file "Tests.xlsx" that will be opened automatically
3. Start the test by clicking the button `START`
> ℹ️ Starting a test will also save the configuration for the next usage of the application (as step 5)
4. Look at the `Test Result` status from the indicator at the bottom of the application
5. When the Test finishes its execution, look at the reports generated by the test by going to the **".\TestRunner\report"** folder from the repository: they will be available under the name `"Test Name".html` for the Partial report and `"Test Name"_Full.html` for the Full one

### 6.2 Run a **Remote Test** from Polarion
1. Plan One or More Test Runs in Polarion
In Polarion, plan one or more **Test Runs**, setting their type to **Automatic** and leaving their status as `Open`.
> ℹ️ **Important:** Make sure you are using the **new Test Run Planning page** (see configuration guide) when creating a new Test Run. Set the type to **Automatic**.
> If you are modifying an existing Test Run, ensure that its type is already set to **Automatic**.
> This is crucial because the application will:
> * Execute all Test Tasks in the specified `ProjectID\TestRunID` **only if** `TestRunID` is set and its type is **Automatic** in Polarion.
> * Otherwise, if `TestRunID` is **not specified**, it will execute all Test Tasks of **all** Test Runs in the project where the type is **Automatic**.

> ℹ️ **Available tests** are listed in the Excel file **"Tests.xlsx"**, which will open automatically.
> Only the tests marked in **green** are properly implemented and validated for execution.

> ℹ️ It is **always suggested to set up the Input Signal Generator** for remote execution, since multiple tests will be runned

> ℹ️ The names listed in the Excel file refer to the **Test Case names**, **not** the Test Task names.

> ℹ️ Any test added to the Test Run that is not available for execution will be **ignored** and will remain in **Waiting** status after the execution completes.
2. Select `Test Type = Remote`
3. Specify the Project ID where you define the Test Run(s)
> ℹ️ **Important:** The Project ID correspond to the Polarion repository name **without** spaces (for instance, `BJE QP Training` repository has Project ID = `BJEQPTraining`)
4. (Optional) Specify the Test Run ID
> ℹ️ The Test Run ID correspond to the Test Run Name inside Polarion 
5. Specify the PAT for accessing the Repository
> ℹ️ To retrieve a Personal Access Token for Polarion, navigate to `MyAccount\Personal Access Token`, create a valid token, then copy-paste it inside the application

> ℹ️ **Important:** To make the application able to access the Test Run, you **need** a Personal Access Token that is not expired and that is related to an account with the **authorisation to access and modify the repository and the test run(s) you are going to execute**
6. Start the test by clicking the button `START`
> ℹ️ Starting a test will also save the configuration for the next usage of the application (as step 5)
7. Look at the `Test Result` status from the indicator at the bottom of the application
8. When the Test finishes its execution, look at the reports and results generated automatically inside the Test Run(s) being executed 
---

## 🛠️ Notes
- Remote Execution can be configured to run in a loop, continuously checking for new Test Tasks added to the monitored Test Run. To enable this behaviour, set the LOOP_MODE parameter to True in the ".\TestRunner\utilities\script\polarion_poller.py" script, along with the appropriate configuration options.

---
## ⚠️ Known Issues

### Zera - WinSAM
- **WinSAM Freezes During Startup (Medium-High Probability)**
    - Possible **Causes**:
        - Previous TestStand execution didn't terminate WinSAM properly (less likely).
        - Zera hardware stops responding (**most probable cause**).
        - WinSAM/sequence isn't handling termination/startup correctly.

- **Dispenser Functionality Freezes During Execution (Medium-Low Probability)**
    - Possible **Causes**:
        - Zera hardware stops responding (**most probable cause**).
        - WinSAM/sequence isn't managing the dispenser correctly.

- **Zera Fails to Execute Commands from WinSAM Correctly During Operation (Rare Probability)**
    - Possible **Causes:**
        - Zera hardware mishandles the sent command, possibly due to momentary unresponsiveness.
---
