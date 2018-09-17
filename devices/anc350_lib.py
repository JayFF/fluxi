# -*- coding: utf-8 -*-
"""
This module is a Python implementation of the C++ header provided
with the attocube ANC350 closed-loop positioner system. It is an adaption of
ANC350lib by Rob Heath and all credit goes to him. For more details see
https://github.com/Laukei/attocube-ANC350-Python-library
or http://robheath.me.uk.

Note:
    This module is intended to work with version 2 of the ANC driver and
    adaptions will be necessary when working with versions 3 or 4. To work
    properly, it needs access to the libraries ``anc350v2.dll``, ``libusb0.dll``
    and ``nhconnect.dll``. It may be necessary to add the location of these files
    to the ``PATH`` envirionment variable.
"""

import ctypes

#
# List of error types
#

NCB_Ok = 0 #                    No error
NCB_Error = -1 #                Unknown / other error
NCB_Timeout = 1 #               Timeout during data retrieval
NCB_NotConnected = 2 #          No contact with the positioner via USB
NCB_DriverError = 3 #           Error in the driver response
NCB_BootIgnored	= 4 #          Ignored boot, equipment was already running
NCB_FileNotFound = 5 #          Boot image not found
NCB_InvalidParam = 6 #          Transferred parameter is invalid
NCB_DeviceLocked = 7 #          A connection attempt failed because the device is already in use
NCB_NotSpecifiedParam = 8 #     Transferred parameter is out of specification


#checks the errors returned from the dll
def checkError(code,func,args):
	if code == NCB_Ok:
		return
	elif code == NCB_BootIgnored:	   
		print ("Warning: boot ignored in",func.__name__,"with parameters:",args)
		return
	elif code == NCB_Error:			 
		raise Exception("Error: unspecific in "+str(func.__name__)+" with parameters:"+str(args))
	elif code == NCB_Timeout:		   
		raise Exception("Error: comm. timeout in "+str(func.__name__)+" with parameters:"+str(args))
	elif code == NCB_NotConnected:	  
		raise Exception("Error: not connected") 
	elif code == NCB_DriverError:	   
		raise Exception("Error: driver error") 
	elif code == NCB_FileNotFound:	  
		raise Exception("Error: file not found") 
	elif code == NCB_InvalidParam:	  
		raise Exception("Error: invalid parameter")
	elif code == NCB_DeviceLocked:	  
		raise Exception("Error: device locked")
	elif code == NCB_NotSpecifiedParam: 
		raise Exception("Error: unspec. parameter in "+str(func.__name__)+" with parameters:"+str(args))
	else:					
		raise Exception("Error: unknown in "+str(func.__name__)+" with parameters:"+str(args))
	return code

#structure for PositionerInfo to handle positionerCheck return data
class PositionerInfo(ctypes.Structure):
    _fields_ = [("id",ctypes.c_int),
                ("locked",ctypes.c_bool)]

class ANC350Lib:
    def __init__(self, dll_path):
        self._dll_path = dll_path
        self.anc350v2 = ctypes.WinDLL(self._dll_path)
        
        #aliases for the strangely-named functions from the dll
        self.positionerAcInEnable = getattr(self.anc350v2,"_PositionerAcInEnable@12")
        self.positionerAmplitude = getattr(self.anc350v2,"_PositionerAmplitude@12")
        self.positionerAmplitudeControl = getattr(self.anc350v2,"_PositionerAmplitudeControl@12")
        self.positionerBandwidthLimitEnable = getattr(self.anc350v2,"_PositionerBandwidthLimitEnable@12")
        self.positionerCapMeasure = getattr(self.anc350v2,"_PositionerCapMeasure@12")
        self.positionerCheck = getattr(self.anc350v2,"_PositionerCheck@4")
        self.positionerClearStopDetection = getattr(self.anc350v2,"_PositionerClearStopDetection@8")
        self.positionerClose = getattr(self.anc350v2,"_PositionerClose@4")
        self.positionerConnect = getattr(self.anc350v2,"_PositionerConnect@8")
        self.positionerDcInEnable = getattr(self.anc350v2,"_PositionerDcInEnable@12")
        self.positionerDcLevel = getattr(self.anc350v2,"_PositionerDCLevel@12")
        self.positionerDutyCycleEnable = getattr(self.anc350v2,"_PositionerDutyCycleEnable@8")
        self.positionerDutyCycleOffTime = getattr(self.anc350v2,"_PositionerDutyCycleOffTime@8")
        self.positionerDutyCyclePeriod = getattr(self.anc350v2,"_PositionerDutyCyclePeriod@8")
        self.positionerExternalStepBkwInput = getattr(self.anc350v2,"_PositionerExternalStepBkwInput@12")
        self.positionerExternalStepFwdInput = getattr(self.anc350v2,"_PositionerExternalStepFwdInput@12")
        self.positionerExternalStepInputEdge = getattr(self.anc350v2,"_PositionerExternalStepInputEdge@12")
        self.positionerFrequency = getattr(self.anc350v2,"_PositionerFrequency@12")
        self.positionerGetAcInEnable = getattr(self.anc350v2,"_PositionerGetAcInEnable@12")
        self.positionerGetAmplitude = getattr(self.anc350v2,"_PositionerGetAmplitude@12")
        self.positionerGetBandwidthLimitEnable = getattr(self.anc350v2,"_PositionerGetBandwidthLimitEnable@12")
        self.positionerGetDcInEnable = getattr(self.anc350v2,"_PositionerGetDcInEnable@12")
        self.positionerGetDcLevel = getattr(self.anc350v2,"_PositionerGetDcLevel@12")
        self.positionerGetFrequency = getattr(self.anc350v2,"_PositionerGetFrequency@12")
        self.positionerGetIntEnable = getattr(self.anc350v2,"_PositionerGetIntEnable@12")
        self.positionerGetPosition = getattr(self.anc350v2,"_PositionerGetPosition@12")
        self.positionerGetReference = getattr(self.anc350v2,"_PositionerGetReference@16")
        self.positionerGetReferenceRotCount = getattr(self.anc350v2,"_PositionerGetReferenceRotCount@12")
        self.positionerGetRotCount = getattr(self.anc350v2,"_PositionerGetRotCount@12")
        self.positionerGetSpeed = getattr(self.anc350v2,"_PositionerGetSpeed@12")
        self.positionerGetStatus = getattr(self.anc350v2,"_PositionerGetStatus@12")
        self.positionerGetStepwidth = getattr(self.anc350v2,"_PositionerGetStepwidth@12")
        self.positionerIntEnable = getattr(self.anc350v2,"_PositionerIntEnable@12")
        self.positionerLoad = getattr(self.anc350v2,"_PositionerLoad@12")
        self.positionerMoveAbsolute = getattr(self.anc350v2,"_PositionerMoveAbsolute@16")
        self.positionerMoveAbsoluteSync = getattr(self.anc350v2,"_PositionerMoveAbsoluteSync@8")
        self.positionerMoveContinuous = getattr(self.anc350v2,"_PositionerMoveContinuous@12")
        self.positionerMoveReference = getattr(self.anc350v2,"_PositionerMoveReference@8")
        self.positionerMoveRelative = getattr(self.anc350v2,"_PositionerMoveRelative@16")
        self.positionerMoveSingleStep = getattr(self.anc350v2,"_PositionerMoveSingleStep@12")
        self.positionerQuadratureAxis = getattr(self.anc350v2,"_PositionerQuadratureAxis@12")
        self.positionerQuadratureInputPeriod = getattr(self.anc350v2,"_PositionerQuadratureInputPeriod@12")
        self.positionerQuadratureOutputPeriod = getattr(self.anc350v2,"_PositionerQuadratureOutputPeriod@12")
        self.positionerResetPosition = getattr(self.anc350v2,"_PositionerResetPosition@8")
        self.positionerSensorPowerGroupA = getattr(self.anc350v2,"_PositionerSensorPowerGroupA@8")
        self.positionerSensorPowerGroupB = getattr(self.anc350v2,"_PositionerSensorPowerGroupB@8")
        self.positionerSetHardwareId = getattr(self.anc350v2,"_PositionerSetHardwareId@8")
        self.positionerSetOutput = getattr(self.anc350v2,"_PositionerSetOutput@12")
        self.positionerSetStopDetectionSticky = getattr(self.anc350v2,"_PositionerSetStopDetectionSticky@12")
        self.positionerSetTargetGround = getattr(self.anc350v2,"_PositionerSetTargetGround@12")
        self.positionerSetTargetPos = getattr(self.anc350v2,"_PositionerSetTargetPos@16")
        self.positionerSingleCircleMode = getattr(self.anc350v2,"_PositionerSingleCircleMode@12")
        self.positionerStaticAmplitude = getattr(self.anc350v2,"_PositionerStaticAmplitude@8")
        self.positionerStepCount = getattr(self.anc350v2,"_PositionerStepCount@12")
        self.positionerStopApproach = getattr(self.anc350v2,"_PositionerStopApproach@8")
        self.positionerStopDetection = getattr(self.anc350v2,"_PositionerStopDetection@12")
        self.positionerStopMoving = getattr(self.anc350v2,"_PositionerStopMoving@8")
        self.positionerTrigger = getattr(self.anc350v2,"_PositionerTrigger@16")
        self.positionerTriggerAxis = getattr(self.anc350v2,"_PositionerTriggerAxis@12")
        self.positionerTriggerEpsilon = getattr(self.anc350v2,"_PositionerTriggerEpsilon@12")
        self.positionerTriggerModeIn = getattr(self.anc350v2,"_PositionerTriggerModeIn@8")
        self.positionerTriggerModeOut = getattr(self.anc350v2,"_PositionerTriggerModeOut@8")
        self.positionerTriggerPolarity = getattr(self.anc350v2,"_PositionerTriggerPolarity@12")
        self.positionerUpdateAbsolute = getattr(self.anc350v2,"_PositionerUpdateAbsolute@12")
        
        #set error checking & handling
        self.positionerAcInEnable.errcheck = checkError
        self.positionerAmplitude.errcheck = checkError
        self.positionerAmplitudeControl.errcheck = checkError
        self.positionerBandwidthLimitEnable.errcheck = checkError
        self.positionerCapMeasure.errcheck = checkError
        self.positionerClearStopDetection.errcheck = checkError
        self.positionerClose.errcheck = checkError
        self.positionerConnect.errcheck = checkError
        self.positionerDcInEnable.errcheck = checkError
        self.positionerDcLevel.errcheck = checkError
        self.positionerDutyCycleEnable.errcheck = checkError
        self.positionerDutyCycleOffTime.errcheck = checkError
        self.positionerDutyCyclePeriod.errcheck = checkError
        self.positionerExternalStepBkwInput.errcheck = checkError
        self.positionerExternalStepFwdInput.errcheck = checkError
        self.positionerExternalStepInputEdge.errcheck = checkError
        self.positionerFrequency.errcheck = checkError
        self.positionerGetAcInEnable.errcheck = checkError
        self.positionerGetAmplitude.errcheck = checkError
        self.positionerGetBandwidthLimitEnable.errcheck = checkError
        self.positionerGetDcInEnable.errcheck = checkError
        self.positionerGetDcLevel.errcheck = checkError
        self.positionerGetFrequency.errcheck = checkError
        self.positionerGetIntEnable.errcheck = checkError
        self.positionerGetPosition.errcheck = checkError
        self.positionerGetReference.errcheck = checkError
        self.positionerGetReferenceRotCount.errcheck = checkError
        self.positionerGetRotCount.errcheck = checkError
        self.positionerGetSpeed.errcheck = checkError
        self.positionerGetStatus.errcheck = checkError
        self.positionerGetStepwidth.errcheck = checkError
        self.positionerIntEnable.errcheck = checkError
        self.positionerLoad.errcheck = checkError
        self.positionerMoveAbsolute.errcheck = checkError
        self.positionerMoveAbsoluteSync.errcheck = checkError
        self.positionerMoveContinuous.errcheck = checkError
        self.positionerMoveReference.errcheck = checkError
        self.positionerMoveRelative.errcheck = checkError
        self.positionerMoveSingleStep.errcheck = checkError
        self.positionerQuadratureAxis.errcheck = checkError
        self.positionerQuadratureInputPeriod.errcheck = checkError
        self.positionerQuadratureOutputPeriod.errcheck = checkError
        self.positionerResetPosition.errcheck = checkError
        self.positionerSensorPowerGroupA.errcheck = checkError
        self.positionerSensorPowerGroupB.errcheck = checkError
        self.positionerSetHardwareId.errcheck = checkError
        self.positionerSetOutput.errcheck = checkError
        self.positionerSetStopDetectionSticky.errcheck = checkError
        self.positionerSetTargetGround.errcheck = checkError
        self.positionerSetTargetPos.errcheck = checkError
        self.positionerSingleCircleMode.errcheck = checkError
        self.positionerStaticAmplitude.errcheck = checkError
        self.positionerStepCount.errcheck = checkError
        self.positionerStopApproach.errcheck = checkError
        self.positionerStopDetection.errcheck = checkError
        self.positionerStopMoving.errcheck = checkError
        self.positionerTrigger.errcheck = checkError
        self.positionerTriggerAxis.errcheck = checkError
        self.positionerTriggerEpsilon.errcheck = checkError
        self.positionerTriggerModeIn.errcheck = checkError
        self.positionerTriggerModeOut.errcheck = checkError
        self.positionerTriggerPolarity.errcheck = checkError
        self.positionerUpdateAbsolute.errcheck = checkError
        
        #set argtypes
        self.positionerAcInEnable.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_bool]
        self.positionerAmplitude.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerAmplitudeControl.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerBandwidthLimitEnable.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_bool]
        self.positionerCapMeasure.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerCheck.argtypes = [ctypes.POINTER(PositionerInfo)]
        self.positionerClearStopDetection.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerClose.argtypes = [ctypes.c_int]
        self.positionerConnect.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerDcInEnable.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_bool]
        self.positionerDcLevel.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerDutyCycleEnable.argtypes = [ctypes.c_int, ctypes.c_bool]
        self.positionerDutyCycleOffTime.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerDutyCyclePeriod.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerExternalStepBkwInput.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerExternalStepFwdInput.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerExternalStepInputEdge.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerFrequency.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerGetAcInEnable.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_bool)]
        self.positionerGetAmplitude.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerGetBandwidthLimitEnable.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_bool)]
        self.positionerGetDcInEnable.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_bool)]
        self.positionerGetDcLevel.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerGetFrequency.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerGetIntEnable.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_bool)]
        self.positionerGetPosition.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerGetReference.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_bool)]
        self.positionerGetReferenceRotCount.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerGetRotCount.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerGetSpeed.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerGetStatus.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerGetStepwidth.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.positionerIntEnable.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_bool]
        self.positionerLoad.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_char)]
        self.positionerMoveAbsolute.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerMoveAbsoluteSync.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerMoveContinuous.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerMoveReference.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerMoveRelative.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerMoveSingleStep.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerQuadratureAxis.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerQuadratureInputPeriod.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerQuadratureOutputPeriod.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerResetPosition.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerSensorPowerGroupA.argtypes = [ctypes.c_int, ctypes.c_bool]
        self.positionerSensorPowerGroupB.argtypes = [ctypes.c_int, ctypes.c_bool]
        self.positionerSetHardwareId.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerSetOutput.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_bool]
        self.positionerSetStopDetectionSticky.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_bool]
        self.positionerSetTargetGround.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_bool]
        self.positionerSetTargetPos.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerSingleCircleMode.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_bool]
        self.positionerStaticAmplitude.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerStepCount.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerStopApproach.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerStopDetection.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_bool]
        self.positionerStopMoving.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerTrigger.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerTriggerAxis.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerTriggerEpsilon.argtypes = [ctypes.c_int,ctypes.c_int, ctypes.c_int]
        self.positionerTriggerModeIn.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerTriggerModeOut.argtypes = [ctypes.c_int, ctypes.c_int]
        self.positionerTriggerPolarity.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.positionerUpdateAbsolute.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]