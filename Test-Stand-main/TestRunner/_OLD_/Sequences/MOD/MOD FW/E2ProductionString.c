/* Write multiple registers (hex Values) */

/* -- slave address -- function code -- starting register -- num registers -- byte cont -- register value:  
statusBreaker                                           
tripStatus                                              
peakCurrent                                             
motorTorque                                             
timeMaxTorque                                           
peakTorqueAngle                                         
closingTime                                             
openingTime                                             
totalNumberManeuver                                            
totalClosingManeuver                                      
maneuverAttemptOngoing                                  
assessmentOngoing                                       
assessmentResult                                        
out1Status                                              
out2Status                                              
in1Status                                               
in2Status                                               
lastCommand                                               
modStatus                                 
productTypeID                                              
productType1                                            
productType2                             
productType3                                         
productType4                                        
productType5                                         
productType6                                        
productType7                                         
productType8                            
serialNumberMOD1                                      
serialNumberMOD2                                      
serialNumberMOD3                                       
serialNumberMOD4                                      
serialNumberMOD5                                                           
fwVersionMod1                                      
fwVersionMod2                                                                             
assessmentTemp
assessmentVoltage
assessmentPhRd
assessmentRd															                               
commandBreaker                                         
OldcommandBreaker                          
leverPosition 								      	  
enableInput                                            
enableCommunication                       
reclosingAttempts                                     
waitingTime                    
neutralizationTime	// Default value is 12 sec for ARI, 45 sec for ARI30 and ARH 
outputsConfiguration
-- crc */  

MOD Configuration string Sign NC (MOD PCBA)  
//02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 00 00 4F 4D FF 44 FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF 
//FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 00 00 00 00 00 00 00 40 2E 41

MOD Configuration string (MOD PCBA)
02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 00 00 4F 4D FF 44 FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF 
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 00 00 00 00 00 00 00 00 2F B1


MOD_LV Configuration string (MOD PCBA)  
02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 01 00 4F 4D 5F 44 56 4C FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF 
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 00 00 00 00 00 00 00 00 17 5B

MOD_LV Configuration string Sign NC (MOD PCBA)  
//02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 01 00 4F 4D 5F 44 56 4C FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF 
//FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 00 00 00 00 00 00 00 40 16 AB

MOD_LV Configuration string Hager (MOD PCBA)  
02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 01 00 4F 4D 5F 44 56 4C FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF 
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 00 00 00 00 00 00 00 C0 17 0B


ARI Configuration string (MOD PCBA) 
02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 02 00 52 41 FF 49 FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF 
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 03 00 03 00 0C 00 00 00 D5 4B

ARI_LV Configuration string (MOD PCBA) 
02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 03 00 52 41 5F 49 56 4C FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF 
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 03 00 03 00 0C 00 00 00 ED A1


ARI_30 Configuration string (MOD PCBA) 
02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 04 00 52 41 5F 49 30 33 FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF 
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 03 00 1E 00 2D 00 00 00 EA F9


ARH_2P_30mA Configuration string (MOD PCBA) 
02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 05 00 52 41 5F 48 50 32 33 5F 6D 30 FF 41 FF FF FF FF FF FF FF FF FF FF 
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 00 00 00 00 2D 00 00 00 30 5B


ARH_2P_300mA Configuration string (MOD PCBA) 
02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 06 00 52 41 5F 48 50 32 33 5F 30 30 41 6D FF FF FF FF FF FF FF FF FF FF 
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 00 00 00 00 2D 00 00 00 12 9D


ARH_4P_30mA Configuration string (MOD PCBA) 
02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 07 00 52 41 5F 48 50 34 33 5F 6D 30 FF 41 FF FF FF FF FF FF FF FF FF FF 
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 00 00 00 00 2D 00 00 00 FB 97


ARH_4P_300mA Configuration string (MOD PCBA)      
02 10 91 00 00 30 60 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 A5 A5 00 00 00 00 00 00 00 00 A5 A5 01 00 08 00 52 41 5F 48 50 34 33 5F 30 30 41 6D FF FF FF FF FF FF FF FF FF FF 
FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF A5 A5 A5 A5 00 00 00 FF 00 FF 00 00 00 00 2D 00 00 00 CD 91


Motor Driver Parameters string (MOD PCBA)
//02 10 90 00 00 17 2E 78 05 78 05 88 13 E8 03 00 00 BC 02 E6 00 E6 00 A0 0F D0 07 40 06 40 06 B0 04 FF 00 54 03 FF 03 32 00 08 00 00 00 01 00 01 00 00 00 0A 00 09 B1

                    |     |     |     |     |     |     |     |     |     |     |     |     |     |     |     |     |     |     |     |     |     |     |     |     |      
02 10 90 00 00 18 30 78 05 78 05 78 05 01 00 26 02 E6 00 E6 00 A0 0F D0 07 B8 0B 40 06 B0 04 FF 00 54 03 FF 03 90 01 00 00 32 00 08 00 00 00 01 00 01 00 00 00 0A 00 24 26

Lock string
02 06 92 00 A5 A5 1E 6A
Unlock string
02 06 92 00 5A 5A 1F DA