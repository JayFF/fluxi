# -*- coding: utf-8 -*-8
"""
Interface for Attocube ANC 150 piezo controller.
"""

from .devices import Device, DeviceQty, decorator_access_control, make_enum
import serial
import warnings
import re
import enum


class ANC150IOError(Exception):
    """
    ANC150 communication error.
    """
    def __init__(self, message = 'Communication with device failed'):
        super().__init__(message)

@enum.unique
class ANC150Direction(enum.IntEnum):
    """
    Enum for specification of the direction.
    
    Attributes
        forward (int):
            Alias for forward movement. Corresponds to value 0.
        backward (int):
            Alias for backward movement. Corresponds to value 1.
    """
    forward = 0
    backward = 1
   
@enum.unique
class ANC150AxisMode(enum.IntEnum):
    """
    Enum for specification of the amplitude control mode.
    
    Attributes
        ext (int):
            Alias for external mode. Corresponds to value 0.
        stp (int):
            Alias for step mode. Corresponds to value 1.
        gnd (int):
            Alias grounded mode. Corresponds to value 2.
        cap (int):
            Alias capacitance mode. Corresponds to value 3.
    """
    ext = 0
    stp = 1
    gnd = 2
    cap = 3

class ANC150Serial(serial.Serial):
    """
    Serial port interface with customizable line end character.
    """
    def readline(self, eol=b'\r\n> '):
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
                raise ANC150IOError
        return bytes(line)


class ANC150Axis(DeviceQty):
    """
    Class to communicate with a single controller axis.
    
    Args:
        parent (ANC150):
            The parent ANC150 instance that the axis is derived from.
        axis_number (int):
            Numerical value representing the axis
        prio (int):
            Priority level used for device access control. Higher numbers
            indicate higher priority with zero being the lowest possible
            priority. Calls with positive priority level are guaranteed
            to be executed, while calls with zero priority level may be
            omitted and return `None`, if the device is busy. Keyword
            argument only.
    """
    def __init__(self, parent, axis_number, *, prio = 0):
        super().__init__(parent, prio = prio)
        self._axis_number = axis_number
    
    @property
    def axis_number(self):
        """
        Property to retrieve the numerical value representing the current axis.

        :type: int
        """
        return self._axis_number
    
    @decorator_access_control
    def get(self, attr, axis):
        """
        Read current value of an attribute.
        
        Args:
            attr (str): Letter shorthand for get command according to
                Attocube ANC150 documentation without leading ``"get"``.
            axis (int): Integer determmining correspondng controller axis.

        Returns:
            str: String representation of value returned by ANC150.
        """
        return self.parent._get(attr, axis)
    
    @decorator_access_control
    def set(self, attr, axis, value):
        """
        Set attribute to given value.
        
        Args:
            attr (str): Letter shorthand for set command according to
                Attocube ANC150 documentation without leading ``"set"``.
            axis (int): Integer determmining correspondng controller axis.
            value (int or bool): Value to be set
        
        Returns:
            None
        """
        self.parent._set(attr, axis, value)

    @property
    @decorator_access_control
    def capacitance(self):
        """
        Property to determine the capacitance of the piezo addressed by this
        axis in nF.
        
        :type: int
        """
        mode = self.parent._get('m', self.axis_number)
        self.parent._set('m', self.axis_number, 'cap')
        for i in range(10):
            res = self.parent._get('c', self.axis_number)
            if res != '0 nF':
                break
            self.parent.wait_func(0.1)
        self.parent._set('m', self.axis_number, mode)
        if res[-3:] != ' nF':
            raise ANC150IOError
        return int(res[:-3])
    
    @property
    def frequency(self):
        """
        Property for the frequency in Hz to drive the piezo addressed by this
        axis.
        
        :getter: Gets the current driving frequency
        :setter: Sets the driving frequency
        :type: int
        """
        res = self.get('f', self.axis_number)
        if res[-3:] != ' Hz':
            raise ANC150IOError
        return int(res[:-3])
    
    @frequency.setter
    @decorator_access_control
    def frequency(self, value):
        mode = self.parent._get('m', self.axis_number)
        if not mode in ('gnd','stp'):
            self.parent._set('m', self.axis_number, 'gnd')
        self.parent._set('f', self.axis_number, value)
        self.parent._set('m', self.axis_number, mode)
    
    @property
    def mode(self):
        """
        Property for the operation mode of this axis.
        
        :getter: Gets the current operation mode
        :setter: Sets the operation mode
        :type: ANC150AxisMode
        """
        return make_enum(ANC150AxisMode, self.get('m', self.axis_number))

    @mode.setter
    def mode(self, value):
        try:
            m = make_enum(ANC150AxisMode, value).name
        except ValueError:
            m = value
        self.set('m', self.axis_number, m)
    
    @property
    @decorator_access_control
    def position(self):
        """
        Property to retrieve the position of this axis according to the
        registered res_func
        """
        return self.parent._res_func(self.axis_number, prio = self.prio)
    
    @property
    def voltage(self):
        """
        Property for the amplitude in V to drive the piezo addressed by this
        axis.
        
        :getter: Gets the current driving amplitude
        :setter: Sets the driving amplitude
        :type: int
        """
        res = self.get('v', self.axis_number)
        if res[-2:] != ' V':
            raise ANC150IOError
        return int(res[:-2])
    
    @voltage.setter
    @decorator_access_control
    def voltage(self, value):
        mode = self.parent._get('m', self.axis_number)
        if not mode in ('gnd','stp'):
            self.parent._set('m', self.axis_number, 'gnd')
        self.parent._set('v', self.axis_number, value)
        self.parent._set('m', self.axis_number, mode)
    
    @decorator_access_control
    def step(self, steps = 1, direction = ANC150Direction.forward):
        """
        Move stepper with the currently set amplitude and frequency.
        
        Args:
            steps (int or None): 
                Number of steps to be made. If set to `None`, stepper will
                operate in continuous mode, until stopped manually.
            direction (ANC150Direction):
                Direction in which the stepper is supposed to move.
        """
        try:
            forward = make_enum(ANC150Direction, direction) is ANC150Direction.forward
        except:
            forward = direction
        mode = self.parent._get('m', self.axis_number)
        self.parent._set('m', self.axis_number, 'stp')
        self.parent._step(self.axis_number, steps, forward)
        if not steps is None:
            self.parent._set('m', self.axis_number, mode)
    
    @decorator_access_control
    def stop_moving(self):
        """
        Stop movement of the axis, when the axis is moving in continuous mode.
        """
        self.parent._stop_moving(self.axis_number)
        self.parent._set('m', self.axis_number, 'gnd')

        
class ANC150(Device):
    """
    Interface for ANC150 piezo controller. In itself, this class does not know
    anything about the axes that are connected to the controller. On
    instanciation, a mapping between axis numbers and strings naming the
    corresponding axes is read from the config passed to the constructor. For
    each axis name, a method with this name and signature ``axis_func(prio = 0)``
    is auto generated to provide easy access for all axes.

    Args:
        config (dictionary): Dictionary of key-value pairs that determines
            the configuration of the serial port connection. Entries ``port``
            and ``axes`` are mandatory. The latter must be a dict with a mapping
            between strings describing the axis and the corresponding axis
            number. Options ``address``, ``baudrate``, ``bytesize``,
            ``parity``, ``stopbits``, ``timeout``, ``xonxoff``, ``rtscts`` and
            ``dsrdtr`` are currently supported.
            
    Attributes:
        _port (str): Serial port to connect to.
        _ser (Serial): Object of type `Serial` for communication to serial port.
    """
    _attrs = ('baudrate', 'bytesize', 'parity', 'stopbits', 'timeout',
              'xonxoff', 'rtscts', 'dsrdtr')
    
    def __init__(self, config):
        # Try to get portnumber
        try:
            self._port = config['port']
        except KeyError as e:
            msg = "No serial port specified for ANC150"
            raise Exception(msg).with_traceback(e.__traceback__)
            
        # Create serial device object
        self._ser = ANC150Serial(self._port)
        
        # Set config default values
        self.address = 1
        self.baudrate = 38400
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.timeout = 1
        self.xonxoff = False
        self.rtscts = False
        self.dsrdtr = False
        self._axis_moving = dict()
        
        # Register no-op res function
        def res_func(axis, *, prio = 0, coarse = False):
            return None
        
        self.register_res_function(res_func)
        
        # Get attributes from config
        attrs = {key:config[key] for key in self._attrs \
            if key in config}
        for k, v in attrs.items():
            setattr(self, k, v)

        # Set up axes according to specification in config.
        try:
            axes = config['axes']
            if not type(axes) is dict:
                raise ANC150IOError("Expected 'dict' as axes specification, found '{0}'.".format(str(type(axes))))
            
            # Define generator for axis functions
            def make_axis_func(num):
                def axis_func(*, prio = 0):
                    return ANC150Axis(self, num, prio = prio)
                return axis_func
            
            # Loop over all axis names and numbers
            for label, num in axes.items():
                if not type(label) is str:
                    raise ANC150IOError("'{0}' is not a legal axis label".format(label))
                try:
                    num = int(num)
                except TypeError as e:
                    msg = "'{0}' is not a legal axis number".format(num)
                    raise ANC150IOError(msg).with_traceback(e.__traceback__)
                
                # Add method with axis name as function name
                setattr(self, label, make_axis_func(num))
                self._axis_moving[num] = False
        except KeyError as e:
            msg = "No axes specified for ANC150"
            raise Exception(msg).with_traceback(e.__traceback__)

        # Check if timeout is specified
        if self.timeout is None:
            warnings.warn("No timeout specified for ANC150. Reading may block forever on errors.", Warning)
        
        # Open connection to device
        super().__init__(ANC150IOError)
    
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
        print('Opening connection to ANC150... ', end = '', flush = True)
        
        # Open serial connection, if necessary
        if not self._ser.isOpen():
            self._ser.open()

        # Set timeout to at least 1 second to test communication.
        if self.timeout is None or self.timeout < 1:
            self._ser.timeout = 1

        # Sometimes characters are stuck in the read buffer. Get rid of them.
        self._ser.read(9999)

        # Check communication with motor
        message = 'ver\r\n'
        chars_sent = self._ser.write(message.encode())
        if chars_sent != len(message):
            raise ANC150IOError
        response = self._ser.readline().decode().split('\r\n')
        if len(response) != 5 or response[0] != 'ver':
            raise ANC150IOError
        if re.match('^attocube controller version.*build date', response[1]) is None:
            raise ANC150IOError
        if re.match('^serial number', response[2]) is None:
            raise ANC150IOError
        if response[3] != 'OK' or response[4] != '> ':
            raise ANC150IOError

        # Reset timeout
        self._ser.timeout = self.timeout
        
        super().open()
        print('Success.', flush = True)
    
    def close(self):
        super().close()
        self._ser.close()
    
    def _get(self, attr, axis):
        """
        Read current value of an attribute.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            attr (str): Letter shorthand for reading command according to
                ANC 150 documentation.
        
        Returns:
            int: Value returned by ANC 150.
        """
        message = 'get' + str(attr) + ' ' + str(axis) + '\r\n'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.readline().decode().split('\r\n')
        if chars_sent != len(message) or response[-1] != '> ':
            raise ANC150IOError
        if response[-2] == 'ERROR':
            raise ANC150IOError(response[-3])
        if len(response) != 4 or response[-2] != 'OK' or response[0] != message.strip():
            raise ANC150IOError
        return response[1].split('=')[1].strip()
    
    def _set(self, attr, axis, value):
        """
        Set attribute to given value.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            attr (str): Letter shorthand for set command according to
                ANC 150 documentation.
            value (int or bool): Value to be set
        
        Returns:
            None
        """
        message = 'set' + str(attr) + ' ' + str(axis) + ' ' + str(value) + '\r\n'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.readline().decode().split('\r\n')
        if chars_sent != len(message) or response[-1] != '> ':
            raise ANC150IOError
        if response[-2] == 'ERROR':
            raise ANC150IOError(response[-3])
        if len(response) != 3 or response[-2] != 'OK' or response[0] != message.strip():
            raise ANC150IOError
        if self._get(attr, axis).split(' ')[0] != str(value):
            raise ANC150IOError
    
    def _step(self, axis, steps = 1, forward = True):
        """
        Move stepper with the currently set amplitude and frequency.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            axis (int): Numerical axis ID.
            steps (int or None): 
                Number of steps to be made. If set to `None`, stepper will
                operate in continuous mode, until stopped manually.
            forward (bool):
                Move in forward direction, if `True`. Move in backward direction
                if `False`.
        """
        
        # Send command to move and get response
        if steps is None:
            s = 'c'
        else:
            s = str(steps)
        if forward:
            cmd = 'stepu'
        else:
            cmd = 'stepd'
            
        message = cmd + ' ' + str(axis) + ' ' + s + '\r\n'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.readline().decode().split('\r\n')
        
        # Check if execution was successful
        if chars_sent != len(message) or response[-1] != '> ':
            raise ANC150IOError
        if response[-2] == 'ERROR':
            raise ANC150IOError(response[-3])
        if len(response) != 3 or response[-2] != 'OK' or response[0] != message.strip():
            raise ANC150IOError
        self._axis_moving[axis] = True
        
        # Wait estimated time until execution is completed
        self.wait_func(0.05)
        if not steps is None and steps > 1:
            res = self._get('f', axis)
            if res[-3:] != ' Hz':
                raise ANC150IOError
            freq = int(res[:-3])
            for i in range(steps):
                self.wait_func(1/freq)
            self._axis_moving[axis] = False
        
        
    def _stop_moving(self, axis) :
        """
        Stop movement of selected axis.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            axis (int): Numerical axis ID.
        """
        message = 'stop ' + str(axis) +'\r\n'
        chars_sent = self._ser.write(message.encode())
        response = self._ser.readline().decode().split('\r\n')
        
        # Check if execution was successful
        if chars_sent != len(message) or response[-1] != '> ':
            raise ANC150IOError
        if response[-2] == 'ERROR':
            raise ANC150IOError(response[-3])
        if len(response) != 3 or response[-2] != 'OK' or response[0] != message.strip():
            raise ANC150IOError
        self._axis_moving[axis] = False
    
    def register_res_function(self, func):
        """
        Registers a function, which is called to determine the current position
        of a piezo stepper. Since the ANC 150 has no capability for resisitive
        readout, this usually requires interference with other devices that are
        not related to the ANC 150 and is merely introduced as a convenience
        method, since the resistive readout is conceptually linked to the tasks
        that the ANC 150 is used for. The default readout function always
        returns *None*.
        
        Args:
            func (function): Function to be registered as resistive readout
                function. The function ``func`` has to accept exactly one
                positional argument ``axis``, which is the number the axis to
                query and two keyword arguments ``prio`` for the query priority
                as well as the boolean ``coarse``. Tue function `func` is
                called with ``coarse`` set to *True*, if the corresponding
                piezo axis is currently moving and coarser but faster readout
                is usually required, and with ``coarse`` set to false, if the
                corresponding piezo axis is currently not moving.
        
        Returns:
            None
        """
        def res_func(axis, *, prio = 0):
            if self._axis_moving[axis]:
                return func(axis, prio = prio, coarse = True)
            else:
                return func(axis, prio = prio, coarse = False)
        self._res_func = res_func
        
    def reset_res_func(self):
        """
        Resets the readout function to a function always returning *None*.
        
        Returns:
            None
        """
        def res_func(axis, *, prio = 0, coarse = False):
            return None
        self.register_res_function(res_func)

    def __enter__(self):
        if self.closed:
            self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
    
    def __del__(self):
        self.close()