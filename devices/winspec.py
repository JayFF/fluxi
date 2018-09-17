# -*- coding: utf-8 -*-
"""
Communication with WinSpec/32 via Windows COM interface (ActiveX).
"""

from .devices import Device, DeviceQty, decorator_access_control, make_enum
import enum
import ctypes
import comtypes.client
import win32com.client
import pythoncom
import threading
import time
import numpy
import re
import sys


class WinSpecError(Exception):
    """
    WinSpec communication error.
    """
    def __init__(self, message = 'Communication with WinSpec failed'):
        super().__init__(message)

try:
    import comtypes.gen.WINX32Lib as WinSpecLib
except:
    try:
        # Open connection to WinSpec via COM GUID.
        comtypes.client.GetModule(('{1A762221-D8BA-11CF-AFC2-508201C10000}', 3, 11))
        # Get WinSpec DocFile and ExpSetup.
        win32com.client.pythoncom.CoInitialize()
        import comtypes.gen.WINX32Lib as WinSpecLib
    except Exception as e:
        if not 'sphinx' in sys.modules:
            msg = "Could not auto-generate WinSpec COM interface"
            raise WinSpecError(msg).with_traceback(e.__traceback__)
        else:
            WinSpecLib = None


@enum.unique
class WinSpecADCRateCCD(enum.IntEnum):
    """
    Enum for specification of the ADC sampling rate of a CCD.
    
    Attributes
        rate100kHz (int):
            Alias for sampling rate 100kHz. Corresponds to value 6.
        rate1MHz (int):
            Alias for sampling rate 1MHz. Corresponds to value 11.
    """
    rate100kHz =  6
    rate1MHz   = 11

@enum.unique
class WinSpecDatatype(enum.IntEnum):
    """
    Enum for specification of the WinSpec datatype.
    
    Attributes
        byte (int):
            Alias for datatype byte. Corresponds to value 5.
        int16 (int):
            Alias for datatype signed 16-bit integer. Corresponds to value 1.
        long (int):
            Alias for datatype long. Corresponds to value 2.
        float (int):
            Alias for datatype float. Corresponds to value 3.
        uint16 (int):
            Alias for datatype unsigned 16-bit integer. Corresponds to value 6.
    """
    byte   = 5
    int16  = 1
    long   = 2
    float  = 3
    uint16 = 6

@enum.unique
class WinSpecDetector(enum.IntEnum):
    """
    Enum for specification of the currently used detector.
    
    Attributes
        unknown (int):
            Current detector not recognized. Corresponds to value 0.
        CCD (int):
            Current detector is a 1340x100 CCD. Corresponds to value 1.
        InGaAs (int):
            Current detector is a 1024x1 InGaAs array. Corresponds to value 2.
    """
    unknown = 0
    CCD = 1
    InGaAs = 2

@enum.unique
class WinSpecMode(enum.IntEnum):
    """
    Enum for specification of the WinSpec acquisition mode.
    
    Attributes
        fast (int):
            Alias for WinSpec fast mode. Corresponds to value 0.
        safe (int):
            Alias for WinSpec safe mode. Corresponds to value 1.
    """
    fast = 0
    safe = 1

@enum.unique
class WinSpecMirrorPosition(enum.IntEnum):
    """
    Enum for specification of the mirror position in the spectrometer
    
    Attributes
        front (int):
            Alias for mirror in front position. Corresponds to value 1.
        side (int):
            Alias for mirror in side position. Corresponds to value 2.
    """
    front = 1
    side  = 2

@enum.unique
class WinSpecShutterControl(enum.IntEnum):
    """
    Enum for specification of the WinSpec shutter control.
    
    Attributes
        normal (int):
            Alias for normal shutter mode. Corresponds to value 1.
        disabled_closed (int):
            Alias for disabled closed shutter. Corresponds to value 2.
        disabled_open (int):
            Alias for disabled open shutter. Corresponds to value 3.
    """
    normal          = 1
    disabled_closed = 2
    disabled_open   = 3

@enum.unique
class WinSpecTimingMode(enum.IntEnum):
    """
    Enum for specification of the WinSpec timing mode.
    
    Attributes
        free_run (int):
            Alias for free run mode. Corresponds to value 1.
        external_sync (int):
            Alias for external trigger mode. Corresponds to value 3.
    """
    free_run      = 1
    external_sync = 3
    

class WinSpecROI:
    """
    Simplified interface for creating WinSpec regions of interest. Instances of
    this class are iterable and return their properties in the order ``top``,
    ``left``, ``bottom``, ``right``, ``x_group``, ``y_group``, which is the
    order used by the WinSpec COM API.
    """
    
    def __init__(self, *, top = 1, bottom = 100, left = 1, right = 1340, x_group = None, y_group = None):
        self._top = top
        self._bottom = bottom
        self._left = left
        self._right = right
        self._x_group = x_group
        self._y_group = y_group
        self._item_order = ('top', 'left', 'bottom', 'right', 'x_group', 'y_group')
        
    def __iter__(self):
        for i in range(6):
            yield getattr(self, self._item_order[i])
    
    def __repr__(self):
        s = '<WinSpecROI: '
        s += ", ".join(map(lambda x: '{0} = {1}'.format(*x), zip(self._item_order, list(self))))
        s += '>'
        return s
    
    @property
    def top(self):
        """
        `Property` for the y coordinate of the top left corner of the rectangle.
        
        :getter: Get y coordinate.
        :type: int
        """
        return self._top
    
    @property
    def bottom(self):
        """
        `Property` for the y coordinate of the bottom right corner of the rectangle.
        
        :getter: Get y coordinate.
        :type: int
        """
        return self._bottom
    
    @property
    def left(self):
        """
        `Property` for the x coordinate of the top left corner of the rectangle.
        
        :getter: Get x coordinate.
        :type: int
        """
        return self._left
    
    @property
    def right(self):
        """
        `Property` for the x coordinate of the bottom right corner of the rectangle.
        
        :getter: Get x coordinate.
        :type: int
        """
        return self._right
        
    @property
    def x_group(self):
        """
        `Property` for group size used in the x direction.
        
        :getter: Returns group size used in the x direction. If no group
            size was specified, this function always returns 1.
        :type: int
        """
        if self._x_group is None:
            return 1
        else:
            return self._x_group
    
    @property
    def y_group(self):
        """
        `Property` for group size used in the y direction.
        
        :getter: Returns group size used in the y direction. If no group
            size was specified, this function always returns difference between
            top and bottom plus 1.
        :type: int
        """
        if self._y_group is None:
            return self.bottom - self.top + 1
        else:
            return self._y_group

if not WinSpecLib is None:
    winspec_speaking_names = {WinSpecLib.EXP_ACCUMS: 'accumulations', \
        WinSpecLib.EXP_ACTUAL_TEMP: 'temperature', \
        WinSpecLib.EXP_ADC_RATE: 'adc_rate', \
        WinSpecLib.EXP_BBACKSUBTRACT: 'background_subtraction', \
        WinSpecLib.EXP_CONT_CLNS: 'continuous_cleans', \
        WinSpecLib.EXP_DATATYPE: 'datatype', \
        WinSpecLib.EXP_DARKNAME: 'background_file', \
        WinSpecLib.EXP_DELAY_TIME: 'safe_mode_time', \
        WinSpecLib.EXP_EXPOSURE: 'integration_time', \
        WinSpecLib.EXP_GAIN: 'gain', \
        WinSpecLib.EXP_RUNNING: 'running', \
        WinSpecLib.EXP_SEQUENTS: 'spectra', \
        WinSpecLib.EXP_SHT_PREOPEN: 'shutter_preopen', \
        WinSpecLib.EXP_SHUTTER_CONTROL: 'shutter_control', \
        WinSpecLib.EXP_SYNC_ASYNC: 'mode', \
        WinSpecLib.EXP_TEMP_STATUS: 'temperature_locked', \
        WinSpecLib.EXP_TIMING_MODE: 'timing_mode', \
        WinSpecLib.EXP_USEROI: 'roi_enabled', \
        WinSpecLib.EXP_XDIMDET: 'detector_size_x', \
        WinSpecLib.EXP_YDIMDET: 'detector_size_y'}
    
    spec_speaking_names = {WinSpecLib.SPT_CUR_GRATING: 'grating_number', \
        WinSpecLib.SPT_CUR_POSITION: 'grating_current_position', \
        WinSpecLib.SPT_GRAT_GROOVES: 'grooves', \
        WinSpecLib.SPT_DEF_PIXELWIDTH: 'detector_pixel_width', \
        WinSpecLib.SPT_GRAT_CENTERADJ: 'offset', \
        WinSpecLib.SPT_GRAT_DETECT_ANGLE: 'detector_angle', \
        WinSpecLib.SPT_GRAT_FOCAL_LEN: 'focal_length', \
        WinSpecLib.SPT_GRAT_GROOVES: 'grooves', \
        WinSpecLib.SPT_GRAT_INCL_ANGLE: 'inclusion_angle', \
        WinSpecLib.SPT_GRAT_SLOPE_ADJ: 'adjust', \
        WinSpecLib.SPT_MIRROR_CURPOSITION: 'mirror_current_position', \
        WinSpecLib.SPT_MIRROR_NEWPOSITION: 'mirror_new_position', \
        WinSpecLib.SPT_GRAT_USERNAME: 'name', \
        WinSpecLib.SPT_NEW_POSITION: 'grating_new_position', \
        WinSpecLib.SPT_PIXEL_WIDTH: 'calibrated_pixel_width'}
    
    winspec_constants = {winspec_speaking_names[k]:k for k in winspec_speaking_names}
    spec_constants = {spec_speaking_names[k]:k for k in spec_speaking_names}

class WinSpecGrating(DeviceQty):
    def __init__(self, parent, grating_number, *, prio = 0):
        self._grating_number = grating_number
        super().__init__(parent, prio = prio)
    
    @decorator_access_control
    def get(self, attr_name):
        """
        Get current value of an attribute.
        
        Args:
            attr_name (str): String specifying, which attribute is queried. For
                simplicity, predefined constants from the dictionaries 
                ``winspec_constants`` or ``spec_constants`` should be used
                for this purpose.
        
        Returns:
            Value returned by WinSpec.
        """
        return self.parent._get_spec_attr(spec_constants[attr_name], grating_number = self.grating_number)
    
    @decorator_access_control
    def set(self, attr_name, value):
        """
        Set attribute to given value.
        
        Args:
            attr_name (str): String specifying, which attribute is to be set. For
                simplicity, predefined constants from the dictionaries 
                ``winspec_constants`` or ``spec_constants`` should be used
                for this purpose.
            value: Value to be set.
        
        Returns:
            Value returned by WinSpec.
        """
        return self.parent._set_spec_attr(spec_constants[attr_name], value, grating_number = self.grating_number)

    @property
    def grating_number(self):
        return self._grating_number
    
    @property
    def parent(self):
        return self._parent()
    
    @property
    def prio(self):
        return self._prio
    
    @property
    def adjust(self):
        return self.get('adjust')
    
    @adjust.setter
    @decorator_access_control
    def adjust(self, value):
        self.parent._set_spec_attr(spec_constants['adjust'], value, grating_number = self.grating_number)
        self.parent._winspec_spec.Current.Move()
    
    @property
    def detector_angle(self):
        return self.get('detector_angle')
    
    @detector_angle.setter
    @decorator_access_control
    def detector_angle(self, value):
        self.parent._set_spec_attr(spec_constants['detector_angle'], value, grating_number = self.grating_number)
        self.parent._winspec_spec.Current.Move()
    
    @property
    def focal_length(self):
        return self.get('focal_length')
    
    @focal_length.setter
    @decorator_access_control
    def focal_length(self, value):
        self.parent._set_spec_attr(spec_constants['focal_length'], value, grating_number = self.grating_number)
        self.parent._winspec_spec.Current.Move()
    
    @property
    def grooves(self):
        return int(self.get('grooves'))
    
    @property
    @decorator_access_control
    def ident(self):
        grooves = int(self.parent._get_spec_attr(spec_constants['grooves'], grating_number = self.grating_number))
        name = self.parent._get_spec_attr(spec_constants['name'], grating_number = self.grating_number)
        name_parts = tuple(s.strip() for s in name.split('='))
        return str(grooves) + 'g, ' + ' '.join(reversed(name_parts))
    
    @property
    def inclusion_angle(self):
        return self.get('inclusion_angle')
    
    @inclusion_angle.setter
    @decorator_access_control
    def inclusion_angle(self, value):
        self.parent._set_spec_attr(spec_constants['inclusion_angle'], value, grating_number = self.grating_number)
        self.parent._winspec_spec.Current.Move()
    
    @property
    def offset(self):
        return self.get('offset')
    
    @offset.setter
    @decorator_access_control
    def offset(self, value):
        self.parent._set_spec_attr(spec_constants['offset'], value, grating_number = self.grating_number)
        self.parent._winspec_spec.Current.Move()
    

class WinSpecQty(DeviceQty):
    _attrs = ('accumulations', 'acquisition_tries', 'acquisition_tolerance', \
              'adc_rate', 'background_file', 'datatype', 'delay_time', 'gain', \
              'grating_position', 'integration_time', 'mirror_position', 'mode', \
              'roi_enabled', 'safe_mode_time', 'shutter_control', 'shutter_preopen', \
              'spectra', 'timing_mode', 'wrap')
    
    def __init__(self, parent, *, prio = 0):
        super().__init__(parent, prio = prio)

    @decorator_access_control
    def get(self, attr_name):
        """
        Get current value of an attribute.
        
        Args:
            attr_name (str): String specifying, which attribute is queried. For
                simplicity, predefined constants from the dictionaries 
                ``winspec_constants`` or ``spec_constants`` should be used
                for this purpose.
        
        Returns:
            Value returned by WinSpec.
        """
        if attr_name in winspec_constants:
            return self.parent._get(winspec_constants[attr_name])
        elif attr_name in spec_constants:
            return self.parent._get_spec_attr(spec_constants[attr_name])
        else:
            raise WinSpecError('Unknown attribute "{0}"'.format(attr_name))
    
    @decorator_access_control
    def set(self, attr_name, value):
        """
        Set attribute to given value.
        
        Args:
            attr_name (str): String specifying, which attribute is to be set. For
                simplicity, predefined constants from the dictionaries 
                ``winspec_constants`` or ``spec_constants`` should be used
                for this purpose.
            value: Value to be set.
        
        Returns:
            Value returned by WinSpec.
        """
        if attr_name in winspec_constants:
            return self.parent._set(winspec_constants[attr_name], value)
        elif attr_name in spec_constants:
            return self.parent._set_spec_attr(spec_constants[attr_name], value)
        else:
            raise WinSpecError('Unknown attribute "{0}"'.format(attr_name))

    def set_attrs(self, config):
        """
        Set multiple attributes at once.
        
        Args:
            config (dict): Key-value pairs of attribute name and value to be
                set. Currently supported names are 
                ``accumulations``, ``acquisition_tries``, ``acquisition_tolerance``,
                ``adc_rate``, ``background_file``, ``datatype``, ``delay_time``, ``gain``,
                ``grating_position``, ``integration_time``,, ``mirror_position``, ``mode``,
                ``roi_enabled``, ``safe_mode_time``, ``shutter_control``, ``shutter_preopen``,
                ``spectra``, ``timing_mode``, and ``wrap``.
        """
        attrs = {key:config[key] for key in type(self)._attrs if key in config}
        for k, v in attrs.items():
            # Omit continuous cleans
            if not k == 'continuous_cleans' and not k == 'shutter_control':
                setattr(self, k, v)
        # Set shutter control after all other attributes to avoid problems.
        if 'shutter_control' in attrs:
            setattr(self, 'shutter_control', attrs['shutter_control'])
        # Set continuous cleans after all other attributes, since it depends
        # on the value of timing mode.
        if 'continuous_cleans' in attrs:
            if self.timing_mode.name == 'external_sync':
                setattr(self, 'continuous_cleans', attrs['continuous_cleans'])
    
    def get_attrs(self, attrs = None):
        """
        Get multiple attributes at once.
        
        Args:
            attrs (list): Attribute names to be queried. Currently supported 
                names are 
                ``accumulations``, ``acquisition_tries``, ``acquisition_tolerance``,
                ``adc_rate``, ``background_file``, ``datatype``, ``delay_time``, ``gain``,
                ``grating_position``, ``integration_time``,, ``mirror_position``, ``mode``,
                ``roi_enabled``, ``safe_mode_time``, ``shutter_control``, ``shutter_preopen``,
                ``spectra``, ``timing_mode``, and ``wrap``.
                Omitting this argument will query all of these attributes.
        
        Returns:
            Dictionary of key-value pairs.
        """
        if attrs is None:
            attrs = type(self)._attrs
        result = {}
        for k in attrs:
            result[k] = getattr(self, k)
        return result
    
    def backup_attrs(self, attrs = None):
        """
        Query specified attributes and store their values for later use.
        
        Args:
            attrs (list): Attribute names to be stored. Currently supported 
                names are
                ``accumulations``, ``acquisition_tries``, ``acquisition_tolerance``,
                ``adc_rate``, ``background_file``, ``datatype``, ``delay_time``, ``gain``,
                ``grating_position``, ``integration_time``,, ``mirror_position``, ``mode``,
                ``roi_enabled``, ``safe_mode_time``, ``shutter_control``, ``shutter_preopen``,
                ``spectra``, ``timing_mode``, and ``wrap``.
                Omitting this argument will store all of these
                attributes.
        """
        if attrs is None:
            attrs = type(self)._attrs
        attrs = tuple(key for key in type(self)._attrs if key in attrs)
        self.parent._backup.append(self.get_attrs(attrs))
        
    def restore_attrs(self, attrs = None):
        """
        Restore specified attributes from last backup.
        
        Args:
            attrs (list): Attribute names to be restored. Currently supported 
                names are
                ``accumulations``, ``acquisition_tries``, ``acquisition_tolerance``,
                ``adc_rate``, ``background_file``, ``datatype``, ``delay_time``, ``gain``,
                ``grating_position``, ``integration_time``,, ``mirror_position``, ``mode``,
                ``roi_enabled``, ``safe_mode_time``, ``shutter_control``, ``shutter_preopen``,
                ``spectra``, ``timing_mode``, and ``wrap``.
                Omitting this argument will restore all of these
                attributes
        """
        if attrs is None:
            attrs = type(self)._attrs
        try:
            config = self.parent._backup.pop()
        except IndexError:
            raise WinSpecError("No configuration backup available to resore")
        config = {key:config[key] for key in type(self)._attrs if key in attrs}
        self.set_attrs(config)

    @decorator_access_control
    def start(self):
        """
        Starts acquisition of spectra with the currently set parameters.
        """
        self.parent._start()
    
    @decorator_access_control
    def stop(self):
        """
        Stops currently running acquisition.
        """
        self.parent._stop()
        
    @decorator_access_control
    def acquire(self):
        """
        Starts acquisition of spectra with the currently set parameters. Errors
        during acquisition are detected and acquisition is repeated according
        to the values of ``_acquisition_tries`` and ``_acquisition_tolerance``.
        If acquisition keeps failing, eventually an exception is raised.
        
        Returns:
            numpy.array: The first row of this array stores the wavelength
                in nanometers, while all subsequent rows store the counts
                for the acquired spectra.
        """
        return self.parent._acquire()

    @property
    def accumulations(self):
        """
        `Property` for number of accumulations during acquisition.
        
        :getter: Get number of accumulations.
        :setter: Set number of accumulations.
        :type: int
        """
        return self.get('accumulations')
    
    @accumulations.setter
    def accumulations(self, value):
        self.set('accumulations', value)
    
    @property
    @decorator_access_control
    def acquisition_tolerance(self):
        """
        `Property` for acquisition tolerance. This number determines, which
        multiple of the actual acquisition time the program waits for WinSpec
        to notify a acquisition to be completed, until WinSpec is halted
        manually and a new try is carried out.
        
        :getter: Get acquisition tolerance.
        :setter: Set acquisition tolerance.
        :type: float
        """
        return self.parent._acquisition_tolerance
    
    @acquisition_tolerance.setter
    @decorator_access_control
    def acquisition_tolerance(self, value):
        self.parent._acquisition_tolerance = value
        
    @property
    @decorator_access_control
    def acquisition_tries(self):
        """
        `Property` for acquisition tries. This number determines,
        how many times acquisition is repeated if unsuccessful, until
        an exception is raised.
        
        :getter: Get acquisition tries.
        :setter: Set acquisition tries.
        :type: int
        """
        return self.parent._acquisition_tries
    
    @acquisition_tries.setter
    @decorator_access_control
    def acquisition_tries(self, value):
        self.parent._acquisition_tries = value
    
    @property
    def adc_rate(self):
        """
        `Property` for ADC sampling rate.
        
        :getter: Get current sampling rate. The numerical value can be
            obtained by calling ``adc_rate.value``, while the string representation
            can be obtained by calling ``adc_rate.name``.
        :setter: Set mode. The setter can either take an integer or the 
            corresponding enum as argument.
        :type: enum
        """
        return make_enum(WinSpecADCRateCCD, self.get('adc_rate'))
    
    @adc_rate.setter
    def adc_rate(self, value):
        try:
            v = make_enum(WinSpecADCRateCCD, value)
        except ValueError:
            v = value
        self.set('adc_rate', v)
        
    @property
    def background_file(self):
        """
        `Property` for background file
        
        :getter: Gets the path of the current background file.
        :setter: Sets the path of the background file.
        :type: str
        """
        return self.get('background_file')
    
    @background_file.setter
    def background_file(self, value):
        self.set('background_file', value)
    
    @property
    def background_subtraction(self):
        """
        `Property` for enabling background subtraction
        
        :getter: Returns `True` if background subtraction is being used and
            `False` otherwise.
        :setter: Sets or unsets the use of background subtraction.
        :type: bool
        """
        return bool(self.get('background_subtraction'))
    
    @background_subtraction.setter
    def background_subtraction(self, value):
        self.set('background_subtraction', int(value))
        
    @property
    def calibrated_pixel_width(self):
        """
        `Property` for the detector pixel size used for grating calibration.
        
        :getter: Returns the pixel width in micrometers.
        :type: float
        """
        return self.get('calibrated_pixel_width')
    
    @calibrated_pixel_width.setter
    @decorator_access_control
    def calibrated_pixel_width(self, value):
        self.parent._set_spec_attr(spec_constants['calibrated_pixel_width'], value)
        self.parent._winspec_spec.Current.Move()
    
    @property
    def continuous_cleans(self):
        """
        `Property` for continuous CCD cleans.
        
        :getter: Get current status. Returns `True`, if continuous cleans are
            enabled, `False` otherwise.
        :setter: Set status.
        :type: bool
        """
        return bool(self.get('continuous_cleans'))
        
    @continuous_cleans.setter
    @decorator_access_control
    def continuous_cleans(self, value):
        if WinSpecTimingMode(self.parent._get(winspec_constants['timing_mode'])).name == 'external_sync':
            self.parent._set(winspec_constants['continuous_cleans'], value)
    
    @property
    def datatype(self):
        """
        `Property` for WinSpec datatype used for data acquisition.
        
        :getter: Get current datatype. The numerical value can be
            obtained by calling ``datatype.value``, while the string representation
            can be obtained by calling ``datatype.name``.
        :setter: Set mode. The setter can either take an integer or the 
            corresponding enum as argument.
        :type: enum
        """
        return make_enum(WinSpecDatatype, self.get('datatype'))
    
    @datatype.setter
    def datatype(self, value):
        try:
            v = make_enum(WinSpecDatatype, value)
        except ValueError:
            v = value
        self.set('datatype', v)

    @property
    @decorator_access_control
    def delay_time(self):
        """
        `Property` for waiting time used to ensure that the device is
        ready in seconds.
        
        :getter: Get current delay time.
        :setter: Set delay time.
        :type: float
        """
        return self.parent._delay_time
    
    @delay_time.setter
    @decorator_access_control
    def delay_time(self, value):
        self.parent._delay_time = value
    
    @property
    def detector(self):
        """
        `Property` to determine the currently used detector.
        
        Note:
            The type of the detector is iferred from the size of the detector
            in pixels. This procedure might be **unreliable** in some situations!
            The steps to change between the detectors is currently hardcoded
            and not guaranteed to work on any other systems.
        
        :getter: Get the current detector. The numerical value can be obtained
            by calling ``detector.value``, while the string representation can
            be obtained by calling ``detector.name``.
        :setter: Set the current detector.
        :type: WinSpecDetector
        """
        size = self.detector_size
        if size == (1340, 100):
            return WinSpecDetector.CCD
        elif size == (1024, 1):
            return WinSpecDetector.InGaAs
        else:
            return WinSpecDetector.unknown
    
    @detector.setter
    def detector(self, value):
        v = make_enum(WinSpecDetector, value)
        if v.name == 'CCD':
            if self.detector.name != 'CCD':
                self.stop()
                self.shutter_control = 'disabled_closed'
                self.parent.wait_func(0.1)

                setup_ui = win32com.client.Dispatch("WinX32.HWSetupUI")
                # ' Controller Number (This line MUST be first)
                setup_ui.SetControllerNumber(1)
                # ' Camera2
                setup_ui.SetCamera(1)
                # ' Set to EEV100x1340B
                setup_ui.SetChipType(98)
                # ' Set to Shutter
                setup_ui.SetLogicOut(1)
                # ' Set to Custom
                setup_ui.SetShutterType(6)
                #' Set to Full Frame
                setup_ui.SetReadoutMode(1)
                # ' Custom Chip = FALSE
                setup_ui.SetCustomChip(0)
                # ' Custom Timing = FALSE
                setup_ui.SetCustomTiming(0)
                # ' Shutter Compensation Post Time
                setup_ui.SetShutterCompTimePost(0)
                # ' Display Mode = Normal
                setup_ui.SetDisplay(0)
                # ' Minimum Block Size
                setup_ui.SetMinBlockSize(2)
                # ' Number of Blocks
                setup_ui.SetNumBlocks(5)
                # ' Number of Cleans
                setup_ui.SetNumCleans(1)
                # ' Number of Strips Per Clean
                setup_ui.SetStripsPerClean(100)
                # ' Clean Mode
                setup_ui.SetCleanMode(2)
                # ' Set to USB(Serial)
                setup_ui.SetInterfaceType(22)
                setup_ui.Download()
                del setup_ui
                
                self.mirror_position = 'front'
                self.calibrated_pixel_width = self.detector_pixel_width
                for i in (1, 2, 3):
                    grat = self.parent.grat(prio = self.prio, number = i)
                    ident = grat.ident
                    grat.offset = self.parent._calibration[ident]['ccd_offset']
                roi = WinSpecROI(top = 40.0, bottom = 60.0, left = 1.0, right = 1340.0)
                self.roi = roi
                self.roi_enabled = True
                self.adc_rate = WinSpecADCRateCCD.rate100kHz
                self.gain = 1
                self.background_subtraction = True
                self.datatype = WinSpecDatatype.long
                self.background_file = \
                    'C:\\Program Files\\Princeton Instruments\\WinSpec\\Background_CCD_2017-07-11.SPE'
                self.mode = 'safe'
                self.safe_mode_time = 0.4
                
        elif v.name == 'InGaAs':
            if self.detector.name != 'InGaAs':
                self.stop()
                self.shutter_control = 'disabled_closed'
                self.parent.wait_func(0.1)

                setup_ui = win32com.client.Dispatch("WinX32.HWSetupUI")
                # ' Controller Number (This line MUST be first)
                setup_ui.SetControllerNumber(1)
                # ' Camera2
                setup_ui.SetCamera(2)
                # ' Set to InGaAs    1x1024
                setup_ui.SetChipType(122)
                # ' Set to Shutter
                setup_ui.SetLogicOut(1)
                # ' Set to Custom
                setup_ui.SetShutterType(6)
                #' Set to Full Frame
                setup_ui.SetReadoutMode(1)
                # ' Custom Chip = FALSE
                setup_ui.SetCustomChip(0)
                # ' Custom Timing = FALSE
                setup_ui.SetCustomTiming(0)
                # ' Shutter Compensation Post Time
                setup_ui.SetShutterCompTimePost(0)
                # ' Display Mode = Reverse
                setup_ui.SetDisplay(2)
                # ' Minimum Block Size
                setup_ui.SetMinBlockSize(2)
                # ' Number of Blocks
                setup_ui.SetNumBlocks(5)
                # ' Number of Cleans
                setup_ui.SetNumCleans(1)
                # ' Number of Strips Per Clean
                setup_ui.SetStripsPerClean(1)
                # ' Clean Mode
                setup_ui.SetCleanMode(2)
                # ' Set to USB(Serial)
                setup_ui.SetInterfaceType(22)
                setup_ui.Download()
                del setup_ui

                self.mirror_position = 'side'
                self.calibrated_pixel_width = self.detector_pixel_width
                for i in (1, 2, 3):
                    grat = self.parent.grat(prio = self.prio, number = i)
                    ident = grat.ident
                    grat.offset = self.parent._calibration[ident]['ingaas_offset']
                
                self.mode = 'safe'
                self.safe_mode_time = 0.4
        
    @property
    def detector_pixel_width(self):
        """
        `Property` to determine size of a single pixel of the current detector.
        
        :getter: Returns the pixel width in micrometers.
        :type: float
        """
        return self.get('detector_pixel_width')
    
    @property
    def detector_size(self):
        """
        `Property` to determine size of current detecor in pixels.
        
        :getter: Returns a tuple with the number of pixels in x and y direction,
            respectively.
        :type: tuple
        """
        return (self.get('detector_size_x'), self.get('detector_size_y'))
    
    @property
    @decorator_access_control
    def float_tolerance(self):
        """
        `Property` for float tolerance. This number determines the maximum
        allowed relative difference between a float parameter to be set and the
        actual value assumed by WinSpec.
        
        :getter: Get float tolerance.
        :setter: Set float tolerance.
        :type: float
        """
        return self.parent._float_tolerance
    
    @float_tolerance.setter
    @decorator_access_control
    def float_tolerance(self, value):
        self.parent._float_tolerance = value
        
    @property
    def gain(self):
        """
        `Property` for detector gain.
        
        :getter: Get detector gain.
        :setter: Set detector gain.
        :type: int
        """
        return self.get('gain')
    
    @gain.setter
    def gain(self, value):
        self.set('gain', value)
        
    @property
    def grating_position(self):
        """
        `Property` for center wavelength of the current grating.
        
        :getter: Get center wavelength of current grating in nanometer.
        :setter: Set center wavelength of current grating.
        :type: float
        """
        return self.get('grating_current_position')
    
    @grating_position.setter
    @decorator_access_control
    def grating_position(self, value):
        self.parent._set_spec_attr(spec_constants['grating_new_position'], value)
        self.parent._winspec_spec.Current.Move()
    
    @property
    def integration_time(self):
        """
        `Property` for integration time in seconds.
        
        :getter: Get current integration time.
        :setter: Set integration time.
        :type: float
        """
        return self.get('integration_time')
    
    @integration_time.setter
    def integration_time(self, value):
        self.set('integration_time', value)
    
    @property
    def mirror_position(self):
        """
        `Property` for spectrometer mirror position.
        
        :getter: Get current mirror position. The numerical value can be
            obtained by calling ``mirror_position.value``, while the string
            representation can be obtained by calling ``mirror_position.name``.
        :setter: Set mode. The setter can either take an integer or the 
            corresponding enum as argument.
        :type: enum
        """
        return make_enum(WinSpecMirrorPosition, self.get('mirror_current_position'))
    
    @mirror_position.setter
    @decorator_access_control
    def mirror_position(self, value):
        try:
            v = make_enum(WinSpecMirrorPosition, value)
        except ValueError:
            v = value
        self.parent._set_spec_attr(spec_constants['mirror_new_position'], v)
        self.parent._winspec_spec.Current.Move()
    
    @property
    def mode(self):
        """
        `Property` for WinSpec acquisition mode.
        
        :getter: Get current acquisition mode. The numerical value can be
            obtained by calling ``mode.value``, while the string representation
            can be obtained by calling ``mode.name``.
        :setter: Set mode. The setter can either take an integer or the 
            corresponding enum as argument.
        :type: enum
        """
        return make_enum(WinSpecMode, self.get('mode'))
    
    @mode.setter
    def mode(self, value):
        try:
            v = make_enum(WinSpecMode, value)
        except ValueError:
            v = value
        self.set('mode', v)
    
    @property
    @decorator_access_control
    def roi(self):
        """
        `Property` for getting and setting the region of interest (ROI).
        
        :getter: Get the first ROI. Retrieving other stored ROIs is currently
            not supported.
        :setter: Clears all ROIs and sets the first ROI.
        :type: WinSpecROI
        """
        return self.parent._get_roi()
    
    @roi.setter
    @decorator_access_control
    def roi(self, roi):
        self.parent._set_roi(roi)
    
    @property
    def roi_enabled(self):
        """
        `Property` for enabling usage of a region of interest (ROI).
        
        :getter: Returns `True` if a ROI is being used and `False` otherwise.
        :setter: Sets or unsets the use of a ROI.
        :type: bool
        """
        return bool(self.get('roi_enabled'))
    
    @roi_enabled.setter
    def roi_enabled(self, value):
        self.set('roi_enabled', value)
    
    @property
    def running(self):
        """
        `Property` to check if an experiment is running in WinSpec.
        
        :getter: Return `True` if an experiment is running and `False`
            otherwise.
        :type: bool
        """
        return bool(self.get('running'))
    
    @property
    def safe_mode_time(self):
        """
        `Property` for additional waiting time in seconds in case safe mode
        is used.
        
        :getter: Get current save mode time.
        :setter: Set safe mode time.
        :type: float
        """
        return self.get('safe_mode_time')
        
    @safe_mode_time.setter
    def safe_mode_time(self, value):
        self.set('safe_mode_time', value)
    
    @property
    def shutter_control(self):
        """
        `Property` for WinSpec shutter control.
        
        :getter: Get shutter control. The numerical
            value can be obtained by calling ``shutter_control.value``,
            while the string representation can be obtained by calling
            ``shutter_control.name``.
        :setter: Set shutter control. The setter can either take an integer or the
            corresponding enum as argument.
        :type: enum
        """
        return make_enum(WinSpecShutterControl, self.get('shutter_control'))
    
    @shutter_control.setter
    def shutter_control(self, value):
        try:
            v = make_enum(WinSpecShutterControl, value)
        except ValueError:
            v = value
        self.set('shutter_control', v)
    
    @property
    def shutter_preopen(self):
        """
        `Property` to determine if shutter is preopened during acquisition.
        
        :getter: Get current status. Return
            `True` if shutter is preopened during acquisition and `False`
            otherwise.
        :setter: Enable or disable shutter preopen mode.
        :type: bool
        """
        return bool(self.get('shutter_preopen'))
    
    @shutter_preopen.setter
    def shutter_preopen(self, value):
        self.set('shutter_preopen', value)
    
    @property
    def spectra(self):
        """
        `Property` for number of spectra to be acquired.
        
        :getter: Get number of spectra.
        :setter: Set number of spectra.
        :type: int
        """
        return self.get('spectra')
    
    @spectra.setter
    def spectra(self, value):
        self.set('spectra', value)
        
    @property
    def temperature(self):
        """
        `Property` to check current detector temperature.
        
        :getter: Return current detector temperature.
        :type: float
        """
        return self.get('temperature')
    
    @property
    def temperature_locked(self):
        """
        `Property` to check whether detector temperature is locked.
        
        :getter: Return `True` if detector temperature is locked and
            `False` otherwise.
        :type: float
        """
        return self.get('temperature_locked')
    
    @property
    def timing_mode(self):
        """
        `Property` for WinSpec timing mode.
        
        :getter: Get timing mode. The numerical
            value can be obtained by calling ``timing_mode.value``,
            while the string representation can be obtained by calling
            ``timing_mode.name``.
        :setter: Set timing mode. The setter can either take an integer or the
            corresponding enum as argument.
        :type: enum
        """
        return make_enum(WinSpecTimingMode, self.get('timing_mode'))
    
    @timing_mode.setter
    def timing_mode(self, value):
        try:
            v = make_enum(WinSpecTimingMode, value)
        except ValueError:
            v = value
        self.set('timing_mode', v)

    @property
    @decorator_access_control
    def wrap(self):
        """
        `Property` for wrap-around of negative numbers. If wrap is set to `True`,
        negative numbers in measured data will be wrapped around to yield
        positive numbers.
        
        :getter: Get current wrap status.
        :setter: Set wrap staus.
        :type: bool
        """
        return bool(self.parent._wrap)
    
    @wrap.setter
    @decorator_access_control
    def wrap(self, value):
        self.parent._wrap = bool(value)
    


class WinSpec(Device):
    """
    Communication with WinSpec/32 via Windows COM interface (ActiveX).
    
    Note:
        For this class to work properly, WinSpec needs to register it's ActiveX
        library in the Windows registry. This works automatically on older
        versions of Windows. As of Windows 7, however, WinSpec needs to be
        started **once** as Administrator to perform this task. No user
        interaction is needed, WinSpec should do this on it's own.
        
    Args:
        config (dictionary): Dictionary of key-value pairs that determines
            the configuration of the measurement performed by WinSpec. Entries
            ``accumulations``, ``acquisition_tries``, ``acquisition_tolerance``, 
            ``delay_time``, ``integration_time``, ``mode``, ``safe_mode_time``,
            ``shutter_control``, ``shutter_preopen``, ``spectra``, ``timing_mode``
            and ``wrap`` are currently supported.
    
    Attributes:
        _acquisition_tries (int):
            Sometimes acquisition in WinSpec fails. This number determines,
            how many times acquisition is repeated if unsuccessful, until
            an exception is raised. Default value is 10.
        _acquisition_tolerance (float):
            If acquisition in WinSpec is unsuccessful, WinSpec never notifies
            the current acquisition as completed. This number determines, which
            multiple of the actual acquisition time the program waits for WinSpec
            to notify a acquisition to be completed, until WinSpec is halted
            manually and a new try is carried out. Default value is 2.0.
        _delay_time (float):
            Additional waiting time used to ensure that the device is
            ready in seconds. Default is 0.1.
        _float_tolerance (float):
            Some float type properties cannot be set with arbitrary accuracy
            by WinSpec. This number determines the maximum allowed
            relative difference between a float parameter to be set and the
            actual value assumed by WinSpec. Default value is 0.01.
        _wrap (bool):
            By default, WinSpec stores data as signed 16-bit integers, meaning
            that data points with more than 32786 counts will be displayed as
            negative numbers. This can be corrected for by setting wrapping
            around negative numbers, to obtain the correct positive values.
            Default value is `True`.
    """

    def __init__(self, config):
        doc = win32com.client.Dispatch("WinX32.DocFile.3")
        exp = win32com.client.Dispatch("WinX32.ExpSetup")
        spc = win32com.client.Dispatch("WinX32.SpectroObjMgr")
        self._winspec_doc_dict = dict()
        self._winspec_exp_dict = dict()
        self._winspec_spc_dict = dict()
        self._winspec_doc_dict[threading.get_ident()] = doc
        self._winspec_doc_id = pythoncom.CoMarshalInterThreadInterfaceInStream(pythoncom.IID_IDispatch, doc)
        self._winspec_exp_dict[threading.get_ident()] = exp
        self._winspec_exp_id = pythoncom.CoMarshalInterThreadInterfaceInStream(pythoncom.IID_IDispatch, exp)
        self._winspec_spc_dict[threading.get_ident()] = spc
        self._winspec_spc_id = pythoncom.CoMarshalInterThreadInterfaceInStream(pythoncom.IID_IDispatch, spc)
        self._backup = list()
        
        self._acquisition_tries = int()
        self._acquisition_tolerance = int()
        self._float_tolerance = float()
        self._delay_time = float()
        self._wrap = bool()
        
        super().__init__(WinSpecQty, WinSpecError)
        
        # Set config default values
        if not 'acquisition_tries' in config:
            config['acquisition_tries'] = 10
        if not 'acquisition_tolerance' in config:
            config['acquisition_tolerance'] = 2.0
        if not 'float_tolerance' in config:
            config['float_tolerance'] = 0.01
        if not 'delay_time' in config:
            config['acquisition_tries'] = 0.1
        if not 'wrap' in config:
            config['wrap'] = True

        if 'calibration' in config:
            self._calibration = config['calibration']
        else:
            self._calibration = None
        
        self.qty(prio = 9999).backup_attrs()
        self._float_tolerance = config['float_tolerance']
        self.qty(prio = 9999).set_attrs(config)
    
    def open(self):
        print('Opening connection to WinSpec... ', end = '', flush = True)
        
        # Is there already a running experiment?
        running = self._get(winspec_constants['running'])
        if running:
            if ctypes.windll.user32.MessageBoxA(0, \
            b"An experiment is still running in Winspec. Do you want to stop it now?", \
            b"Running experiment", 4) == 7:
                # No.
                raise WinSpecError
            else:
                # Yes.
                self._stop()
        
        super().open()
        print('Success.', flush = True)
    
    def close(self):
        super().close()
        
#        # Restore attributes, if there is a backup
#        if len(self._backup) > 1:
#            # Iterate over all stored WinSpec settings
#            for attr, name in winspec_speaking_names:
#                if name in self._backup[0]:
#                    # Omit continuous cleans and shutter control
#                    if not name in ('continuous_cleans', 'shutter_control'):
#                        self._set(attr, self._backup[0][name])
#            
#            # Restore continuous cleans, if timing mode is correct
#            if 'continuous_cleans' in self._backup[0]:
#                if WinSpecTimingMode(self._get(winspec_constants['timing_mode'])).name == 'external_sync':
#                    self._set(winspec_constants['continuous_cleans'], self._backup[0]['continuous_cleans'])
#        
#        # Close shutter for safety reasons
#        self._set(winspec_constants['shutter_control'], WinSpecShutterControl.disabled_closed)
        
        # Reset attribute backup
        self._backup = list()
    
    def grat(self, *, prio = 0, number = None, ident = None):
        if number:
            return WinSpecGrating(self, number, prio = prio)
        if ident:
            gratings = map(lambda n: WinSpecGrating(self, n, prio = prio), (1, 2, 3))
            ident_strings = map(lambda g: g.ident, gratings)
            matches = map(lambda s: re.match('.*'.join(('', ident, '')), s), ident_strings)
            indices = [index for index, value in enumerate(matches) if not value is None]
            if len(indices) < 1:
                raise WinSpecError('Found no matching grating.')
            if len(indices) > 1:
                raise WinSpecError("Couldn't identify unique grating.")
            return WinSpecGrating(self, indices[0] + 1, prio = prio)
        grating_number = self._get_spec_attr(spec_constants['grating_number'])
        return WinSpecGrating(self, grating_number, prio = prio)
    
    @property
    def _winspec_doc(self):
        if threading.get_ident() in self._winspec_doc_dict:
            return self._winspec_doc_dict[threading.get_ident()]
        else:
            pythoncom.CoInitialize()
            doc = win32com.client.Dispatch(pythoncom.CoGetInterfaceAndReleaseStream(self._winspec_doc_id, pythoncom.IID_IDispatch))
            self._winspec_doc_dict[threading.get_ident()] = doc
            return doc
            
    @property
    def _winspec_exp(self):
        if threading.get_ident() in self._winspec_exp_dict:
            return self._winspec_exp_dict[threading.get_ident()]
        else:
            pythoncom.CoInitialize()
            exp = win32com.client.Dispatch(pythoncom.CoGetInterfaceAndReleaseStream(self._winspec_exp_id, pythoncom.IID_IDispatch))
            self._winspec_exp_dict[threading.get_ident()] = exp
            return exp
            
    @property
    def _winspec_spec(self):
        if threading.get_ident() in self._winspec_spc_dict:
            return self._winspec_spc_dict[threading.get_ident()]
        else:
            pythoncom.CoInitialize()
            spc = win32com.client.Dispatch(pythoncom.CoGetInterfaceAndReleaseStream(self._winspec_spc_id, pythoncom.IID_IDispatch))
            self._winspec_spc_dict[threading.get_ident()] = spc
            return spc
            
    def _get(self, attr):
        """
        Get current value of an attribute.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.
        
        Args:
            attr (int): Integer specifying, which attribute is queried. For
                simplicity, predefined constants from the WINX32Lib should be
                used for this purpose.
        
        Returns:
            Value returned by WinSpec.
        """
        res = self._winspec_exp.GetParam(attr)
        if res[1] and res != (None, 1):
            if attr in winspec_speaking_names:
                raise WinSpecError('Could not get attribute "{0}".'.format(winspec_speaking_names[attr]))
            else:
                raise WinSpecError("Could not get attribute no. {0}.".format(attr))
        else:
            return res[0]
    
    def _get_spec_attr(self, attr, *, grating_number = 0):
        """
        Get value of an attribute from currently active spectrograph.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.
        
        Args:
            attr (int): Integer specifying, which attribute is queried. For
                simplicity, predefined constants from the WINX32Lib should be
                used for this purpose.
        
        Returns:
            Value returned by WinSpec.
        """
        res = self._winspec_spec.Current.GetParam(attr, grating_number)
        if res[1] and res != (None, 1):
            if attr in spec_speaking_names:
                raise WinSpecError('Could not get attribute "{0}".'.format(spec_speaking_names[attr]))
            else:
                raise WinSpecError("Could not get attribute no. {0}.".format(attr))
        else:
            return res[0]
    
    def _set(self, attr, value):
        """
        Set attribute to given value.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.
        
        Args:
            attr (int): Integer specifying, which attribute is queried. For
                simplicity, predefined constants from the WINX32Lib should be
                used for this purpose.
            value: Value to be set.
        
        Returns:
            Value returned by WinSpec.
        """
        self._winspec_exp.SetParam(attr, value)
        
        # Check if value has been set
        res = self._get(attr)
        if type(value) is float or type(res) is float:
            if not abs(res - value) <= self._float_tolerance * abs(value):
                print(abs(res - value))
                if attr in winspec_speaking_names:
                    raise WinSpecError('Could not set attribute "{0}".'.format(winspec_speaking_names[attr]))
                else:
                    raise WinSpecError("Could not set attribute no. {0}.".format(attr))
        else:
            if res != value:
                if attr in winspec_speaking_names:
                    raise WinSpecError('Could not set attribute "{0}".'.format(winspec_speaking_names[attr]))
                else:
                    raise WinSpecError("Could not set attribute no. {0}.".format(attr))
            
    def _set_spec_attr(self, attr, value, *, grating_number = 0):
        """
        Set attribute of currently active spectrometer to given value.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.
        
        Args:
            attr (int): Integer specifying, which attribute is queried. For
                simplicity, predefined constants from the WINX32Lib should be
                used for this purpose.
            value: Value to be set.
        
        Returns:
            Value returned by WinSpec.
        """
        self._winspec_spec.Current.SetParam(attr, value, grating_number)
        
        # Check if value has been set
        res = self._get_spec_attr(attr, grating_number = grating_number)
        if type(value) is float or type(res) is float:
            if not abs(res - value) <= self._float_tolerance * abs(value):
                print(abs(res - value))
                if attr in spec_speaking_names:
                    raise WinSpecError('Could not set attribute "{0}".'.format(winspec_speaking_names[attr]))
                else:
                    raise WinSpecError("Could not set attribute no. {0}.".format(attr))
        else:
            if res != value:
                if attr in spec_speaking_names:
                    raise WinSpecError('Could not set attribute "{0}".'.format(winspec_speaking_names[attr]))
                else:
                    raise WinSpecError("Could not set attribute no. {0}.".format(attr))
            
    def _start(self):
        """
        Starts acquisition of spectra with the currently set parameters.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.
        """
        res = self._winspec_exp.Start(self._winspec_doc)
        if not res[0]:
            raise WinSpecError("Couldn't start experiment.")

    def _stop(self):
        """
        Stops currently running acquisition.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.
        """
        self._winspec_exp.Stop()

    def _acquire(self):
        """
        Starts acquisition of spectra with the currently set parameters. Errors
        during acquisition are detected and acquisition is repeated according
        to the values of ``_acquisition_tries`` and ``_acquisition_tolerance``.
        If acquisition keeps failing, eventually an exception is raised.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.

        Returns:
            numpy.array: The first row of this arraystores the wavelength
                in nanometers, while all subsequent rows store the counts
                for the acquired spectra.
        """
        success = False
        tries = 0
        safe_mode_time = self._get(winspec_constants['safe_mode_time'])
        integration_time = self._get(winspec_constants['integration_time'])
        spectra = self._get(winspec_constants['spectra'])
        
        while not success and tries < self._acquisition_tries:
            # Start the experiment
            self._start()
            
            # Wait expected duration of experiment plus delay time
            success = True
            self.wait_func(safe_mode_time + integration_time + self._delay_time)
            
            # If experiment is still running, wait at most time specified
            # by _acquisition_tolerance.
            timestamp = time.time()
            delta = self._acquisition_tolerance * integration_time
            while self._get(winspec_constants['running']):
                if time.time() - timestamp > delta:
                    self._stop()
                    success = False
                    tries += 1
                    break
                time.sleep(self._delay_time)
        
        # Raise exception, if acquisition was not successful after at most
        # _acquisition_tries attempts.
        if not success:
            raise WinSpecError("Error during data acquisition.")
    
        # Pass an empty variant to WinSpec, so it will allocate memory for 
        # data transfer.
        var = win32com.client.VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_NULL | pythoncom.VT_BYREF, None)
        
        # WinSpec returns a list of one-tuples for each spectrum. Turn this
        # into a list of lists.
        if self._wrap:
            data = list((list(map(lambda x: x[0] if x[0] >= 0 else 65536 + x[0], \
                self._winspec_doc.GetFrame(i, var))) \
                for i in range(1, 1 + spectra)))
        else:
            data = list((list(map(lambda x: x[0], \
                self._winspec_doc.GetFrame(i, var))) \
                for i in range(1, 1 + spectra)))
        
        # Get calibration
        calibration = self._winspec_doc.GetCalibration()
        if calibration.Order != 2:
            raise WinSpecError("Cannot handle wavelength calibration.")
    
        # Winspec doesn't actually store the wavelength information as an
        # array but instead calculates it every time a spectrum is plotted
        # using the calibration information stored with the spectrum. The
        # calibration coefficients translate to a polynomial.
        p = numpy.array([calibration.PolyCoeffs(2),
                         calibration.PolyCoeffs(1),
                         calibration.PolyCoeffs(0)])
                         
        # Get wavelength from polynomial.
        wavelength = numpy.polyval(p, range(1, 1 + len(data[0])))
        
        return numpy.concatenate(([wavelength], data), axis = 0)
    
    def _get_roi(self):
        """
        Get first specified ROI.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.

        Note:
            More than one ROI is currently not supported.
        
        Returns:
            WinSpecROI
        """
        COM_ROI = self._winspec_exp.GetROI(1)
        roi = WinSpecROI(top = COM_ROI.Top, bottom = COM_ROI.Bottom,
                         left = COM_ROI.Left, right = COM_ROI.right,
                         x_group = COM_ROI.XGroup, y_group = COM_ROI.YGroup)
        return roi
    
    def _set_roi(self, roi):
        """
        Clear current ROIs and set a new ROI.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to WinSpec. It should not be used for external function calls.

        Args:
            roi (WinSpecROI):
                ROI to be set.
        """
        COM_ROI = win32com.client.Dispatch("WinX32.ROIRect")
        COM_ROI.Set(*list(roi))
        self._winspec_exp.ClearROIs()
        self._winspec_exp.SetROI(COM_ROI)

    def __enter__(self):
        if self.closed:
            self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
    
    def __del__(self):
        self.close()