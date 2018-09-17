# -*- coding: utf-8 -*-
"""
Interface for Lasertack LR1 spectrometer.
"""

from .devices import Device, DeviceQty, decorator_access_control
import time
import numpy
import ctypes


class LasertackLR1IOError(Exception):
    """
    Lasertack LR1 communication error.
    """
    def __init__(self, message = 'Communication with device failed'):
        super().__init__(message)
        

class LasertackLR1Qty(DeviceQty):
    """
    Class to communicate with Lasertack LR1 ensuring mutually exclusive access 
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
    _attrs = ('integration_time', )

    def __init__(self, parent, *, prio = 0):
        super().__init__(parent, prio = prio)

    def set_attrs(self, config):
        """
        Set multiple attributes at once.
        
        Args:
            config (dict): Key-value pairs of attribute name and value to be
                set. Currently supported names are only ``integration_time``.
        """
        attrs = {key:config[key] for key in type(self)._attrs if key in config}
        for k, v in attrs.items():
            setattr(self, k, v)
    
    def get_attrs(self, attrs = None):
        """
        Get multiple attributes at once.
        
        Args:
            attrs (list): Attribute names to be queried. Currently supported 
                names are only ``integration_time``.
        
        Returns:
            Dictionary of key-value pairs.
        """
        if attrs is None:
            attrs = type(self)._attrs
        result = {}
        for k in attrs:
            result[k] = getattr(self, k)
        return result
    
    @property
    @decorator_access_control
    def integration_time(self):
        """
        `Property` for integration time in seconds.
        
        :getter: Get current integration time.
        :setter: Set integration time.
        :type: float
        """
        return self.parent._integration_time
    
    @integration_time.setter
    @decorator_access_control
    def integration_time(self, value):
        self.parent._integration_time = value

    @decorator_access_control
    def acquire(self):
        """
        Starts acquisition of spectra with the currently set parameters.
        
        Returns:
            numpy.array: The first row of this array stores the wavelength
                in nanometers, while the second row stores the counts
                for the acquired spectrum.
        """
        return self.parent._acquire()

        
class LasertackLR1(Device):
    """
    Interface for Lasertack LR1 spectrometer.

    Args:
        config (dictionary): Dictionary of key-value pairs that determines
            the configuration of the spectrometers. Entry ``dll_path``
            is mandatory. Option ``integration_time`` is currently supported.
            
    Attributes:
        _dll_path (str): Path to DLL library.
        _integration_time (float): Integration time in seconds.
    """

    def __init__(self, config):
        # Try to get DLL file
        try:
            self._dll_path = config['dll_path']
        except KeyError as e:
            msg = "No DLL path specified for Lasertack LR1."
            raise Exception(msg).with_traceback(e.__traceback__)
        
        try:
            self._adcdll = ctypes.CDLL(self._dll_path)
        except OSError as e:
            msg = 'DLL file "' + self._dll_path + '" not found.'
            raise Exception(msg).with_traceback(e.__traceback__)

        # Setup functions
        self._read_and_write_to_device_func = \
            self._adcdll.ReadAndWriteToDevice
        self._read_and_write_to_device_func.restype = \
            ctypes.POINTER(ctypes.c_ubyte)
        self._read_and_write_to_device_func.argtypes = \
            [ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
        
        self._read_and_write_to_device_new_func = \
            self._adcdll.ReadAndWriteToDevice_new
        self._read_and_write_to_device_new_func.restype = \
            ctypes.POINTER(ctypes.c_ubyte)
        self._read_and_write_to_device_new_func.argtypes = \
            [ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]

        self._get_spectra_func = \
            self._adcdll.GetSpectra
        self._get_spectra_func.restype = ctypes.c_int
        self._get_spectra_func.argtypes = \
            [ctypes.POINTER(ctypes.c_int16), ctypes.c_ubyte, ctypes.c_uint16,
             ctypes.c_uint16, ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_uint16,
             ctypes.c_uint16]
        
        # Setup variables
        self._input_report = (ctypes.c_ubyte * 64)()
        self._output_report = (ctypes.c_ubyte * 64)()
        self._input_spec = (ctypes.c_int16 * 3653)()
        self._integration_time = float()
        
        # Open connection to device
        super().__init__(LasertackLR1IOError)
    
        # Set config default values
        if not 'integration_time' in config:
            config['integration_time'] = 20e-3
        
        self.qty(prio = 9999).set_attrs(config)
        
    def open(self):
        print('Opening connection to Lasertack LR1... ', end = '', flush = True)
        
        # Prepare variables for initialization function call.
        for i in range(64):
            self._output_report[i] = 3
            self._input_report[i] = 3
        self._output_report[1] = 241
        
        # Initialize and check for errors
        self._read_and_write_to_device_func(self._input_report, self._output_report, 0)
        
        if not self._output_report[9] == 15:
            raise LasertackLR1IOError
        
        # Prepare variables to get calibration coefficients
        for i in range(64):
            self._output_report[i] = 0
            self._input_report[i] = 3
        self._output_report[1] = 161      
        
        # Get calibration coefficients and check for errors
        self._read_and_write_to_device_new_func(self._input_report, self._output_report, 0)
        
        if not self._output_report[9] == 15:
            raise LasertackLR1IOError
            
        # Convert calibration coefficients from ASCII to floats.
        chars_A = (c for c in list(map(chr, list(self._input_report)[0:15])) if not c == '\x00')
        chars_B = (c for c in list(map(chr, list(self._input_report)[16:31])) if not c == '\x00')
        chars_C = (c for c in list(map(chr, list(self._input_report)[32:47])) if not c == '\x00')
        
        A = float(''.join(chars_A))
        B = float(''.join(chars_B))
        C = float(''.join(chars_C))
        
        # Calculate wavelength from calibration coefficients
        p = numpy.array([A, B, C])
                         
        # Get wavelength from polynomial.
        self._wavelength = numpy.polyval(p, range(3653))
        
        super().open()
        print('Success.', flush = True)
    
    def close(self):
        super().close()
    
    def qty(self, *, prio = 0):
        return LasertackLR1Qty(self, prio = prio)
    
    def _acquire(self):
        """
        Starts acquisition of spectra with the currently set parameters.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.

        Returns:
            numpy.array: The first row of this array stores the wavelength
                in nanometers, while the second row stores the counts
                for the acquired spectrum.
        """
        # Prepare high and low bits of exposure
        exposure = round(max(self._integration_time / 2.375e-3, 2))
        exposure_low = exposure & 0xff
        exposure_high = (exposure >> 8) & 0xff
        
        # Prepare variables for acquisition
        for i in range(64):
            self._output_report[i] = 0
            self._input_report[i] = 3
        self._output_report[1] = 1
        self._output_report[2] = exposure_low
        self._output_report[3] = 1
        self._output_report[5] = 1
        self._output_report[7] = exposure_high
        
        # Initiate acquisition and check for errors
        self._read_and_write_to_device_func(self._input_report, self._output_report, 0)
        
        if not self._output_report[9] == 15:
            raise LasertackLR1IOError

        # Wait integration time
        time.sleep(self._integration_time)

        # Wait until device signalizes that acquisition is finished
        while True:
            # Prepare variables for status request
            for i in range(64):
                self._output_report[i] = 0
                self._input_report[i] = 3
            self._output_report[1] = 2
            
            # Request status and check for errors
            self._read_and_write_to_device_func(self._input_report, self._output_report, 0)
            
            if not self._output_report[9] == 15:
                raise LasertackLR1IOError
            
            # Break loop, if device is ready
            if self._input_report[3] == 0:
                break
        
        # Reset address
        self._reset_address()
        
        # Prepare variables to get spectrum
        for i in range(3653):
            self._input_spec[i] = 0
        spec_nmb =  ctypes.c_ubyte(1)
        end_pix = ctypes.c_uint16(3652)
        start_pix = ctypes.c_uint16(0)
        fast = ctypes.c_ubyte(0)
        test1 = ctypes.c_ubyte(0)
        tot_start_pix = ctypes.c_uint16(33)
        tot_end_pix = ctypes.c_uint16(3685)
        
        # Get spectrum
        self._get_spectra_func(self._input_spec, spec_nmb, start_pix, end_pix, \
            fast, test1, tot_start_pix, tot_end_pix)
        
        # Reset address
        self._reset_address()
        
        return numpy.concatenate(([self._wavelength], [self._input_spec]), axis = 0)        
    
    def _reset_address(self):
        """
        Reset spectrometer address. This function is employed during acquisition
        and should normally not be called externally.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.
        """
        # Prepare variables for address reset
        for i in range(64):
            self._output_report[i] = 0
            self._input_report[i] = 3
        self._output_report[1] = 3
        
        # Reset address and check for errors
        self._read_and_write_to_device_func(self._input_report, self._output_report, 0)
        
        if not self._output_report[9] == 15:
            raise Exception('Communication with Lasertack failed.')
    
    def __enter__(self):
        if self.closed:
            self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
    
    def __del__(self):
        self.close()