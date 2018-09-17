# -*- coding: utf-8 -*-8
"""
Interface for Oxford Instruments ILM211 helium levelmeter.
"""

from .devices import Device, DeviceQty, decorator_access_control
import serial
import warnings
import re


class OxfordInstrumentsILM211IOError(Exception):
    """
    Oxford Instruments ILM211 communication error.
    """
    def __init__(self, message = 'Communication with device failed'):
        super().__init__(message)
        

class OxfordInstrumentsILM211Serial(serial.Serial):
    """
    Serial port interface with customizable line end character.
    """
    def readline(self, eol=b'\r'):
        """
        Read one line from the serial port which is terminated by the specified
        EOL character. See `<http://stackoverflow.com/a/16961872>`_ for details.
        
        Args:
            eol (str): EOL character.
        """
        leneol = len(eol)
        line = bytearray()
        while True:
            c = self.read(1)
            if c:
                line += c
                if line[-leneol:] == eol:
                    break
            else:
                raise OxfordInstrumentsILM211IOError
        return bytes(line)
    

class OxfordInstrumentsILM211Qty(DeviceQty):
    def __init__(self, parent, *, prio = 0):
        super().__init__(parent, prio = prio)
    
    @decorator_access_control
    def get(self, attr):
        """
        Read current value of an attribute.
        
        Args:
            attr (str): Letter shorthand for reading command according to
                Oxford Instruments ILM211 documentation.

        Returns:
            int: Value returned by Nanotec PD4.
        """
        return self.parent._get(attr)
    
    @decorator_access_control
    def set(self, attr, value):
        """
        Set attribute to given value.
        
        Args:
            attr (str): Letter shorthand for set command according to
                Oxford Instruments ILM211 documentation.
            value (int): Value to be set
        
        Returns:
            None
        """
        self.parent._set(attr, value)

    @property
    def level(self):
        """
        `Property` for current helium level.
        
        :getter: Get current helium level in percent.
        :type: float
        """
        return self.get('R1') / 10.0


class OxfordInstrumentsILM211(Device):
    """
    Interface for Oxford Instruments ILM211 helium levelmeter.

    Args:
        config (dictionary): Dictionary of key-value pairs that determines
            the configuration of the serial port connection. Entry ``port``
            is mandatory. Options ``baudrate``, ``bytesize``, ``parity``,
            ``stopbits``, ``timeout``, ``xonxoff``, ``rtscts`` and
            ``dsrdtr`` are currently supported.
            
    Attributes:
        _port (str): Serial port to connect to.
        _ser (Serial): Object of type `Serial` for communication to serial port.
        _address (int): Address of the motor. Defaults to 1.
    """
    
    def __init__(self, config):
        # Try to get portnumber
        try:
            self._port = config['port']
        except KeyError as e:
            msg = "No serial port specified for OxfordInstrumentsILM211"
            raise Exception(msg).with_traceback(e.__traceback__)
            
        # Create serial device object
        self._ser = OxfordInstrumentsILM211Serial(self._port)
        
        # Set config default values
        self.baudrate = 9600
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_TWO
        self.timeout = 1
        self.xonxoff = False
        self.rtscts = False
        self.dsrdtr = False
        
        # Get attributes from config
        attrs = {key:config[key] for key in ['baudrate', 'bytesize', \
            'parity', 'stopbits', 'timeout', 'xonxoff', 'rtscts', 'dsrdtr'] \
            if key in config}
        for k, v in attrs.items():
            setattr(self, k, v)

        # Check if timeout is specified
        if self.timeout is None:
            warnings.warn("No timeout specified for OxfordInstrumentsILM211. Reading may block forever on errors.", Warning)
        
        # Open serial connection, if necessary
        if not self._ser.isOpen():
            self._ser.open()

        # Open connection to device
        super().__init__(OxfordInstrumentsILM211Qty, OxfordInstrumentsILM211IOError)

    @property
    def baudrate(self):
        return self._baudrate
    
    @baudrate.setter
    def baudrate(self, value):
        self._baudrate = value
        self._ser.baudrate = value
    
    @property
    def bytesize(self):
        return self._bytesize
    
    @bytesize.setter
    def bytesize(self, value):
        self._bytesize = value
        self._ser.bytesize = value
        
    @property
    def parity(self):
        return self._parity
    
    @parity.setter
    def parity(self, value):
        self._parity = value
        self._ser.parity = value
        
    @property
    def stopbits(self):
        return self._stopbits
    
    @stopbits.setter
    def stopbits(self, value):
        self._stopbits = value
        self._ser.stopbits = value
        
    @property
    def timeout(self):
        return self._timeout
    
    @timeout.setter
    def timeout(self, value):
        self._timeout = value
        self._ser.timeout = value
        
    @property
    def xonxoff(self):
        return self._xonxoff
    
    @xonxoff.setter
    def xonxoff(self, value):
        self._xonxoff = value
        self._ser.xonxoff = value
        
    @property
    def rtscts(self):
        return self._rtscts
    
    @rtscts.setter
    def rtscts(self, value):
        self._rtscts = value
        self._ser.rtscts = value
        
    @property
    def dsrdtr(self):
        return self._dsrdtr
    
    @dsrdtr.setter
    def dsrdtr(self, value):
        self._dsrdtr = value
        self._ser.dsrdtr = value
    
    def open(self):
        print('Opening connection to Oxford Instruments ILM211... ', end = '', flush = True)
        
        # Set timeout to at least 1 second to test communication.
        if self.timeout is None or self.timeout < 1:
            self._ser.timeout = 1

        # Sometimes characters are stuck in the read buffer. Get rid of them.
        self._ser.read(9999)

        # Check communication with motor
        message = 'V\r'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.read(36).decode()
        match = re.match('ILM200 Version 1\.\d\d \(c\) OXFORD \d\d\d\d\r', \
                         response)
        if chars_sent != len(message) or match is None:
            raise OxfordInstrumentsILM211IOError

        # Reset timeout
        self._ser.timeout = self.timeout
        
        super().open()
        print('Success.', flush = True)

    def close(self):
        super().close()
        self._ser.close()
    
    def _get(self, attr):
        """
        Read current value of an attribute.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.
        
        Args:
            attr (str): Letter shorthand for reading command according to
                Oxfords Instruments ILM211 documentation.
        
        Returns:
            int: Value returned by Oxford Instruments ILM211.
        """
        # Get response:
        message = attr + '\r'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.readline().decode()
        
        # Use regex to extract desired value:
        match = re.match('[A-Za-z]+([\+-]?\d+)\r', response)
        if chars_sent != len(message) or match == None:
            raise OxfordInstrumentsILM211IOError('Could not get attribute "{0}"'.format(attr))
        return int(match.group(1))

    def _set(self, attr, value):
        """
        Set attribute to given value.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            attr (str): Letter shorthand for set command according to
                Oxford Instruments ILM211 documentation.
            value (int or bool): Value to be set
        
        Returns:
            None
        """
        # Send command and get response:
        message = attr + str(int(value)) + '\r'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.readline().decode()
        
        # Use regex to extract returned value:
        match = re.match(attr + '([\+-]?\d+)\r', response)
        if chars_sent != len(message) or match == None:
            raise OxfordInstrumentsILM211IOError('Could not set attribute "{0}"'.format(attr))
        
        # Check if value has actually been set:
        if int(match.group(1)) != value:
            raise OxfordInstrumentsILM211IOError('Could not set attribute "{0}"'.format(attr))

    def __enter__(self):
        if self.closed:
            self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
    
    def __del__(self):
        self.close()
