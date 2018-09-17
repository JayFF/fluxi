# -*- coding: utf-8 -*-

from .devices import Device, DeviceQty, decorator_access_control
import visa
import warnings

class StanfordSR400IOError(Exception):
    """
    Stanford SR400 communication error.
    """
    def __init__(self, message = 'Communication with device failed'):
        super().__init__(message)
        
class StanfordSR400Qty(DeviceQty):
    def __init__(self, parent, *, prio = 0):
        super().__init__(parent, prio = prio)
    
    @decorator_access_control
    def get(self, attr):
        """
        Read current value of an attribute.
        
        Args:
            attr (str): String for reading command according to
                Stanford SR400 documentation.

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
                Stanford SR400 documentation.
            value (int): Value to be set
        
        Returns:
            None
        """
        self.parent._set(attr, value)
        
    @decorator_access_control    
    def start(self):
        self.parent._device.write('CS')
        
    @decorator_access_control    
    def stop(self):
        self.parent._device.write('CH')
        
    @decorator_access_control    
    def reset(self):
        self.parent._device.write('CR')
        
    @property
    def A(self):
        return int(self.get('QA'))
        
    @property
    def B(self):
        return int(self.get('QB'))
    
    @property
    def mode(self):
        return int(self.get('CM'))
    
    @mode.setter
    def mode(self, value):
        self.set('CM', str(value))
    
    @property
    def input_A(self):
        return int(self.get('CI0'))
    
    @input_A.setter
    def input_A(self, value):
        self.set('CI0,', str(value))
        
    @property
    def input_B(self):
        return int(self.get('CI1'))
    
    @input_B.setter
    def input_B(self, value):
        self.set('CI1,', str(value))
        
    @property
    def input_T(self):
        return int(self.get('CI2'))
    
    @input_T.setter
    def input_T(self, value):
        self.set('CI2,', str(value))
    
    @property
    def preset_A(self):
        return int(self.get('CP0'))
    
    @preset_A.setter
    def preset_A(self, value):
        self.set('CP0,', str(value))
        
    @property
    def preset_B(self):
        return int(self.get('CP1'))
    
    @preset_B.setter
    def preset_B(self, value):
        self.set('CP1,', str(value))
        
    @property
    def preset_T(self):
        return int(self.get('CP2'))
    
    @preset_T.setter
    def preset_T(self, value):
        self.set('CP2,', str(value))
        
    @property
    def periods(self):
        return int(self.get('NP'))
        
    @periods.setter
    def periods(self, value):
        self.set('NP,', str(value))
        
    @property
    def dwell_time(self):
        return int(self.get('DT'))
    
    @dwell_time.setter
    def dwell_time(self, value):
        self.set('DT,', str(value))
        
class StanfordSR400(Device):
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
            raise StanfordSR400IOError("Device " + device_string + " not found.")
        self._device = self._resource_manager.open_resource(device_string)
        
        # Set config default values
        self.timeout = 1
        self.read_termination = '\r\n'
        self.write_termination = '\r\n'        

        # Set device attributes
        attrs = {key:config[key] for key in ['timeout', 'read_termination', \
            'write_termination'] if key in config}
        for k, v in attrs.items():
            if hasattr(self._device, k):
                setattr(self._device, k, v)
                
        # Check if timeout is specified
        if self.timeout is None:
            warnings.warn("No timeout specified for Signal Recovery 7265. Reading may block forever on errors.", Warning)
        
        super().__init__(StanfordSR400Qty, StanfordSR400IOError)
                
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
        print('Opening connection to Stanford SR400... ', end = '', flush = True)
        
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
            response = self._device.query("SV")
        except visa.VisaIOError:
            raise StanfordSR400IOError
            
        if response != "0":
            raise StanfordSR400IOError

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
                Stanford SR400 documentation.

        Returns:
            int: Value returned by Signal Recovery 7265.
        """
        try:
            response = self._device.query(attr)
        except visa.VisaIOError:
            raise StanfordSR400IOError('Could not get attribute "{0}"'.format(attr))
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
                Stanford SR400 documentation.
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
            raise StanfordSR400IOError('Could not set attribute "{0}"'.format(attr))
        
        if result[0] != message_length or result[1].value != 0:
            print(str(result[0]), message_length, str(result[1].value))
            raise StanfordSR400IOError('Could not set attribute "{0}"'.format(attr))
        
        # Get new set voltage
        response = self._get(attr)
        
        # Check if both values are identical
        if response != value:
            raise StanfordSR400IOError('Could not set attribute "{0}"'.format(attr))

    def __enter__(self):
        if self.closed:
            self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
    
    def __del__(self):
        self.close()