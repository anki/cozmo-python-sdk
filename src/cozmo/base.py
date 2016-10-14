# Copyright (c) 2016 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__all__ = []

import threading

import asyncio
import concurrent.futures
import functools
import inspect
import traceback
import types


class _MetaBase(type):
    '''Metaclass for all Cozmo package classes.

    Ensures that all *_factory class attributes are wrapped into a _Factory
    descriptor to automatically support synchronous operation.
    '''

    def __new__(mcs, name, bases, attrs, **kw):
        for k, v in attrs.items():
            if k.endswith('_factory'):
                # TODO: check type here too
                attrs[k] = _Factory(v)
        return super().__new__(mcs, name, bases, attrs, **kw)

    def __setattr__(cls, name, val):
        if name.endswith('_factory'):
            cls.__dict__[name].__set__(cls, val)
        else:
            super().__setattr__(name, val)


class Base(metaclass=_MetaBase):
    '''Base class for Cozmo package objects.

    *_factory attributes are automatically wrapped into a _Factory descriptor to
    support synchronous operation.
    '''

    # used by SyncFatory
    _sync_thread_id = None
    _sync_abort_future = None

    def __init__(self, _sync_thread_id=None, _sync_abort_future=None, **kw):
        # machinery for SyncFactory
        if _sync_abort_future is not None:
            self._sync_thread_id = threading.get_ident()
        else:
            self._sync_thread_id = _sync_thread_id
        self._sync_abort_future = _sync_abort_future
        super().__init__(**kw)

    @property
    def loop(self):
        ''':class:`asyncio.BaseEventLoop`:  loop instance that this object is registered with.'''
        return getattr(self, '_loop', None)



class _Factory:
    '''Descriptor to wraps an object factory method.

    If the factory is called while the program is running in synchronous mode
    then the objects returned by the factory will be wrapped by a _SyncProxy
    object, which translates asynchronous responses to synchronous ones
    when made outside of the thread the top level object's event loop is running on.
    '''

    def __init__(self, factory):
        self._wrapped_factory = factory

    def __get__(self, ins, owner):
        sync_thread_id = getattr(ins, '_sync_thread_id', None)
        loop = getattr(ins, '_loop', None)
        if sync_thread_id:
            # Object instance is running in sync mode
            return _SyncFactory(self._wrapped_factory, loop, sync_thread_id, ins._sync_abort_future)
        # Pass through to the factory.  Set loop here as a convenience as all
        # Cozmo objects require it by virtue of inheriting from event.Dispatcher
        return functools.partial(self._wrapped_factory, loop=loop)

    def __set__(self, ins, val):
        self._wrapped_factory = val


def _SyncFactory(f, loop, thread_id, sync_abort_future):
    '''Instantiates a class by calling a factory function and then wrapping it with _SyncProxy'''
    def factory(*a, **kw):
        kw['_sync_thread_id'] = thread_id
        kw['_sync_abort_future'] = sync_abort_future
        if 'loop' not in kw:
            kw['loop'] = loop
        obj = f(*a, **kw)
        return  _mkproxy(obj)
    return factory


def _mkpt(cls, name):
    # create a passthru function
    f = getattr(cls, name)
    @functools.wraps(f)
    def pt(self, *a, **kw):
        wrap = self.__wrapped__
        f = object.__getattribute__(wrap, name)
        return f(*a, **kw)
    return pt


class _SyncProxy:
    '''Wraps cozmo objects to provide synchronous access when required.

    Each method call and attribute access is passed through to the wrapped object.

    If the caller is operating in a different thread to the callee (for example, the
    caller is operating outside of the context of the event loop), then any
    calls to the wrapped object are dispatched to the event loop running on the
    loop's native thread.

    Returned co-routines functions and Futures are waited upon until completion.
    '''

    def __init__(self, wrapped):
        self.__wrapped__ = wrapped

    def __getattribute__(self, name):
        wrapped = object.__getattribute__(self, '__wrapped__')
        if name == '__wrapped__':
            return wrapped

        # if name points to a property, this will execute the property getter
        # and return the value, else returns the value according to usual
        # lookup rules.
        value = object.__getattribute__(wrapped, name)

        # determine whether the call is being invoked locally, from within the
        # event loop's native thread, or elsewhere (usually the main thread)
        thread_id = object.__getattribute__(wrapped, '_sync_thread_id')
        is_local_thread = thread_id is None or threading.get_ident() == thread_id

        if is_local_thread:
            # passthru/no-op if being called from the same thread as the object
            # was created from.
            return value

        if inspect.ismethod(value) and not asyncio.iscoroutinefunction(value):
                # Wrap the sync method into a coroutine that can be dispatched
                # from the same thread as the main event loop is running in
                f = value.__func__
                f = _to_coroutine(f)
                value = types.MethodType(f, wrapped)
                #value = types.MethodType(f, self)

        elif inspect.isfunction(value) and not asyncio.iscoroutinefunction(value):
            # Dispatch functions in the main event loop thread too
            value = _to_coroutine(value)

        if inspect.isawaitable(value):
            return _dispatch_coroutine(value, wrapped._loop, wrapped._sync_abort_future)

        elif asyncio.iscoroutinefunction(value):
            # Wrap coroutine into synchronous dispatch
            @functools.wraps(value)
            def wrap(*a, **kw):
                return  _dispatch_coroutine(value(*a, **kw), wrapped._loop, wrapped._sync_abort_future)
            return wrap

        return value

    def __setattr__(self, name, value):
        if name == '__wrapped__':
            return super().__setattr__(name, value)
        wrapped = object.__getattribute__(self, '__wrapped__')
        return wrapped.__setattr__(name, value)

    def __repr__(self):
        wrapped = self.__wrapped__
        return "wrapped-" + object.__getattribute__(wrapped, '__repr__')()


def _to_coroutine(f):
    @functools.wraps(f)
    async def wrap(*a, **kw):
        return f(*a, **kw)
    return wrap

def _mkproxy(obj):
    '''Create a _SyncProxy for an object.'''
    # dynamically generate a class tailored for the wrapped object.
    d = {}
    cls = obj.__class__
    for name in dir(cls):
        if ((name.endswith('__') and name.startswith('__'))
            and name not in ('__class__', '__new__', '__init__', '__getattribute__', '__setattr__', '__repr__')):
                d[name] = _mkpt(cls, name)
    cls = type("_proxy_"+obj.__class__.__name__, (_SyncProxy,), d)
    proxy = cls(obj)
    obj.__wrapper__ = proxy
    return proxy

def _dispatch_coroutine(co, loop, abort_future):
    '''Execute a coroutine in a loop's thread and block till completion.

    Wraps a co-routine function; calling the function causes the co-routine
    to be dispatched in the event loop's thread and blocks until that call completes.

    Waits for either the coroutine or abort_future to complete.
    abort_future provides the main event loop with a means of triggering a
    clean shutdown in the case of an exception.
    '''
    fut = asyncio.run_coroutine_threadsafe(co, loop)
    result = concurrent.futures.wait((fut, abort_future), return_when=concurrent.futures.FIRST_COMPLETED)
    result =  list(result.done)[0].result()
    if getattr(result, '__wrapped__', None) is None:
        # If the call retuned the wrapped contents of a _SyncProxy then return
        # the enclosing proxy instead to the sync caller
        wrapper = getattr(result, '__wrapper__', None)
        if wrapper is not None:
            result = wrapper
    return result
