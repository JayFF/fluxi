# -*- coding: utf-8 -*-
"""
Base class for device interaction.
"""

import functools
import queue
import threading
import time
import weakref

def make_enum(enum_class, value):
    """
    Function to cast a value into a enumeration member instance. Raises
    ``ValueError`` if a conversion is not possible
    
    Args:
        enum_class (type):
            Enumeration class, which is the type of the desired result
        value:
            Value to typecast into a enumeration memeber instance. Can either
            be the member name, the member value or already an instance of
            the enumeration class ``enum_type``.
    """
    # Check if value is already a enumeration member
    if isinstance(value, enum_class):
        return value

    # Check if value is the name of a enumeration member
    try:
        return enum_class[value]
    except KeyError:
        pass
    
    # Check if value is the value of a enumeration member
    try:
        return enum_class(value)
    except ValueError:
        pass
    
    # Raise an exception, if nothing has worked so far:
    raise ValueError('Invalid value for {0}: {1}'.format(enum_class, value))

class DeviceError(Exception):
    """
    Device error.
    """
    pass

class DeviceQueueItem():
    """
    Data type for item in sorted queue ``DeviceQueue``.
    
    Args:
        data:
            Actual data to be submitted to the queue. Needs to support
            comparison operators. Sorting is performed by applying lexical
            ordering to the tuple ``(data, index)``.
        index (int):
            Unique index for identification of the submitted item. It is
            advised to use the return value of the method ``DeviceQueue.put()``
            for this purpose.
    """
    def __init__(self, data, index):
        self._data = data
        self._index = index
    
    def __repr__(self):
        return str((self._data, self._index))
    
    def __str__(self):
        return self.__repr__()
        
    def __hash__(self):
        return self._index
    
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self._data, self._index) == (other._data, other._index)
        else:
            return NotImplemented
    
    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return (self._data, self._index) != (other._data, other._index)
        else:
            return NotImplemented
    
    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return (self._data, self._index) < (other._data, other._index)
        else:
            return NotImplemented
    
    def __gt__(self, other):
        if isinstance(other, self.__class__):
            return (self._data, self._index) > (other._data, other._index)
        else:
            return NotImplemented
    
    def __le__(self, other):
        if isinstance(other, self.__class__):
            return (self._data, self._index) <= (other._data, other._index)
        else:
            return NotImplemented
    
    def __ge__(self, other):
        if isinstance(other, self.__class__):
            return (self._data, self._index) >= (other._data, other._index)
        else:
            return NotImplemented
    
    @property
    def data(self):
        """
        Property to access submitted data.
        
        :getter: Get submitted data
        """
        return self._data
    
    @property
    def index(self):
        """
        Property to access unique index.
        
        :getter: Get unique index
        :type: int
        """
        return self._index
        

class DeviceQueue():
    """
    Sorted queue for priority-based device access. This class is a simple
    wrapper around a ``queue.PriorityQueue`` and a ``threading.Condition``
    with an underlying primitive lock.
    
    Args:
        maxsize (int):
            Integer that sets the upperbound limit on the number of items that
            can be placed in the queue. Insertion will block once this size has
            been reached, until queue items are consumed. If maxsize is less
            than or equal to zero, the queue size is infinite. Keyword argument
            only.
    
    Attributes:
        _index (int):
            Index of last submitted item. For each item submitted to the
            queue, this index increases by 1.
        _closed (bool):
            Boolean to indicate whether the queue is closed.
    """
    def __init__(self, *, maxsize = 0):
        self._queue = queue.PriorityQueue(maxsize)
        self._condition = threading.Condition(threading.Lock())
        self._index = 0
        self._closed = False
        self._task_pending = False
    
    @property
    def maxsize(self):
        """
        Property to access the upperbound limit on the number of items that
        can be placed in the queue. Insertion will block once this size has
        been reached, until queue items are consumed. If maxsize is less
        than or equal to zero, the queue size is infinite. Keyword argument
        only.
        
        :getter: Get upperbound limit on the number of items in the queue
        :setter: Set upperbound limit on the number of items in the queue
        :type: int
        """
        with self._queue.mutex:
            return self._queue.maxsize
    
    @maxsize.setter
    def maxsize(self, value):
        with self._queue.mutex:
            self._queue.maxsize = value
    
    @property
    def index(self):
        """
        Property to access index of last submitted item.
        
        :getter: Get index of last submitted item
        :type: int
        """
        return self._index
    
    @property
    def closed(self):
        """
        Property to tell whether queue is closed or not.
        
        :getter: Returns `True` if queue is closed and `False` otherwise.
        :type: bool
        """
        return self._closed
    
    @property
    def task_pending(self):
        """
        Property to tell whether there is a pending task the queue is waiting
        for.
        
        :getter: Returns `True` if there is a pending task and `False` otherwise.
        :type: bool
        """
        return self._task_pending
    
    def close(self):
        """
        Close the queue to block all further submissions.
        """
        self._closed = True
    
    def acquire(self, *, block = True, timeout = None):
        """
        Acquire the underlying primitive lock of the condition variable,
        blocking or non-blocking.
        
        Args:
            block (bool):
                When invoked with the this argument set to `True` (the default),
                block until the lock is unlocked, then set it to locked and
                return `True`. When invoked with this argument set to `False`,
                do not block. If a call with this argument set to `True` would
                block, return `False` immediately; otherwise, set the lock to
                locked and return `True`. Keyword argument only.
            timeout (float or None):
                When set to a positive value, block for at most the number of
                seconds specified by this argument and as long as the lock
                cannot be acquired. Return `True` if wait is successful and
                `False` otherwise. `None` specifies an unbounded wait. It is
                forbidden to specify a timeout when `block` is `False`.
                Keyword argument only.
        
        Returns:
            bool: `True` if the lock is acquired successfully, `False` if not
                (for example if the timeout expired).
        """
        if not timeout is None and timeout < 0:
            raise ValueError("'timeout' must be a non-negative number")
        if not block and not timeout is None:
            raise ValueError("can't specify a timeout for a non-blocking call")
        if timeout is None:
            return self._condition.acquire(blocking = block, timeout = -1)
        else:
            return self._condition.acquire(blocking = block, timeout = timeout)
    
    def release(self):
        """
        Release the underlying primitive lock of the condition variable. This
        can be called from any thread, not only the thread which has acquired
        the lock. When the lock is locked, reset it to unlocked, and return.
        If any other threads are blocked waiting for the lock to become
        unlocked, allow exactly one of them to proceed. When invoked on an
        unlocked lock, a ``RuntimeError`` is raised.
        
        Returns:
            None
        """
        return self._condition.release()
    
    def wait(self, *, timeout = None):
        """
        Wait until notified or until a timeout occurs. If the calling thread 
        has not acquired the underlying primitive lock of the condition variable
        when this method is called, a ``RuntimeError`` is raised.

        This method releases the underlying lock, and then blocks until it is
        awakened by a ``notify()`` or ``notify_all()`` call in another thread,
        or until the optional timeout occurs. Once awakened or timed out, it
        re-acquires the lock and returns.

        Args:
            timeout (float or None):
                When set to a positive value, block for at most the number of
                seconds specified by this argument and as long as no free slot
                is available. Return `True` if wait is successful and
                `False` otherwise. `None` specifies an unbounded wait.
                Keyword argument only.

        Returns:
            bool:
                The return value is `True` unless a given timeout expired, in
                which case it is `False`.
        """
        return self._condition.wait(timeout = timeout)
    
    def wait_for(self, predicate, *, timeout = None):
        """
        Wait until a condition evaluates to True. This utility method may call
        ``wait()`` repeatedly until the predicate is satisfied, or until a
        timeout occurs. The return value is the last return value of the
        predicate and will evaluate to `False` if the method timed out.
        Ignoring the timeout feature, calling this method is roughly equivalent
        to writing::
        
            while not predicate():
                cv.wait()
        
        Therefore, the same rules apply as with ``wait()``: The underlying
        primitive lock of the condition variable must be held when called and
        is re-acquired on return. The predicate is evaluated with the lock held.

        Args:
            predicate (callable):
                The result of ``predicate()`` will be interpreted as a boolean
                value.
            timeout (float or None):
                When set to a positive value, block for at most the number of
                seconds specified by this argument and as long as no free slot
                is available. Return `True` if wait is successful and
                `False` otherwise. `None` specifies an unbounded wait.
                Keyword argument only.
        """
        return self._condition.wait_for(predicate, timeout = timeout)
    
    def notify(self, *, n = 1):
        """
        By default, wake up one thread waiting on the condition variable, if
        any. If the calling thread has not acquired the underlying primitive
        lock when this method is called, a ``RuntimeError`` is raised.
        
        Note:
            An awakened thread does not actually return from its ``wait()``
            call until it can reacquire the lock. Since ``notify()`` does not
            release the lock, its caller should.
        
        Args:
            n (int):
                This method wakes up at most n of the threads waiting for the
                condition variable; it is a no-op if no threads are waiting.
                The current implementation wakes up exactly n threads, if at
                least n threads are waiting. However, it’s not safe to rely
                on this behavior. A future, optimized implementation may
                occasionally wake up more than n threads.
        """
        return self._condition.notify(n = n)
    
    def notify_all(self):
        """
        Wake up all threads waiting on the condition variable. This method
        acts like ``notify()``, but wakes up all waiting threads instead of
        one. If the calling thread has not acquired the underlying primitive 
        lock when this method is called, a ``RuntimeError`` is raised.
        """
        return self._condition.notify_all()
    
    @property
    def locked(self):
        """
        `Property` that returns the status of the underlying primitive lock of
        the condition variable.
        
        :getter: `True` if the lock has been acquired by some thread, `False`
            if not.
        :type: bool
        """
        return self._condition._lock.locked()

    @property
    def empty(self):
        """
        `Property` that is `True` if the queue is empty, `False` otherwise. If
        `empty` is `True` it doesn't guarantee that a subsequent call to
        ``put()`` will not block. Similarly, if `empty` is `False` it doesn't
        guarantee that a subsequent call to ``get()`` will not block.
        
        :getter: `True` if the queue is empty, `False` otherwise
        :type: bool
        """
        return self._queue.empty()
    
    @property
    def full(self):
        """
        `Property` that is  `True` if the queue is full, `False` otherwise. If
        `full` is `True` it doesn't guarantee that a subsequent call to
        ``get()`` will not block. Similarly, if `full` is `False` it doesn't
        guarantee that a subsequent call to ``put()`` will not block.
        
        :getter: `True` if the queue is full, `False` otherwise
        :type: bool
        """
        return self._queue.full()
    
    @property
    def qsize(self):
        """
        `Property` for approximate size of the queue. Note, ``qsize() > 0``
        doesn't guarantee that a subsequent ``get()`` will not block, nor will
        ``qsize() < maxsize`` guarantee that ``put()`` will not block.
        
        :getter: Get approximate size of the queue.
        :type: int
        """
        return self._queue.qsize()
    
    def put(self, data, *, block = True, timeout = None):
        """
        Put item into the queue.
        
        Args:
            data: Data to be put into queue. Needs to support comparison
                operators.
            block (bool):
                When invoked with the this argument set to `True` (the default),
                block until the a free slot is available, then put to the queue
                and return `True`. When invoked with this argument set to
                `False`, do not block. If a call with this argument set to
                `True` would block, return `False` immediately; otherwise, put
                to the queue and return `True`. Keyword argument only.
            timeout (float or None):
                When set to a positive value, block for at most the number of
                seconds specified by this argument and as long as no free slot
                is available. Return `True` if wait is successful and
                `False` otherwise. `None` specifies an unbounded wait. It is
                forbidden to specify a timeout when `block` is `False`.
                Keyword argument only.
        
        Returns:
            int or None:
                Index of submitted item, if put is successful. None if put is
                not successful, for example if the timeout expired or the queue
                is closed.
        """
        # Return None if queue is closed
        if self._closed:
            return None
        # Try to submit to queue if not
        if not timeout is None and timeout < 0:
            raise ValueError("'timeout' must be a non-negative number")
        if not block and not timeout is None:
            raise ValueError("can't specify a timeout for a non-blocking call")
        try:
            # Build DeviceQueueItem
            index = self._index
            item = DeviceQueueItem(data, index)
            # Try to submit
            self._queue.put(item, block = block, timeout = timeout)
            self._index += 1
            return index
        except queue.Full:
            # Return None if queue is full
            return None

    def peek(self):
        """
        Returns first element in queue, whithout actually getting it and
        removing it from the queue. Returns `None` if the queue is empty.
        """
        with self._queue.mutex:
            if len(self._queue.queue) > 0:
                return self._queue.queue[0]
            else:
                return None
    
    def get(self, *, block = True, timeout = None):
        """
        Remove and return an item from the queue. Calling this method marks
        the queue as waiting for the completion for the task corresponding to
        the gotten item by setting ``task_pending`` to `True`. To make this 
        method thread-safe, it should be called with the underlying primitive
        lock of the condition held.
    
        Args:
            block (bool):
                When invoked with the this argument set to `True`, block until an
                item is available, then return and remove the first item from the
                queue. When invoked with this argument set to `False`, do not
                block. If a call with this argument set to `True` would block,
                raise the ``Empty`` exception. Keyword argument only.
            timeout (float or None):
                When set to a positive value, block for at most the number of
                seconds specified by this argument and as long as no item
                is available. `None` specifies an unbounded wait. It is
                forbidden to specify a timeout when `block` is `False`.
                Keyword argument only.
        
        Returns:
            First item from the queue.
        """
        if not timeout is None and timeout < 0:
            raise ValueError("'timeout' must be a non-negative number")
        if not block and not timeout is None:
            raise ValueError("can't specify a timeout for a non-blocking call")
        
        if self._task_pending:
            raise DeviceError("Cannot get item while a task is still pending.")
        else:
            self._task_pending = True
            return self._queue.get(block = block, timeout = timeout)
    
    def task_done(self):
        """
        Indicate that a formerly enqueued task is complete. Used by queue
        consumer threads. For each ``get()`` used to fetch a task, a subsequent
        call to ``task_done()`` tells the queue that the processing on the task
        is complete and sets ``task_pending`` to `False`. To make this 
        method thread-safe, it should be called with the underlying primitive
        lock of the condition held.
    
        If a ``join()`` is currently blocking, it will resume when all items
        have been processed (meaning that a ``task_done()`` call was received
        for every item that had been ``put()`` into the queue).
    
        Raises a ``ValueError`` if called more times than there were items
        placed in the queue.
        """
        if not self._task_pending:
            raise DeviceError("Cannot mark task as done with no task pending.")
        else:
            self._task_pending = False
            return self._queue.task_done()
    
    @property
    def unfinished_tasks(self):
        """
        `Property` for approximate number of unfinished tasks in queue. Note
        that ``unfinished_tasks == 0`` doesn't guarantee that a subsequent call
        to ``join()`` will not block.
        
        :getter: Get approximate number of unfinished tasks.
        :type: int
        """
        with self._queue.mutex:
            return self._queue.unfinished_tasks
        
    def join(self):
        """
        Blocks until all items in the queue have been gotten and processed.
        The count of unfinished tasks goes up whenever an item is added to the
        queue. The count goes down whenever a consumer thread calls ``task_done()``
        to indicate that the item was retrieved and all work on it is complete.
        When the count of unfinished tasks drops to zero, ``join()`` unblocks.
        """
        return self._queue.join()
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        return False
    

def decorator_access_control(func):
    """
    Decorator to provice access control to devices. All calls to the device
    are passed through the corresponding ``DeviceQueue`` and sorted according
    to their priority level. Concurring calls are suspended untill all
    calls with higher priority have completed. Returns `None` if the queue
    is closed. Equally, returns `None` if the priority of a call to the device
    is zero and the queue is not empty.
    """
    @functools.wraps(func)
    def access_control(self, *args, **kwargs):
        # Raise exception if queue is closed
        with self.parent.queue:
            if self.parent.queue.closed:
                raise self.parent._error_class("Device connection closed.")
        # Return None if priority is zero and queue is not empty
        if self.sort_key == self.null_key and not self.parent.queue.empty:
            return None
        # Proceed otherwise
        with self.parent.queue:
            # Try to submit to queue. If this doesn't work, return None or
            # raise exception depeinding on sort key.
            index = self.parent.queue.put(self.sort_key)
            if index is None:
                if self.sort_key == self.null_key:
                    return None
                else:
                    raise self.parent._error_class("Couldn't submit to device queue.")
                
            # Predicate to test, whether the submitted item is the first
            # in the queue.
            def predicate():
                first = self.parent.queue.peek()
                if first is None:
                    raise self.parent._error_class("Internal DeviceQueue error. An item has been lost.")
                else:
                    # Return true if and only if the submitted item is the
                    # first in the queue AND there are no pending tasks.
                    return first.index == index and not self.parent.queue.task_pending

            self.parent.queue.wait_for(predicate)
            
            # Get the submitted item.
            self.parent.queue.get()

        try:
            # Execute device call, as soon as submitted item is the first in the
            # queue and there are no more pending tasks. This can be done with 
            # the condition variable released, due to the explicite check for
            # pending tasks.
            result = func(self, *args, **kwargs)
        finally:
            with self.parent.queue:
                # Mark the task as done and notify other waiting tasks.
                self.parent.queue.task_done()
                self.parent.queue.notify_all()
        return result
    
    return access_control


class DeviceQty:
    """
    Base class for controlled device access. To implement controlled access for
    a specific device, derive a sub-class from this class and pass the type of
    the sub-class to the constructor of class ``Device``. Any methods, which
    perform device access, should be protected with the decorator
    ``decorator_access_control()``.
    
    Sub-classes should override the methods ``get()`` and ``set()``. Also, the
    implementations of ``sort_key()`` and ``null_key()`` can be altered in
    order to fine-tune the behaviour of the associated ``DeviceQueue``.
    
    Attributes:
        _null_key (int):
            Class variable to store the sort key that is used to indicate
            priority level zero. By default, this is an integer with value
            zero.
    
    Args:
        parent (Device): Parent ``Device`` object.
        prio (int):
            Priority level used for device access control. Higher numbers
            indicate higher priority with zero being the lowest possible
            priority. Calls with positive priority level are guaranteed
            to be executed, while calls with zero priority level may be
            omitted and return `None`, if the device is busy. Keyword
            argument only.
    """
    _null_key = 0
    
    def __init__(self, parent, *, prio = 0):
        self._parent = weakref.ref(parent)
        if prio < 0:
            raise self.parent._error_class('Negative priority level {0} given. Priority levels must be non-negative.'.format(prio))
        else:
            self._prio = prio
    
    @property
    def parent(self):
        """
        Property to get parent ``Device`` object.
        
        :getter: Gets parent ``Device`` object.
        :type: Device
        """
        return self._parent()
    
    @property
    def prio(self):
        """
        Property to get priority level.
        
        :getter: Gets priority level.
        :type: int
        """
        return self._prio
    
    @property
    def sort_key(self):
        """
        Property to get sort key. By default, the sort key is the negative of
        the priority level such that highest priority levels are sorted to
        the top.
        
        :getter: Gets sort key.
        :type: int
        """
        return -self._prio
    
    @property
    def null_key(self):
        """
        Property to get the sort key which is used to indicate priority level
        zero. By default, this is an integer with value zero.
        
        :getter: Gets null key.
        :type: int
        """
        return type(self)._null_key

    
class Device:
    """
    Nase class for device interaction. To implement interaction with a specific
    device, derive a sub-class from this class. Sub-classes should override the
    methods ``_get()``, ``_set()``,  ``open()`` and ``close()``.
    
    Attributes:
        _queue (DeviceQueue):
            Sorted queue for priority based device access.
    
    Args:
        error_class (type):
            Type of the class to be used to raise exceptions. Default is
            class ``DeviceError``.
    """
    def __init__(self, error_class = DeviceError):
        self._error_class = error_class
        self._queue = DeviceQueue()
        self.register_wait_func(time.sleep)
        self.open()
        
    @property
    def queue(self):
        """
        Property to return queue used for priority based device access.
        
        :getter: Gets priority queue.
        :type: DeviceQueue
        """
        return self._queue
    
    @property
    def closed(self):
        """
        Property to tell whether connection to device is closed or not.
        
        :getter: Returns `True` if connection to device is closed and `False`
            otherwise.
        :type: bool
        """
        return self._closed
    
    def wait_func(self, seconds):
        """
        Function to be called whenever the termination of some device-related
        process has to be waited for. The internal mechanism of this method
        can be changed using `register_wait_func()`. This is useful, if a
        waiting function is desired, which keeps a GUI responsive, e.g. by
        periodic calls to ``processEvents()``. The default waiting function
        is ``time.sleep()``.
        
        Args:
            seconds (float): Number of seconds to be waited.
            
        Returns:
            None
        """
        self._wait_func(seconds)
    
    def register_wait_func(self, func):
        """
        Registers a function, which is called whenever the termination of
        some device-related process has to be waited for. This is useful, if
        a waiting function is desired, which keeps a GUI responsive, e.g. by
        periodic calls to ``processEvents()``. The default waiting function
        is ``time.sleep()``.
        
        Args:
            func (function): Function to be registered as waiting function.
                The function ``func`` has to accept exactly one positional
                argument ``seconds``, which is the number of seconds to wait.
        
        Returns:
            None
        """
        self._wait_func = func
    
    def reset_wait_func(self):
        """
        Resets the waiting function to ``time.sleep()``.
        
        Returns:
            None
        """
        self.register_wait_func(time.sleep)
    
    def open(self, *args, **kwargs):
        """
        Method to open the connection to the device. Should be overridden in
        all sub-classes.
        """
        self._closed = False
    
    def close(self, *args, **kwargs):
        """
        Method to close the connection to the device. Should be overridden in
        all sub-classes.
        """
        if not self._closed:
            self._closed = True
            with self._queue:
                self._queue.close()
            self._queue.join()