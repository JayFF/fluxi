# -*- coding: utf-8 -*-
"""
Interface for Signal Recovery 7265 DSP lock-in amplifier.
"""

from .devices import Device, DeviceQty, decorator_access_control
import visa
import warnings

class SignalRecovery7265IOError(Exception):
    """
    Signal Recovery 7265 communication error.
    """
    def __init__(self, message = 'Communication with device failed'):
        super().__init__(message)


class SignalRecovery7265Qty(DeviceQty):
    def __init__(self, parent, *, prio = 0):
        super().__init__(parent, prio = prio)
    
    @decorator_access_control
    def get(self, attr):
        """
        Read current value of an attribute.
        
        Args:
            attr (str): String for reading command according to
                Signal Recovery 7265 documentation.

        Returns:
            int: Value returned by Signal Recovery 7265.
        """
        return self.parent._get(attr)
    
    @decorator_access_control
    def set(self, attr, value):
        """
        Set attribute to given value.
        
        Args:
            attr (str): String for set command according to
                Signal Recovery 7265 documentation.
            value (int): Value to be set
        
        Returns:
            None
        """
        self.parent._set(attr, value)
    
    @property
    def adc1(self):
        """
        `Property` for voltage measured at auxiliary analog-to-digital (ADC) input 1.
        
        :getter: Voltage measured at ADC input 1 in volts.
        :type: float
        """
        attr = "ADC1"
        millivolts = self.get(attr)
        if not millivolts is None:
            return float(millivolts) / 1000
        else:
            return None
    
    @property
    def adc2(self):
        """
        `Property` for voltage measured at auxiliary analog-to-digital (ADC) input 2.
        
        :getter: Voltage measured at ADC input 2 in volts.
        :type: float
        """
        attr = "ADC2"
        millivolts = self.get(attr)
        if not millivolts is None:
            return float(millivolts) / 1000
        else:
            return None
    
    @property
    def dac1(self):
        """
        `Property` for voltage applied to auxiliary digital-to-analog (DAC) output 1.
        
        :getter: Get voltage applied to DAC output 1 in volts.
        :setter: Set voltage applied to DAC output 1 in volts.
        :type: float
        """
        attr = "DAC1"
        millivolts = self.get(attr)
        if not millivolts is None:
            return float(millivolts) / 1000
        else:
            return None
    
    @dac1.setter
    def dac1(self, volts):
        millivolts = int(1000 * volts)
        attr = "DAC1"
        self.set(attr, millivolts)
    
    @property
    def dac2(self):
        """
        `Property` for voltage applied to auxiliary digital-to-analog (DAC) output 2.
        
        :getter: Get voltage applied to DAC output 2 in volts.
        :setter: Set voltage applied to DAC output 2 in volts.
        :type: float
        """
        attr = "DAC2"
        millivolts = self.get(attr)
        if not millivolts is None:
            return float(millivolts) / 1000
        else:
            return None
    
    @dac2.setter
    def dac2(self, volts):
        millivolts = int(1000 * volts)
        attr = "DAC2"
        self.set(attr, millivolts)
      
    @property
    def dac3(self):
        """
        `Property` for voltage applied to auxiliary digital-to-analog (DAC) output 3.
        
        :getter: Get voltage applied to DAC output 3 in volts.
        :setter: Set voltage applied to DAC output 3 in volts.
        :type: float
        """
        attr = "DAC3"
        millivolts = self.get(attr)
        if not millivolts is None:
            return float(millivolts) / 1000
        else:
            return None
    
    @dac3.setter
    def dac3(self, volts):
        millivolts = int(1000 * volts)
        attr = "DAC3"
        self.set(attr, millivolts)
    
    @property
    def dac4(self):
        """
        `Property` for voltage applied to auxiliary digital-to-analog (DAC) output 4.
        
        :getter: Get voltage applied to DAC output 4 in volts.
        :setter: Set voltage applied to DAC output 4 in volts.
        :type: float
        """
        attr = "DAC4"
        millivolts = self.get(attr)
        if not millivolts is None:
            return float(millivolts) / 1000
        else:
            return None
    
    @dac4.setter
    def dac4(self, volts):
        millivolts = int(1000 * volts)
        attr = "DAC4"
        self.set(attr, millivolts)
        

class SignalRecovery7265(Device):
    """
    Interface for Signal Recovery 7265 DSP lock-in amplifier connected via GPIB.

    Args:
        config (dictionary): Dictionary of key-value pairs that determines
            the configuration of the serial port connection. Entries ``gpib``
            and ``address`` are mandatory. Options ``timeout``, 
            ``read_termination`` and ``write_termination`` are currently
            supported.
            
    Attributes:
        _gpib (int):
            GPIB interface number.
        _address (int):
            GPIB address of device.
        _resource_manager (ResourceManager):
            Visa resource manager containing general device and interface
            information.
        _device (GPIBInstrument):
            GPIB Instrument object used for communication with device.
    """
    
    def __init__(self, config):
        # Try to get GPIB interface number
        try:
            self._gpib = config['gpib']
        except KeyError as e:
            msg = "No GPIB interface number specified for SignalRecovery7265"
            raise Exception(msg).with_traceback(e.__traceback__)

        # Try to get GPIB address
        try:
            self._address = config['address']
        except KeyError as e:
            msg = "No GPIB address specified for SignalRecovery7265"
            raise Exception(msg).with_traceback(e.__traceback__)
        
        # Open device
        self._resource_manager = visa.ResourceManager()
        device_string = \
            'GPIB' + str(self._gpib) + '::' + str(self._address) + '::INSTR'
        if not device_string in self._resource_manager.list_resources():
            raise SignalRecovery7265IOError("Device " + device_string + " not found.")
        self._device = self._resource_manager.open_resource(device_string)
        
        # Set config default values
        self.timeout = 1
        self.read_termination = '\r\n'
        self.write_termination = '\r\n'        
        
        # Set device attributes
        attrs = {key:config[key] for key in ['timeout', 'read_termination', \
            'write_termination'] if key in config}
        for k, v in attrs.items():
            setattr(self, k, v)

        # Check if timeout is specified
        if self.timeout is None:
            warnings.warn("No timeout specified for Signal Recovery 7265. Reading may block forever on errors.", Warning)
        
        super().__init__(SignalRecovery7265Qty, SignalRecovery7265IOError)
                
    @property
    def timeout(self):
        return self._device.timeout / 1000
    
    @timeout.setter
    def timeout(self, value):
        self._device.timeout = 1000 * value
    
    @property
    def read_termination(self):
        return self._device.read_termination
        
    @read_termination.setter
    def read_termination(self, value):
        self._device.read_termination = value
        
    @property
    def write_termination(self):
        return self._device.write_termination
        
    @write_termination.setter
    def write_termination(self, value):
        self._device.write_termination = value
    
    def open(self):
        print('Opening connection to Signal Recovery 7265... ', end = '', flush = True)
        
        # Open connection to device
        self._device.open()

        # Set timeout to at least 1 second to test communication.
        timeout = self.timeout
        if self.timeout is None or self.timeout < 1:
            self.timeout = 1 

        # Sometimes characters are stuck in the read buffer. Get rid of them.
        try:
            self._device.read_raw(9999)
        except visa.VisaIOError:
            pass

        # Check communication
        try:
            response = self._device.query("ID")
        except visa.VisaIOError:
            raise SignalRecovery7265IOError
            
        if response != "7265":
            raise SignalRecovery7265IOError

        # Reset timeout
        self.timeout = timeout
        
        super().open()
        print('Success.', flush = True)
    
    def close(self):
        super().close()
        self._device.close()
    
    def _get(self, attr):
        """
        Read current value of an attribute.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            attr (str): String for reading command according to
                Signal Recovery 7265 documentation.

        Returns:
            int: Value returned by Signal Recovery 7265.
        """
        try:
            response = self._device.query(attr)
        except visa.VisaIOError:
            raise SignalRecovery7265IOError('Could not get attribute "{0}"'.format(attr))
        return int(response)
    
    def _set(self, attr, value):
        """
        Set attribute to given value.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            attr (str): String for reading command according to
                Signal Recovery 7265 documentation.
            value (int): Value to be set
        
        Returns:
            None
        """
        message = attr + " " + str(value)
        
        if self._device.write_termination == None:
            message_length = len(message)
        else:
            message_length = len(message) + len(self._device.write_termination)
        
        # Check for errors
        try:
            result = self._device.write(message)
        except visa.VisaIOError:
            raise SignalRecovery7265IOError('Could not set attribute "{0}"'.format(attr))
        
        if result[0] != message_length or result[1].value != 0:
            print(str(result[0]), message_length, str(result[1].value))
            raise SignalRecovery7265IOError('Could not set attribute "{0}"'.format(attr))
        
        # Get new set voltage
        response = self._get(attr)
        
        # Check if both values are identical
        if response != value:
            raise SignalRecovery7265IOError('Could not set attribute "{0}"'.format(attr))

    def __enter__(self):
        if self.closed:
            self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
    
    def __del__(self):
        self.close()