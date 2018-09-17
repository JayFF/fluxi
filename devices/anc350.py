# -*- coding: utf-8 -*-
"""
Interface for ANC 350 piezo controller. This is an adaption of PyANC350 by
Rob Heath and all credit goes to him. For more details see
https://github.com/Laukei/attocube-ANC350-Python-library
or http://robheath.me.uk.

Note:
    This module is intended to work with version 2 of the ANC driver and
    adaptions will be necessary when working with versions 3 or 4. To work
    properly, it needs access to the libraries ``anc350v2.dll``, ``libusb0.dll``
    and ``nhconnect.dll``. It may be necessary to add the location of these files
    to the ``PATH`` envirionment variable.
"""

from .devices import Device, DeviceQty, decorator_access_control, make_enum
import ctypes
import enum
import math
from . import anc350_lib

class ANC350IOError(Exception):
    """
    ANC 350 communication error.
    """
    def __init__(self, message = 'Communication with device failed'):
        super().__init__(message)


@enum.unique
class ANC350AmplitudeControlMode(enum.IntEnum):
    """
    Enum for specification of the amplitude control mode.
    
    Attributes
        speed (int):
            Alias for speed mode. Corresponds to value 0.
        amplitude (int):
            Alias for amplitude. Corresponds to value 1.
        step_size (int):
            Alias for step_size. Corresponds to value 2.
    """
    speed = 0
    amplitude = 1
    step_size = 2

@enum.unique
class ANC350Direction(enum.IntEnum):
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
class ANC350TriggerEdge(enum.IntEnum):
    """
    Enum for specification of the trigger edge.
    
    Attributes
        rising (int):
            Alias for trigger on rising slope. Corresponds to value 0.
        amplitude (int):
            Alias for trigger on falling slope. Corresponds to value 1.
    """
    rising = 0
    falling = 1

@enum.unique
class ANC350TriggerModeIn(enum.IntEnum):
    """
    Enum for specification of the input trigger mode.
    
    Attributes
        disabled (int):
            Alias for no trigger. Corresponds to value 0.
        quadrature (int):
            Alias for three pairs of trigger signals that are used to accept
            AB-signals for relative positioning. Corresponds to value 1.
        coarse (int):
            Alias for using the trigger signals to generate coarse steps.
            Corresponds to value 2
    """
    disabled  = 0
    quadrature = 1
    coarse = 2

@enum.unique
class ANC350TriggerModeOut(enum.IntEnum):
    """
    Enum for specification of the output trigger mode.
    
    Attributes
        disabled (int):
            Alias for no trigger. Corresponds to value 0.
        position (int):
            Alias for trigger that reacts to the defined position ranges with
            the selected polarity. Corresponds to value 1.
        quadrature (int):
            Alias for three pairs of triggers that are used to signal relative
            movement as AB-signals. Corresponds to value 2.
        IcHaus (int):
            Alias for triggers that are used to output the internal position
            signal of num-sensors. Corresponds to value 3.
    """
    disabled = 0
    position = 1 
    quadrature = 2
    IcHaus = 3

@enum.unique
class ANC350TriggerPolarity(enum.IntEnum):
    """
    Enum for specification of the output trigger mode.
    
    Attributes
        low_active (int):
            Alias for lower edge trigger. Corresponds to value 0.
        high_active (int):
            Alias for higher edge trigger. Corresponds to value 1.
    """
    low_active = 0
    high_active = 1

class ANC350Axis(DeviceQty):
    """
    Class to communicate with a single controller axis.
    
    Args:
        parent (ANC350):
            The parent ANC350 instance that the axis is derived from.
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
    def get(self, getter, getter_args):
        """
        Read current value of an attribute.
        
        Args:
            getter (str): Name of the library function to query according
                to the name mapping in the anc350_lib module.
            getter_args (tuple): List of arguments to pass to the specified
                getter. Any mutable argument (used by the library function
                to return values) is to be replaced with *None*.

        Returns:
            tuple: Values of the mutable argument in the same order as given in
                ``getter_args``.
        """
        return self.parent._get(getter, getter_args)
    
    @decorator_access_control
    def set(self, setter, setter_args, getter = None):
        """
        Set attribute to given value.
        
        Args:
            setter (str): Name of the library function to query according
                to the name mapping in the anc350_lib module.
            setter_args (tuple): List of arguments to pass to the specified
                setter. Any mutable argument (used by the library function
                to return values) is to be replaced with *None*.
            getter (str): Name of the library function that is the getter for
                the same attribute according to the name mapping in the
                anc350_lib module in order to verify that setting was successful.
        
        Returns:
            None
        """
        self.parent._set(setter, setter_args, getter)
    
    @decorator_access_control
    def call(self, func, func_args):
        """
        Call a library function.
        
        Args:
            func (str): Name of the library function to query according
                to the name mapping in the anc350_lib module.
            func_args (tuple): List of arguments to pass to the specified
                function. Any mutable argument (used by the library function
                to return values) is to be replaced with *None*.
        
        Returns:
            None
        """
        self.parent._call(func, func_args)
    
    @property
    def ac_in_enable(self):
        """
        Property for the status of the AC input of this axis. Only applicable for 
        dither axes.
        
        :getter: Gets the current AC status 
        :setter: Activates/deactivates AC input of this axis
        :type: bool
        """
        return self.get('positionerGetAcInEnable', (self.axis_number, None))[0].value

    @ac_in_enable.setter
    def ac_in_enable(self, state):
        self.set('positionerAcInEnable', (self.axis_number, bool(state)), getter = 'positionerGetAcInEnable')

    @property
    def amplitude(self):
        """
        Property for the driving amplitude in volts. In case of standstill of
        the actor this is the amplitude setpoint. In case of movement the
        amplitude set by amplitude control is determined.
        
        :getter: Gets the current amplitude
        :setter: Set the amplitude setpoint
        :type: float
        """
        return float(self.get('positionerGetAmplitude', (self.axis_number, None))[0].value) / 1000

    @amplitude.setter
    def amplitude(self, value):
        self.set('positionerAmplitude', (self.axis_number, int(1000 * value)), getter = 'positionerGetAmplitude')

    def amplitude_control(self, mode):
        """
        Property for the type of amplitude control. The amplitude is controlled by
        the positioner to hold the value constant determined by the selected
        type of amplitude control.
        
        :setter: Set the amplitude control mode
        :type: :class:`ANC350AmplitudeControlMode`
        """
        m = make_enum(ANC350AmplitudeControlMode, mode)
        self.set('positionerAmplitudeControl', (self.axis_number, m))

    amplitude_control = property(None, amplitude_control, None, amplitude_control.__doc__)

    @property
    def bandwidth_limit_enable(self):
        """
        Property for the status of the bandwidth limiter of this axis. Only 
        applicable for scanner axes.
        
        :getter: Get the current bandwidth limiter state
        :setter: Activates/deactivates the bandwidth limiter of this axis
        :type: bool
        """
        return self.get('positionerGetBandwidthLimitEnable', (self.axis_number, None))[0].value

    @bandwidth_limit_enable.setter
    def bandwidth_limit_enable(self, state):
        self.set('positionerBandwidthLimitEnable', (self.axis_number, bool(state)), getter = 'positionerGetBandwidthLimitEnable')

    @property
    def capacitance(self):
        """
        Property for the capacitance of the piezo addressed by this axis in nF.
        
        :getter: Get the current capacitance
        :type: int
        """
        return self.get('positionerCapMeasure', (self.axis_number, None))[0].value

    def clear_stop_detection(self, axis):
        """
        When sticky stop detection is enabled by setting ``stop_detection_sticky``
        to `True`, this clears the stop detection status.
        """
        self.call('positionerClearStopDetection', (axis, ))

    @property
    def dc_in_enable(self):
        """
        Property for the status of the DC input of this axis. Only applicable for 
        scanner/dither axes.
        
        :getter: Get the current DC input status
        :setter: Activates/deactivates DC input of this axis
        :type: bool
        """
        return self.get('positionerGetDcInEnable', (self.axis_number, None))[0].value

    @dc_in_enable.setter
    def dc_in_enable(self, state):
        self.set('positionerDcInEnable', (self.axis_number, bool(state)), getter = 'positionerGetDcInEnable')

    @property
    def dc_level(self):
        """
        Property for the actual DC level in volts of this axis.
        
        :getter: Get the current DC level
        :setter: Sets the DC level
        :type: float
        """
        return float(self.get('positionerGetDcLevel', (self.axis_number, None))[0].value) / 1000

    @dc_level.setter
    def dc_level(self, value):
        self.set('positionerDCLevel', (self.axis_number, int(1000 * value)), getter = 'positionerGetDCLevel')

    def external_step_backward_input(self, input_trigger):
        """
        Property for the external step trigger input for selected axis. A 
        trigger on this input results in a backwards single step.
        
        :setter: Sets the input trigger (0 disabled, 1-6 input trigger)
        :type: int
        """
        self.set('positionerExternalStepBkwInput', (self.axis_number, input_trigger))

    external_step_backward_input = property(None, external_step_backward_input, None, external_step_backward_input.__doc__)

    def external_step_forward_input(self, input_trigger):
        """
        Property for the external step trigger input for selected axis. A 
        trigger on this input results in a forward single step.
        
        :setter: Sets the input trigger (0 disabled, 1-6 input trigger)
        :type: int
        """
        self.set('positionerExternalStepFwdInput', (self.axis_number, input_trigger))

    external_step_forward_input = property(None, external_step_forward_input, None, external_step_forward_input.__doc__)

    def external_step_input_edge(self, edge):
        """
        Property for the edge sensitivity of external step trigger input for
        this axis.
        
        :setter: Sets the trigger edge sensitivity
        :type: :class:`ANC350TriggerEdge`
        """
        e = make_enum(ANC350TriggerEdge, edge)
        self.set('positionerExternalStepInputEdge', (self.axis_number, e))

    external_step_input_edge = property(None, external_step_input_edge, None, external_step_input_edge.__doc__)

    @property
    def frequency(self):
        """
        Property for the driving frequency in Hz of this axis
        
        :getter: Get the current driving frequency
        :setter: Set the driving frequency
        :type: int
        """
        return self.get('positionerGetFrequency', (self.axis_number, None))[0].value

    @frequency.setter
    def frequency(self, value):
        self.set('positionerFrequency', (self.axis_number, int(value)), getter = 'positionerGetFrequency')
        
    @property
    def int_enable(self):
        """
        Property for the status of the internal signal generation of this axis. 
        Only applicable for scanner/dither axes.
        
        :getter: Get the current signal generation status
        :setter: Activates/deactivates internal signal generation of this axis
        :type: bool
        """
        return self.get('positionerGetIntEnable', (self.axis_number, None))[0].value

    @int_enable.setter
    def int_enable(self, state):
        self.set('positionerIntEnable', (self.axis_number, bool(state)), getter = 'positionerGetIntEnable')

    def load(self, filename):
        """
        Loads a parameter file for actor configuration.
        
        Note: 
            This requires a pointer to a char datatype. Having no parameter
            file to test, I have no way of telling whether this will work,
            especially with the manual being as erroneous as it is. As such,
            use at your own (debugging) risk!
        """
        self.call('positionerLoad', (self.axis_number, filename))

    def move_absolute(self, position, rotcount = 0):
        """
        Starts approach to absolute target position. Previous movement will be
        stopped.
        
        Args:
            position (int): 
                Position units in 'units of actor' (generally nanometres).
            rotcount (int):
                Number of rotations in case of rotary actor 
        """
        self.call('positionerMoveAbsolute', (self.axis_number, int(position), int(rotcount)))
        
    def move_continuous(self, direction):
        """
        Starts continuous movement with set parameters for amplitude, speed 
        and amplitude control respectively.
        
        Args:
            direction (:class:`ANC350Direction`):
                Direction of the movement
        """
        d = make_enum(ANC350Direction, direction)
        self.call('positionerMoveContinuous', (self.axis_number, d))

    def move_reference(self):
        """
        Starts approach to reference position. Previous movement will be stopped.
        """
        self.call('positionerMoveReference', (self.axis_number, ))

    def move_relative(self, position, rotcount = 0):
        """
        Starts approach to relative target position. Previous movement will
        be stopped.
        
        Args:
            position (int): 
                Position units in 'units of actor' (generally nanometres).
            rotcount (int):
                Number of rotations in case of rotary actor 
        """
        self.call('positionerMoveRelative', (self.axis_number, int(position), int(rotcount)))

    def move_single_step(self, direction):
        """
        Starts a one-step positioning. Previous movement will be stopped. 
        
        Args:
            direction (:class:`ANC350Direction`):
                Direction of the movement
        """
        d = make_enum(ANC350Direction, direction)
        self.call('positionerMoveSingleStep', (self.axis_number, d))

    def output(self, state):
        """
        Property for enabling and disabling this axis
        
        :setter: Activates/deactivates this axis
        :type: bool
        """
        self.set('positionerSetOutput', (self.axis_number, bool(state)))
    
    output = property(None, output, None, output.__doc__)

    @property
    def position(self):
        """
        Property for the actual position of this axis in micrometer.
        
        :getter: Get the current position in 'units of actor' (generally
            nanometers)
        :type: float
        """
        return float(self.get('positionerGetPosition', (self.axis_number, None))[0].value) / 1000

    def quadrature_axis(self, quadrature_number):
        """
        Property to select this axis for use with trigger in/out pair. 
        
        :setter: Sets the number of the addressed quadrature unit (0-2).
        :type: int
        """
        self.call('positionerQuadratureAxis', (quadrature_number, self.axis_number))
        
    quadrature_axis = property(None, quadrature_axis, None, quadrature_axis.__doc__)

    @property
    def reference(self):
        """
        Property for the distance of the reference mark to the origin.
        
        :getter: Returns the reference position in the 'unit of the actor' 
            (generally nanometers) and a flag showing whether the indicator for the
            reference position is valid.
        :type: tuple
        """
        res = self.get('positionerGetReference', (self.axis_number, None, None))
        return res[0].value, bool(res[1].value)

    @property
    def reference_rot_count(self):
        """
        Property for the actual number of rotations for the reference position 
        in case of a rotary actor. 
        
        :getter: Gets the number of rotations
        :type: int
        """
        return self.get('positionerGetReferenceRotCount', (self.axis_number, None))[0].value

    def reset_position(self):
        """
        Sets the origin to the actual position
        """
        self.call('positionerResetPosition', (self.axis_number, ))

    @property
    def rot_count(self):
        """
        Property for the actual number of rotations in case of rotary actuator.
        
        :getter: Gets the number of rotations
        :type: int
        """
        return self.get('positionerGetRotCount', (self.axis_number, None))[0].value

    def single_circle_mode(self, state):
        """
        Property for single circle mode. In case of activated single circle mode
        the number of rotations are ignored and the shortest way to target
        position is used. Only relevant for rotary actors.
        
        :setter: Activates/deactivates single circle mode
        :type: bool
        """
        self.set('positionerSingleCircleMode', (self.axis_number, bool(state)))
    
    single_circle_mode = property(None, single_circle_mode, None, single_circle_mode.__doc__)

    @property
    def speed(self):
        """
        Property for the actor speed. In case of standstill of this actor this
        is the calculated speed resulting from amplitude setpoint, frequency, 
        and motor parameters. In case of movement this is measured speed.
        
        :getter: Gets speed in 'units of actor' (generally nanometers) per
            second
        :type: float
        """
        return float(self.get('positionerGetSpeed', (self.axis_number, None))[0].value) / 1000

    @property
    def status(self):
        """
        Property for the status of this axis. Resulting bitmask has the fields
        bit0 (moving), bit1 (stop detected), bit2 (sensor error), 
        bit3 (sensor disconnected) and can be split into individual values
        using :func:`ANC350.debitmask()`.
        
        :getter: Get the current status
        :type: int
        """
        return self.get('positionerGetStatus', (self.axis_number, None))[0].value

    @property
    def stepwidth(self):
        """
        Property for the step width. In case of standstill of the motor this is 
        the calculated step width resulting from amplitude setpoint, frequency, 
        and motor parameters. In case of movement this is measured step width.
        
        :getter: Get the current stepwidth in 'units of actor' (usually nanometers)
        :type: float
        """
        return float(self.get('positionerGetStepwidth', (self.axis_number, None))[0].value) / 1000

    def step_count(self, steps):
        """
        Property for the number of successive steps caused by external trigger or
        manual step request.
        
        :setter: Sets the number of steps to a value between 1 and 65535
        :type: int
        """
        self.set('positionerStepCount', (self.axis_number, steps))

    step_count = property(None, step_count, None, step_count.__doc__)

    def stop_approach(self):
        """
        Stops approaching target/relative/reference position. DC level of
        affected axis after stopping depends on setting by ``target_ground()``.
        """
        self.call('positionerStopApproach', (self.axis_number, ))

    def stop_detection(self, state):
        """
        Property for stop detection
        
        :setter: Switches stop detection on/off
        :type: bool
        """
        self.set('positionerStopDetection', (self.axis_number, bool(state)))

    stop_detection = property(None, stop_detection, None, stop_detection.__doc__)

    def stop_detection_sticky(self, state):
        """
        When this property is enabled, an active stop detection status remains
        active until cleared manually by ``clear_stop_detection()``.
        
        :setter: Switch sticky stop detection on/off
        :type: bool
        """
        self.set('positionerSetStopDetectionSticky', (self.axis_number, bool(state)))

    stop_detection_sticky = property(None, stop_detection_sticky, None, stop_detection_sticky.__doc__)

    def stop_moving(self):
        """
        Stops any positioning, DC level of affected axis is set to zero after 
        stopping.
        """
        self.call('positionerStopMoving', (self.axis_number, ))

    def target_ground(self, state):
        """
        When this property is enabled, actor voltage set to zero after
        closed-loop positioning finished.
        
        :setter: Switch target grounding on/off
        :type: bool
        """
        self.set('positionerSetTargetGround', (self.axis_number, bool(state)))

    target_ground = property(None, target_ground, None, target_ground.__doc__)

    def target_pos(self, value):
        """
        Sets target position for use with :func:`ANC350Qty.move_absolute_sync()`.

        :setter: If provided with a tuple of a float and an int, sets target
            position in 'units of actor' (generally nanometers) and number of
            rotations in case of rotary actor. If provided with only a float,
            sets number of rotations to zero.
        :type: float or tuple (float, int)
        """
        if type(value) is tuple or type(value) is list:
            if not len(value) == 2:
                raise ANC350IOError('Expected tuple of length 2 to assign to `target_pos`.')
            pos, rotcount = value
            self.set('positionerSetTargetPos', (self.axis_number, int(pos*1000), rotcount))
        else:
            pos = value
            self.set('positionerSetTargetPos', (self.axis_number, int(pos*1000), 0))
        
    target_pos = property(None, target_pos, None, target_pos.__doc__)

    def trigger_axis(self, trigger_number):
        """
        Selects this axis for the addressed trigger. 
        
        :setter: Set trigger number of this axis (0-5)
        :type: int
        """
        self.call('positionerTriggerAxis', (trigger_number, self.axis_number))

    trigger_axis = property(None, trigger_axis, None, trigger_axis.__doc__)

    def update_absolute(self, position):
        """
        Updates target position for a *running* approach. Function has lower
        performance impact on running approach compared to ``move_absolute()``.
        
        Args:
            position (int): Target position in 'unit of actor' (generally nanometres)
        """
        self.call('positionerUpdateAbsolute', (self.axis_number, int(position)))


class ANC350Qty(DeviceQty):
    """
    Class to communicate with ANC350 ensuring mutually exclusive access 
    to the device.
    
    Args:
        parent (ANC350):
            The parent ANC350 instance that the axis is derived from.
        prio (int):
            Priority level used for device access control. Higher numbers
            indicate higher priority with zero being the lowest possible
            priority. Calls with positive priority level are guaranteed
            to be executed, while calls with zero priority level may be
            omitted and return `None`, if the device is busy. Keyword
            argument only.
    """
    def __init__(self, parent, *, prio = 0):
        super().__init__(parent, prio = prio)
    
    @decorator_access_control
    def get(self, getter, getter_args):
        """
        Read current value of an attribute.
        
        Args:
            getter (str): Name of the library function to query according
                to the name mapping in the anc350_lib module.
            getter_args (tuple): List of arguments to pass to the specified
                getter. Any mutable argument (used by the library function
                to return values) is to be replaced with *None*.

        Returns:
            tuple: Values of the mutable argument in the same order as given in
                ``getter_args``.
        """
        return self.parent._get(getter, getter_args)
    
    @decorator_access_control
    def set(self, setter, setter_args, getter = None):
        """
        Set attribute to given value.
        
        Args:
            setter (str): Name of the library function to query according
                to the name mapping in the anc350_lib module.
            setter_args (tuple): List of arguments to pass to the specified
                setter. Any mutable argument (used by the library function
                to return values) is to be replaced with *None*.
            getter (str): Name of the library function that is the getter for
                the same attribute according to the name mapping in the
                anc350_lib module in order to verify that setting was successful.
        
        Returns:
            None
        """
        self.parent._set(setter, setter_args, getter)
    
    @decorator_access_control
    def call(self, func, func_args):
        """
        Call a library function.
        
        Args:
            func (str): Name of the library function to query according
                to the name mapping in the anc350_lib module.
            func_args (tuple): List of arguments to pass to the specified
                function. Any mutable argument (used by the library function
                to return values) is to be replaced with *None*.
        
        Returns:
            None
        """
        self.parent._call(func, func_args)
    
    def duty_cycle_enable(self, state):
        """
        Property do control the duty cycle mode.
        
        :setter: Enables/diables the duty cycle mode
        :type: bool
        """
        self.set('positionerDutyCycleEnable', (bool(state), ))

    duty_cycle_enable = property(None, duty_cycle_enable, None, duty_cycle_enable.__doc__)

    def duty_cycle_off_time(self, value):
        """
        Property to set the duty cycle off time.
        
        :setter: Sets the duty cycle off time
        :type: int
        """
        self.set('positionerDutyCycleOffTime', (value, ))

    duty_cycle_off_time = property(None, duty_cycle_off_time, None, duty_cycle_off_time.__doc__)

    def duty_cycle_period(self, value):
        """
        Property to set the duty cycle period.
        
        :setter: Sets the duty cycle period
        :type: int
        """
        self.set('positionerDutyCyclePeriod', (value, ))

    duty_cycle_period = property(None, duty_cycle_period, None, duty_cycle_period.__doc__)

    def hardware_id(self, hardware_id):
        """
        Property to set the hardware ID for the device (used to differentiate multiple 
        devices).
        
        :setter: Sets the hardware ID
        :type: int
        """
        self.set('positionerSetHardwareId', (hardware_id, ))
    
    hardware_id = property(None, hardware_id, None, hardware_id.__doc__)

    def move_absolute_sync(self, bitmask_of_axes):
        """
        Starts the synchronous approach to absolute target position for
        selected axis. Previous movement will be stopped. Parget position for
        each axis defined by :func:`ANC350Axis.target_pos()`.
        
        Args:
            bitmask_of_axes (int):
                A bitmask of axes that can be constructed with :func:`ANC350.bitmask()`.
        """
        self.call('positionerMoveAbsoluteSync', (bitmask_of_axes, ))

    def quadrature_input_period(self, quadrature_number, period):
        """
        Selects the stepsize the controller executes when detecting a step
        on its input AB-signal.
        
        Args:
            quadrature_number (int):
                The number of of the addressed quadrature unit (0-2).
            period (float) 
                Stepsize in the 'unit of actor'.
        """
        self.call('positionerQuadratureInputPeriod', (quadrature_number, int(period * 1000)))

    def quadrature_output_period(self, quadrature_number, period):
        """
        Selects the position difference which causes a step on the output
        AB-signal.
        
        Args:
            quadrature_number (int):
                The number of of the addressed quadrature unit (0-2).
            period (float) 
                Stepsize in the 'unit of actor'.
        """
        self.call('positionerQuadratureOutputPeriod', (quadrature_number, int(period * 1000)))

    def sensor_power_group_a(self, state):
        """
        Property for the power of sensor group A. Sensor group A contains
        either the sensors of axis 1-3 or 1-2 dependent on hardware of controller.
        
        :setter: Switches the power of sensor group A
        :type: bool
        """
        self.set('positionerSensorPowerGroupA', (bool(state), ))

    sensor_power_group_a = property(None, sensor_power_group_a, None, sensor_power_group_a.__doc__)

    def sensor_power_group_b(self, state):
        """
        Property for the power of sensor group B. Sensor group B contains
        either the sensors of axis 4-6 or 3 dependent on hardware of controller.
        
        :setter: Switches the power of sensor group B
        :type: bool
        """
        self.set('positionerSensorPowerGroupB', (bool(state), ))

    sensor_power_group_b = property(None, sensor_power_group_b, None, sensor_power_group_b.__doc__)

    def set_trigger(self, trigger_number, low, high):
        """
        Sets the trigger thresholds for the external trigger.
        
        Args:
            trigger_number (int): Number of addressed trigger (0-5)
            low (float): Lower trigger threshold in unit of actor
            high (float): Upper trigger threshold in unit of actor
        """
        self.call('positionerTrigger', (trigger_number, int(low * 1000), int(high * 1000)))

    def set_trigger_epsilon(self, trigger_number, epsilon):
        """
        Sets the hysteresis of the external trigger. 
        
        Args:
            trigger_number (int): Number of addressed trigger (0-5)
            epsilon (float): Hysteresis in units of actor
        """
        self.call('positionerTriggerEpsilon', (trigger_number, int(epsilon * 1000)))

    def set_trigger_polarity(self, trigger_number, polarity):
        """
        Sets the polarity of the external trigger. 
        
        Args:
            trigger_number (int): Number of addressed trigger (0-5)
            polarity (:class:`ANC350TriggerPolarity`): Trigger polarity
        """
        p = make_enum(ANC350TriggerPolarity, polarity)
        self.call('positionerTriggerPolarity', (trigger_number, p))

    def static_amplitude(self, value):
        """
        Property for output voltage for resistive sensors.
        
        :setter: Sets the output voltage in volts
        :type: int
        """
        self.set('positionerSingleCircleMode', (int(value), ))

    static_amplitude = property(None, static_amplitude, None, static_amplitude.__doc__)

    def trigger_mode_in(self, mode):
        """
        Property for the mode of the input trigger signals.
        
        :setter: Sets the mode of the input trigger signal
        :type: :class:`ANC350TriggerModeIn`
        """
        m = make_enum(ANC350TriggerModeIn, mode)
        self.set('positionerTriggerModeIn', (m, ))

    trigger_mode_in = property(None, trigger_mode_in, None, trigger_mode_in.__doc__)

    def trigger_mode_out(self, mode):
        """
        Property for the mode of the output trigger signals.
        
        :setter: Sets the mode of the output trigger signal
        :type: :class:`ANC350TriggerModeOut`
        """
        m = make_enum(ANC350TriggerModeOut, mode)
        self.set('positionerTriggerModeOut', (m, ))

    trigger_mode_out = property(None, trigger_mode_out, None, trigger_mode_out.__doc__)


class ANC350(Device):
    """
    Interface for ANC350 piezo controller. In itself, this class does not know
    anything about the axes that are connected to the controller. On
    instanciation, a mapping between axis numbers and strings naming the
    corresponding axes is read from the config passed to the constructor. For
    each axis name, a method with this name and signature ``axis_func(prio = 0)``
    is auto generated to provide easy access for all axes.

    Args:
        config (dictionary): Dictionary of key-value pairs that determines
            the configuration of the serial port connection. Entries ``axes``
            and ``dll_path`` are mandatory. The latter must be a dict with a mapping
            between strings describing the axis and the corresponding axis
            number. No other options are currently supported.
    """
    
    def __init__(self, config):
        # Try to get DLL file
        try:
            self._dll_path = config['dll_path']
        except KeyError as e:
            msg = "No DLL path specified for ANC350."
            raise Exception(msg).with_traceback(e.__traceback__)
        
        try:
            self._anc350_lib = anc350_lib.ANC350Lib(self._dll_path)
        except OSError as e:
            msg = 'DLL file "' + self._dll_path + '" not found.'
            raise Exception(msg).with_traceback(e.__traceback__)

        #Create PositionerInfo struct.
        self._positioner_info = anc350_lib.PositionerInfo()
        self._num_connected = self._anc350_lib.positionerCheck(ctypes.byref(self._positioner_info))
        if self._num_connected == 0:
            raise ANC350IOError("No positioner connected.")
        if self._num_connected > 1:
            raise ANC350IOError("More than one positioner connected.")
        
        try:
            axes = config['axes']
            if not type(axes) is dict:
                raise ANC350IOError("Expected 'dict' as axes specification, found '{0}'.".format(str(type(axes))))
                
            def make_axis_func(num):
                def axis_func(*, prio = 0):
                    return ANC350Axis(self, num, prio = prio)
                return axis_func
                
            for label, num in axes.items():
                if not type(label) is str:
                    raise ANC350IOError("'{0}' is not a legal axis label".format(label))
                try:
                    num = int(num)
                except TypeError as e:
                    msg = "'{0}' is not a legal axis number".format(num)
                    raise ANC350IOError(msg).with_traceback(e.__traceback__)
                
                setattr(self, label, make_axis_func(num))
        except KeyError as e:
            msg = "No axes specified for ANC350"
            raise Exception(msg).with_traceback(e.__traceback__)

        # Open connection to device
        super().__init__(ANC350IOError)

    def open(self):
        print('Opening connection to ANC 350... ', end = '', flush = True)

        self._handle = ctypes.c_int(0)
        try:
            # Connect to positioner. 0 means first device.
            self._anc350_lib.positionerConnect(0, ctypes.byref(self._handle))
        except Exception as e:
            msg = "Unable to connect to controller with id {0}".format(self._positioner_info.id)
            raise ANC350IOError(msg).with_traceback(e.__traceback__)

        super().open()
        print('Success.', flush = True)
        
    def close(self):
        """
        Closes connection to ANC 350
        """
        super().close()
        self._anc350_lib.positionerClose(self._handle)
    
    def qty(self, *, prio = 0):
        return ANC350Qty(self, prio = prio)
    
    def _get(self, getter, getter_args):
        """
        Very generic getter to read the value of an attribute. Checks if
        ``getter`` and ``getter_args`` conform to the API definitions
        before performing the actual call.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            getter (str): Name of the library function to query according
                to the name mapping in the anc350_lib module.
            getter_args (tuple): List of arguments to pass to the specified
                getter. Any mutable argument (used by the library function
                to return values) is to be replaced with *None*.

        Returns:
            tuple: Values of the mutable argument in the same order as given in
                ``getter_args``.
        """
        # Check if API exports requested getter method
        try:
            getter_func = getattr(self._anc350_lib, getter)
        except AttributeError as e:
            msg = "Unknown API method {0}.".format(getter)
            raise ANC350IOError(msg).with_traceback(e.__traceback__)
        # Try to access argtypes of getter
        try:
            getter_argtypes = getter_func.argtypes
        except AttributeError as e:
            # Raise error, if argtypes are not defined
            msg = "Cannot get argtypes for method {0}.".format(getter)
            raise ANC350IOError(msg).with_traceback(e.__traceback__)
        if not type(getter_argtypes) is list:
            raise ANC350IOError("Unsupported argtypes specification for method {0}".format(getter))
        # Check if argtype of first argument is ctypes.c_int, which is the
        # argtype for passing self._handle.
        if not getter_argtypes[0] is ctypes.c_int:
            raise ANC350IOError("Wrong argtypes provided for method {0}".format(getter))
        # Check if correct number of arguments has been provided
        if len(getter_argtypes) != len(getter_args) + 1:
            raise ANC350IOError("Wrong number of arguments provided for method {0}".format(getter))
        
        # Define a function to make a constructor from every argtype,
        # which is applied to the argument prior to calling the getter.
        def make_constructor(ctypes_type):
            # Check if the argtype is a pointer type.
            if ctypes_type.__class__.__name__ == 'PyCPointerType':
                # For pointer types, the constructor is just ctypes.byref
                return ctypes.byref
            else:
                # For all other types, the constructor is the corresponding
                # ctypes type.
                return ctypes_type
        
        # Define a function to prepare each argument from the corresponding
        # argtype and the provided value. To each of the prepared arguments
        # the correspondig constructor is to be applied.
        def make_argument(ctypes_type, value):
            # Check if the argtype is a pointer type
            if ctypes_type.__class__.__name__ == 'PyCPointerType':
                # Pointer types should be output arguments, so no value
                # should be supplied
                if not value is None:
                    raise ANC350IOError("Found value {0} for byref argument, where NoneType was expected".format(value))
                # Return an empty variable with the appropriate base type.
                return ctypes_type._type_()
            else:
                # For all other types just pass through the provided value.
                return value
            
        # Make a tuple of constructors for all arguments
        constructors = tuple(map(make_constructor, getter_argtypes))
        
        # Make a tuple of all arguments including self._handle
        arguments = tuple(map(make_argument, getter_argtypes, \
                              (self._handle.value, ) + getter_args))
        
        # Apply constructors to corresponding arguments, unpack resulting
        # tuple and pass to getter call.
        getter_func(*tuple(map(lambda f,x: f(x), constructors, arguments)))
        
        return tuple(a for c, a in zip(constructors, arguments) \
                     if c is ctypes.byref)
    
    def _set(self, setter, setter_args, getter = None):
        """
        Very generic setter to read the value of an attribute. Checks if
        ``setter`` and ``setter_args`` conform to the API definitions
        before performing the actual call.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            setter (str): Name of the library function to query according
                to the name mapping in the anc350_lib module.
            setter_args (tuple): List of arguments to pass to the specified
                setter. Any mutable argument (used by the library function
                to return values) is to be replaced with *None*.
            getter (str): Name of the library function that is the getter for
                the same attribute according to the name mapping in the
                anc350_lib module in order to verify that setting was successful.
                No checking is performed if this is set to *None*.
        
        Returns:
            None
        """
        # Check if API exports requested setter method
        try:
            setter_func = getattr(self._anc350_lib, setter)
        except AttributeError as e:
            msg = "Unknown API method {0}.".format(setter)
            raise ANC350IOError(msg).with_traceback(e.__traceback__)
        # Try to access argtypes of setter
        try:
            setter_argtypes = setter_func.argtypes
        except AttributeError as e:
            # Raise error, if argtypes are not defined
            msg = "Cannot get argtypes for method {0}.".format(setter)
            raise ANC350IOError(msg).with_traceback(e.__traceback__)
        if not type(setter_argtypes) is list:
            raise ANC350IOError("Unsupported argtypes specification for method {0}".format(setter))
        # Check if argtype of first argument is ctypes.c_int, which is the
        # argtype for passing self._handle.
        if not setter_argtypes[0] is ctypes.c_int:
            raise ANC350IOError("Wrong argtypes provided for method {0}".format(setter))
        # Check if correct number of arguments has been provided
        if len(setter_argtypes) != len(setter_args) + 1:
            raise ANC350IOError("Wrong number of arguments provided for method {0}".format(setter))
        
        if not getter is None:
            # Check if API exports requested getter method
            try:
                getter_func = getattr(self._anc350_lib, getter)
            except AttributeError as e:
                msg = "Unknown API method {0}.".format(getter)
                raise ANC350IOError(msg).with_traceback(e.__traceback__)
            # Try to access argtypes of getter
            try:
                getter_argtypes = getter_func.argtypes
            except AttributeError as e:
                # Raise error, if argtypes are not defined
                msg = "Cannot get argtypes for method {0}.".format(getter)
                raise ANC350IOError(msg).with_traceback(e.__traceback__)
            if not type(getter_argtypes) is list:
                raise ANC350IOError("Unsupported argtypes specification for method {0}".format(getter))
            # Check if argtype of first argument is ctypes.c_int, which is the
            # argtype for passing self._handle.
            if not getter_argtypes[0] is ctypes.c_int:
                raise ANC350IOError("Wrong argtypes provided for method {0}".format(getter))

            # Check if argtypes of getter and setter are compatible
            for i in range(len(getter_argtypes)):
                if getter_argtypes[i].__class__.__name__ == 'PyCPointerType':
                    if not getter_argtypes[i]._type_ is setter_argtypes[i]:
                        raise ANC350IOError("Incompatible argtypes provided for methods {0} and {1}".format(getter, setter))
                else:
                    if not getter_argtypes[i] is setter_argtypes[i]:
                        raise ANC350IOError("Incompatible argtypes provided for methods {0} and {1}".format(getter, setter))
        
        # Define a function to make a constructor from every argtype,
        # which is applied to the argument prior to calling the setter.
        def make_constructor(ctypes_type):
            # Check if the  argtype is a pointer type.
            if ctypes_type.__class__.__name__ == 'PyCPointerType':
                # For pointer types, the constructor is just ctypes.byref
                return ctypes.byref
            else:
                # For all other types, the constructor is the corresponding
                # ctypes type.
                return ctypes_type
        
        # Define a function to prepare each argument from the corresponding
        # argtype and the provided value. To each of the prepared arguments
        # the correspondig constructor is to be applied.
        def make_argument(ctypes_type, value):
            # Check if the argtype is a pointer type
            if ctypes_type.__class__.__name__ == 'PyCPointerType':
                # Make an instance of the required ctypes type.
                return ctypes_type._type_(value)
            else:
                # For all other types just pass through the provided value.
                return value
            
        # Make a tuple of constructors for all arguments
        constructors = tuple(map(make_constructor, setter_argtypes))
        
        # Make a tuple of all arguments including self._handle
        arguments = tuple(map(make_argument, setter_argtypes, \
                              (self._handle.value, ) + setter_args))
        
        # Apply constructors to corresponding arguments, unpack resulting
        # tuple and pass to setter call.
        setter_func(*tuple(map(lambda f,x: f(x), constructors, arguments)))
        
        # Check set value, if also a getter is provided:
        if not getter is None:
            # Define function to derive getter argument from setter argument.
            def derive_argument(ctypes_type, value):
                # Check if the argtype is a pointer type
                if ctypes_type.__class__.__name__ == 'PyCPointerType':
                    # Return an empty variable with the appropriate base type.
                    return ctypes_type._type_()
                else:
                    # For all other types just pass through the provided value.
                    return value
            
            # Make a tuple of constructors for all arguments
            constructors = tuple(map(make_constructor, getter_argtypes))
            
            # Make a tuple of all arguments including self._handle
            arguments = tuple(map(derive_argument, getter_argtypes, \
                                  (self._handle.value, ) + setter_args))
                                  
            # Apply constructors to corresponding arguments, unpack resulting
            # tuple and pass to getter call.
            getter_func(*tuple(map(lambda f,x: f(x), constructors, arguments)))
            
            # Check all byref arguments, if they have been set successfully.
            for i in range(len(constructors)):
                # Found a byref argument?
                if constructors[i] is ctypes.byref:
                    # Try to get return value
                    try:
                        res = arguments[i].value
                    except AttributeError as e:
                        msg = "Could not validate value set by method {0}".format(setter)
                        raise ANC350IOError(msg).with_traceback(e.__traceback__)
                    # Check if value has been set.
                    if not res == setter_args[i-1]:
                        raise ANC350IOError("Could not set value using method {0}".format(setter))
    
    def _call(self, func, func_args):
        """
        Very generic method to call a library function. Checks if
        ``func`` and ``func_args`` conform to the API definitions
        before performing the actual call.
        
        Note:
            This function is **not** decorated to ensure mutual exclusive
            access to the device. It should not be used for external function
            calls.

        Args:
            func (str): Name of the library function to query according
                to the name mapping in the anc350_lib module.
            func_args (tuple): List of arguments to pass to the specified
                function. Any mutable argument (used by the library function
                to return values) is to be replaced with *None*.
        
        Returns:
            None
        """
        self._set(func, func_args, None)
    
    def bitmask(input_array):
        """
        Takes an array or string and converts to integer bitmask; 
        reads from left to right e.g. 0100 = 2 not 4
        """
        total = 0
        for i in range(len(input_array)):
            if int(input_array[i]) != 0 and int(input_array[i])!=1:
                raise Exception('nonbinary value in bitmask, panic!')
            else: 
                total += int(input_array[i])*(2**(i))
        return total
    
    def debitmask(input_int,num_bits = False):
        """
        Takes a bitmask and returns a list of which bits are switched; 
        reads from left to right e.g. 2 = [0, 1] not [1, 0]
        """
        if num_bits == False and input_int>0:
            num_bits = int(math.ceil(math.log(input_int+1,2)))
        elif input_int == 0:
            return [0]
    
        result_array = [0]*num_bits
        for i in reversed(range(num_bits)):
            if input_int - 2**i >= 0:
                result_array[i] = 1
                input_int -= 2**i
        return result_array

    def __enter__(self):
        if self.closed:
            self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
    
    def __del__(self):
        self.close()