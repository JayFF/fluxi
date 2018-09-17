# -*- coding: utf-8 -*-8
"""
Interface for Nanotec PD4 step motor.
"""

from .devices import Device, DeviceQty, decorator_access_control, make_enum
import serial
import warnings
import re
import enum


class NanotecPD4IOError(Exception):
    """
    Nanotec PD4 communication error.
    """
    def __init__(self, message = 'Communication with device failed'):
        super().__init__(message)
        
@enum.unique
class NanotecPD4Direction(enum.IntEnum):
    """
    Enum for specification of the direction.
    
    Attributes
        counterclockwise (int):
            Alias for counterclockwise movement. Corresponds to value 0.
        clockwise (int):
            Alias for clockwise movement. Corresponds to value 1.
    """
    counterclockwise = 0
    clockwise = 1
   

class NanotecPD4Serial(serial.Serial):
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
                raise NanotecPD4IOError
        return bytes(line)


class NanotecPD4Qty(DeviceQty):
    """
    Class to communicate with Nanotec PD4 ensuring mutually exclusive access 
    to the device.
    
    Args:
        parent (LasertackLR1):
            The parent LasertackLR1 instance that the axis is derived from.
        prio (int):
            Priority level used for device access control. Higher numbers
            indicate higher priority with zero being the lowest possible
            priority. Calls with positive priority level are guaranteed
            to be executed, while calls with zero priority level may be
            omitted and return `None`, if the device is busy. Keyword
            argument only.
    """
    _attrs = ('steps', 'direction', 'phase_current', 'rest_phase_current')
    
    def __init__(self, parent, *, prio = 0):
        super().__init__(parent, prio = prio)
    
    @decorator_access_control
    def get(self, attr):
        """
        Read current value of an attribute.
        
        Args:
            attr (str): Letter shorthand for reading command according to
                Nanotec PD4 documentation.

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
                Nanotec PD4 documentation.
            value (int or bool): Value to be set
        
        Returns:
            None
        """
        self.parent._set(attr, value)
    
    def get_attrs(self, attrs = None):
        """
        Get several attributes by passing a tuple of strings. Currently
        supported are the attributes ``steps``, ``direction``, ``phase_current``
        and ``rest_phase_current``.
        
        Args:
            attrs (list): List of strings of attributes to be returned.
        
        Returns:
            dictionary: Key-value pairs of attributes.
        """
        if attrs is None:
            attrs = type(self)._attrs
        result = {}
        for k in attrs:
            result[k] = getattr(self, k)
        return result
    
    def set_attrs(self, config):
        """
        Set several attributes by passing a dictionary with key-value pairs.
        Currently supported are the attributes ``steps``, ``direction``,
        ``phase_current`` and ``rest_phase_current``.
        
        Args:
            keyval (dictionary): Dictionary of key-value pairs to be set.
        
        Returns:
            None
        """
        attrs = {key:config[key] for key in type(self)._attrs if key in config}
        for k, v in attrs.items():
            setattr(self, k, v)

    @decorator_access_control
    def move(self):
        """
        Move motor according to the current parameter set.
        
        Returns:
            int: Number of steps moved including direction.
        """
        self.parent._move()
    
    @decorator_access_control
    def inc(self, value = 1):
        """
        Increment motor position
        
        Args:
            value (int): Number of steps by wihch position is incremented
        
        Returns:
            int: Number of steps moved including direction.
        """
        # Set number of steps according to current direction
        direction = int(self.parent._get('Zd'))
        self.parent._set('s', value * (2 * direction - 1))
        # Return number of steps made
        return self.parent._move()
            
    def dec(self, value = 1):
        """
        Decrement motor position
        
        Args:
            value (int): Number of steps by wihch position is decremented
        
        Returns:
            int: Number of steps moved including direction.
        """
        return self.inc(-value)

    @decorator_access_control
    def reset_position(self):
        """
        Reset motor position to zero.
        
        Returns:
            None
        """
        # Send command to move and get response
        message = '#' + str(self._address) + 'c\r'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.readline().decode()
        
        # Check if command was successful
        if chars_sent != len(message) or response != str(self._address) + 'c\r':
            raise NanotecPD4IOError
        
        # Check if position has been reset without access control
        if self.parent._get('C') != 0:
            raise NanotecPD4IOError('Could not reset motor position.')

    @property
    def position(self):
        """
        Property for current motor position.
        
        :getter: Get current motor position in steps.
        :setter: Move motor to specified position in steps.
        :type: int
        """
        return self.get('C')
    
    @position.setter
    @decorator_access_control
    def position(self, value):
        # Set number of steps according to current position and direction
        current_position = self.parent._get('C')
        steps = value - current_position
        direction = int(self.parent._get('Zd'))
        self.parent._set('s', steps * (2 * direction - 1))
        # Move motor
        self.parent._move()
    
    @property
    def steps(self):
        """
        Property for number of steps to be made.
        
        :getter: Get number of steps to be made.
        :setter: Set number of steps to be made.
        :type: int
        """
        return self.get('Zs')
    
    @steps.setter
    def steps(self, value):
        self.set('s', value)
    
    @property
    def direction(self):
        """
        Property for turning direction of motor.
        
        :getter: Get turning direction.
        :setter: Set turning direction.
        :type: :class:`NanotecPD4Direction`
        """
        return make_enum(NanotecPD4Direction, self.get('Zd'))
    
    @direction.setter
    def direction(self, value):
        self.set('d', make_enum(NanotecPD4Direction, value).value)
    
    @property
    def phase_current(self):
        """
        Property for phase current in percent. Needs to be between 0 and
        150. Avoid values above 100.
        
        :getter: Get current phase current.
        :setter: Set phase current.
        :type: int
        """
        return self.get('Zi')
    
    @phase_current.setter
    def phase_current(self, value):
        self.set('i', value)
    
    @property
    def rest_phase_current(self):
        """
        Property for rest phase current in percent. Needs to be between 0 and
        150. Avoid values above 100.
        
        :getter: Get current rest phase current.
        :setter: Set rest phase current.
        :type: int
        """
        return self.get('Zr')
    
    @rest_phase_current.setter
    def rest_phase_current(self, value):
        self.set('r', value)


class NanotecPD4(Device):
    """
    Interface for Nanotec PD4 step motor.

    Args:
        config (dictionary): Dictionary of key-value pairs that determines
            the configuration of the serial port connection. Entry ``port``
            is mandatory. Options ``address``, ``baudrate``, ``bytesize``,
            ``parity``, ``stopbits``, ``timeout``, ``xonxoff``, ``rtscts`` and
            ``dsrdtr`` are currently supported.
            
    Attributes:
        _port (str): Serial port to connect to.
        _ser (Serial): Object of type `Serial` for communication to serial port.
        _address (int): Address of the motor. Defaults to 1.
    """
    _attrs = ('address', 'baudrate', 'bytesize', 'parity', 'stopbits', 
              'timeout', 'xonxoff', 'rtscts', 'dsrdtr')
    
    def __init__(self, config):
        # Try to get portnumber
        try:
            self._port = config['port']
        except KeyError as e:
            msg = "No serial port specified for NanotecPD4"
            raise Exception(msg).with_traceback(e.__traceback__)
            
        # Create serial device object
        self._ser = NanotecPD4Serial(self._port)
        
        # Set config default values
        self.address = 1
        self.baudrate = 115200
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.timeout = 1
        self.xonxoff = False
        self.rtscts = False
        self.dsrdtr = False
        
        # Get attributes from config
        attrs = {key:config[key] for key in self._attrs \
            if key in config}
        for k, v in attrs.items():
            setattr(self, k, v)

        # Check if timeout is specified
        if self.timeout is None:
            warnings.warn("No timeout specified for NanotecPD4. Reading may block forever on errors.", Warning)
        
        # Open connection to device
        super().__init__(NanotecPD4IOError)
    
    @property
    def address(self):
        return self._address
    
    @address.setter
    def address(self, value):
        self._address = value

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
        print('Opening connection to Nanotec PD4... ', end = '', flush = True)
        
        # Open serial connection, if necessary
        if not self._ser.isOpen():
            self._ser.open()

        # Set timeout to at least 1 second to test communication.
        if self.timeout is None or self.timeout < 1:
            self._ser.timeout = 1

        # Sometimes characters are stuck in the read buffer. Get rid of them.
        self._ser.read(9999)

        # Check communication with motor
        message = '#' + str(self._address) + '|1\r'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.read(len(message) - 1).decode()
        if chars_sent != len(message) or response != str(self._address) + '|1\r':
            raise NanotecPD4IOError

        # Reset timeout
        self._ser.timeout = self.timeout
        
        super().open()
        print('Success.', flush = True)
    
    def close(self):
        super().close()
        self._ser.close()
    
    def qty(self, *, prio = 0):
        return NanotecPD4Qty(self, prio = prio)
    
    def _get(self, attr):
        """
        Read current value of an attribute.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            attr (str): Letter shorthand for reading command according to
                Nanotec PD4 documentation.
        
        Returns:
            int: Value returned by Nanotec PD4.
        """
        # Get response:
        message = '#' + str(self._address) + attr + '\r'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.readline().decode()
        
        # Use regex to extract desired value:
        match = re.match(str(self._address) + attr + '([\+-]?\d+)\r', response)
        if chars_sent != len(message) or match == None:
            raise NanotecPD4IOError('Could not get attribute "{0}"'.format(attr))
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
                Nanotec PD4 documentation.
            value (int or bool): Value to be set
        
        Returns:
            None
        """
        # Send command and get response:
        message = '#' + str(self._address) + attr + str(int(value)) + '\r'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.readline().decode()
        
        # Use regex to extract returned value:
        match = re.match(str(self._address) + attr + '([\+-]?\d+)\r', response)
        if chars_sent != len(message) or match == None:
            raise NanotecPD4IOError('Could not set attribute "{0}"'.format(attr))
        
        # Check if value has actually been set:
        if int(match.group(1)) != value or self._get('Z' + attr) != value:
            raise NanotecPD4IOError('Could not set attribute "{0}"'.format(attr))
    
    def _move(self):
        """
        Move motor according to the current parameter set.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Returns:
            int: Number of steps moved including direction.
        """
        # Get inital position without access control
        initial = self._get('C')

        # Calculate final position. Get number of steps and direction without
        # access control.
        increment = self._get('Zs') * (2 * int(self._get('Zd')) - 1)
        final = initial + increment
        
        # Send command to move and get response
        message = '#' + str(self._address) + 'A\r'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.readline().decode()
        
        # Check if command was successful
        if chars_sent != len(message) or response != str(self._address) + 'A\r':
            raise NanotecPD4IOError
        
        # Wait until target position has been reached. Query current position
        # without access control.
        while self._get('C') != final:
            self.wait_func(0.1)
        
        # Return number of steps made
        return increment
    
    def __enter__(self):
        if self.closed:
            self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
    
    def __del__(self):
        self.close()
