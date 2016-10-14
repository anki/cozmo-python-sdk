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

import unittest

import asyncio
from asyncio import test_utils

from cozmo import event
from cozmo import exceptions


class DispatchTest(event.Dispatcher):
    pass


class EventReceiver(event.Dispatcher):
    _result_evt_one = None
    _result_evt_one_internal = None
    _result_evt_two = None
    _result_evt_internal = None
    _result_evt_child1 = None

    def recv_evt_one(self, evt, **kw):
        self._result_evt_one = evt

    def _recv_evt_one(self, evt, **kw):
        self._result_evt_one_internal = evt

    async def recv_evt_two(self, evt, param1=False, **kw):
        self._result_evt_two = evt
        if param1:
            raise exceptions.StopPropogation

    def _recv_evt_child1(self, evt, **kw):
        self._result_evt_child1 = evt

    def recv_default_handler(self, evt, **kw):
        self._result_default_handler = evt

    def _recv_default_handler(self, evt, **kw):
        self._result_default_handler_internal = evt

    def _recv_evt_internal(self, evt, **kw):
        self._result_evt_internal = evt

    def named_handler(self, evt, param1=False, **kw):
        self._result_named_handler = evt
        if param1:
            raise exceptions.StopPropogation



class EventTests(test_utils.TestCase):
    def setUp(self):
        self.loop = self.new_test_loop()
        self.addCleanup(self.loop.close)
        event.registered_events = {}
        self._register_events()

    def _register_events(self):
        class EvtOne(event.Event):
            "Test event"
            param1 = "Parameter one"
            param2 = "Parameter two"
            param3 = "Parameter three"
        class EvtTwo(event.Event):
            "Test event"
            param1 = "Parameter one"
            param2 = "Parameter two"
        class _EvtInternal(event.Event):
            "Internal event"
            param1 = "Parameter one"
            param2 = "Parameter two"
        class _EvtChild1(EvtOne):
            'Child event'
            param4 = "Parameter four"
        class _EvtChild2(_EvtChild1):
            'Subchild event'
            param5 = "Parameter five"
        self.evt_one = EvtOne
        self.evt_two = EvtTwo
        self.evt_internal = _EvtInternal
        self.evt_child1 = _EvtChild1
        self.evt_child2 = _EvtChild2

    def test_dupe_event_def(self):
        # Duplicate event names should fail
        class EvtTest1(event.Event):
            "test1"

        class EvtTest2(event.Event):
            "test2"

        with self.assertRaises(ValueError):
            class EvtTest1(event.Event):
                "test3"

    def test_event_set_attr(self):
        ev = self.evt_one(param1=123, param3=345)
        self.assertEqual(ev.param1, 123)
        self.assertEqual(ev.param2, None)
        self.assertEqual(ev.param3, 345)

    def test_event_dispatch_func(self):
        ev = self.evt_one(param1=123, param3=345)
        cap_kw = {}
        cap_evt = None
        def capture(evt, **kw):
            nonlocal cap_kw, cap_evt
            cap_kw = kw
            cap_evt = evt
            return "set"
        result = ev._dispatch_to_func(capture)
        self.assertEqual(result, "set")
        self.assertEqual(cap_evt, ev)
        self.assertEqual(cap_kw, {"param1": 123, "param2": None, "param3": 345})

    def test_event_dispatch_obj(self):
        ev = self.evt_one(param1=123, param3=345)
        cap_kw = {}
        cap_evt = None
        class capture:
            def recv_evt_one(self, evt, **kw):
                nonlocal cap_kw, cap_evt
                cap_kw = kw
                cap_evt = evt
                return "set"
        result = ev._dispatch_to_obj(capture())
        self.assertEqual(result, "set")
        self.assertEqual(cap_evt, ev)
        self.assertEqual(cap_kw, {"param1": 123, "param2": None, "param3": 345})

    def test_event_dispatch_obj_default(self):
        ev = self.evt_one(param1=123, param3=345)
        cap_kw = {}
        cap_evt = None
        class capture:
            def recv_default_handler(self, evt, **kw):
                nonlocal cap_kw, cap_evt
                cap_kw = kw
                cap_evt = evt
                return "set"
        result = ev._dispatch_to_obj(capture())
        self.assertEqual(result, "set")
        self.assertEqual(cap_evt, ev)
        self.assertEqual(cap_kw, {"param1": 123, "param2": None, "param3": 345})

    def test_event_dispatch_obj_default_internal(self):
        ev = self.evt_internal(param1=123)
        cap_kw = {}
        cap_evt = None
        class capture:
            def _recv_default_handler(self, evt, **kw):
                nonlocal cap_kw, cap_evt
                cap_kw = kw
                cap_evt = evt
                return "set"
        result = ev._dispatch_to_obj(capture())
        self.assertEqual(result, "set")
        self.assertEqual(cap_evt, ev)
        self.assertEqual(cap_kw, {"param1": 123, "param2": None})

    def test_event_dispatch_future(self):
        ev = self.evt_one(param1=123, param3=345)
        f = asyncio.Future(loop=self.loop)
        ev._dispatch_to_future(f)
        self.assertEqual(f.result(), ev)

    def test_add_remove_handler_byfunc(self):
        ins = DispatchTest(loop=self.loop)
        ins.add_event_handler(self.evt_one, "one")
        ins.add_event_handler(self.evt_one, "two")
        ins.add_event_handler(self.evt_two, "three")
        self.assertEqual(ins._dispatch_handlers["EvtOne"],
                [event.Handler(ins, self.evt_one, 'one'), event.Handler(ins, self.evt_one, 'two')])
        self.assertEqual(ins._dispatch_handlers["EvtTwo"],
                [event.Handler(ins, self.evt_two, 'three')])

        ins.remove_event_handler(self.evt_one, 'two')
        self.assertEqual(ins._dispatch_handlers["EvtOne"],
                [event.Handler(ins, self.evt_one, 'one')])

        with self.assertRaises(ValueError):
            ins.remove_event_handler(self.evt_one, 'two')

    def test_dispatch_event_obj_sync(self):
        recv = EventReceiver(loop=self.loop)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        self.assertEqual(recv._result_evt_one.param2, 123)

    def test_dispatch_event_obj_async(self):
        recv = EventReceiver(loop=self.loop)
        recv.dispatch_event(self.evt_two, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        self.assertEqual(recv._result_evt_two.param2, 123)

    def test_dispatch_event_obj_internal(self):
        recv = EventReceiver(loop=self.loop)
        recv.dispatch_event(self.evt_internal, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        self.assertEqual(recv._result_evt_internal.param2, 123)

    def test_dispatch_event_handler(self):
        # should fire both the object's handler, and the registered handler
        recv = EventReceiver(loop=self.loop)
        cap_evt = None
        def capture(evt, **kw):
            nonlocal cap_evt
            cap_evt = evt
        recv.add_event_handler(self.evt_one, capture)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        self.assertEqual(recv._result_evt_one.param2, 123)
        self.assertEqual(cap_evt.param2, 123)

    def test_dispatch_event_async_handler(self):
        # should fire both the object's handler, and the registered handler
        recv = EventReceiver(loop=self.loop)
        cap_evt = None
        async def capture(evt, **kw):
            nonlocal cap_evt
            cap_evt = evt
        recv.add_event_handler(self.evt_one, capture)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        self.assertEqual(recv._result_evt_one.param2, 123)
        self.assertEqual(cap_evt.param2, 123)

    def test_dispatch_event_future(self):
        # should fire both the future, and the registered handler
        recv = EventReceiver(loop=self.loop)
        f = asyncio.Future(loop=self.loop)
        recv.add_event_handler(self.evt_one, f)
        self.assertEqual(len(recv._dispatch_handlers['EvtOne']), 1)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        evt = f.result()
        self.assertEqual(recv._result_evt_one.param2, 123)
        self.assertEqual(evt.param2, 123)

        # future should of been removed from the handler list
        self.assertEqual(len(recv._dispatch_handlers['EvtOne']), 0)

    def test_dispatch_to_parent(self):
        recv_parent = EventReceiver(loop=self.loop)
        recv_child = EventReceiver(loop=self.loop, dispatch_parent=recv_parent)
        recv_child.dispatch_event(self.evt_one, param1=False, param2=123)

        test_utils.run_briefly(self.loop)
        self.assertEqual(recv_child._result_evt_one.param2, 123)
        self.assertEqual(recv_parent._result_evt_one.param2, 123)

    def test_dispatch_stop_propogation(self):
        recv = EventReceiver(loop=self.loop)
        cap_evt = None
        def handler(evt, **kw):
            nonlocal cap_evt
            cap_evt = evt
            raise exceptions.StopPropogation()
        recv.add_event_handler(self.evt_one, handler)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        self.assertEqual(cap_evt.param2, 123)
        self.assertIsNone(recv._result_evt_one)

    def test_dispatch_wait_for_event(self):
        recv = EventReceiver(loop=self.loop)
        co = recv.wait_for(self.evt_one, timeout=None)
        f = asyncio.ensure_future(co, loop=self.loop)
        test_utils.run_briefly(self.loop)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        evt = f.result()
        self.assertEqual(evt.param2, 123)
        self.assertEqual(recv._result_evt_one.param2, 123)

    def test_dispatch_wait_for_timeout(self):
        def gen():
            yield
            # fake a 20 second delay
            yield 20

        loop = self.new_test_loop(gen=gen)
        recv = EventReceiver(loop=loop)
        co = recv.wait_for(self.evt_one, timeout=10)
        with self.assertRaises(asyncio.TimeoutError):
            loop.run_until_complete(co)

    def test_dispatch_wait_for_filter(self):
        recv = EventReceiver(loop=self.loop)
        filter = event.Filter(self.evt_one, param2=456)
        co = recv.wait_for(filter, timeout=None)
        f = asyncio.ensure_future(co, loop=self.loop)
        test_utils.run_briefly(self.loop)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        self.assertFalse(f.done())

        recv.dispatch_event(self.evt_one, param1=False, param2=456)
        test_utils.run_briefly(self.loop)
        self.assertTrue(f.done())
        self.assertEqual(f.result().param2, 456)

    def test_dispatch_filter_decorator_single(self):
        recv = EventReceiver(loop=self.loop)
        cap_evt = None

        @event.filter_handler(self.evt_one, param2=456)
        def handler(evt, **kw):
            nonlocal cap_evt
            cap_evt = evt

        recv.add_event_handler(self.evt_one, handler)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        self.assertIsNone(cap_evt)

        recv.dispatch_event(self.evt_one, param1=False, param2=456)
        test_utils.run_briefly(self.loop)
        self.assertIsNotNone(cap_evt)
        self.assertEqual(cap_evt.param2, 456)

    def test_dispatch_filter_setattr(self):
        recv = EventReceiver(loop=self.loop)
        filter = event.Filter(self.evt_one)
        filter.param2 = 456
        with self.assertRaises(AttributeError):
            filter.param_invalid = 123
        co = recv.wait_for(filter, timeout=None)
        f = asyncio.ensure_future(co, loop=self.loop)
        test_utils.run_briefly(self.loop)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)
        self.assertFalse(f.done())

        recv.dispatch_event(self.evt_one, param1=False, param2=456)
        test_utils.run_briefly(self.loop)
        self.assertTrue(f.done())
        self.assertEqual(f.result().param2, 456)

    def test_dispatch_filter_decorator_multiple(self):
        recv = EventReceiver(loop=self.loop)
        cap_evt = None

        @event.filter_handler(self.evt_one, param2=456)
        @event.filter_handler(self.evt_one, param2=789)
        def handler(evt, **kw):
            nonlocal cap_evt
            cap_evt = evt

        recv.add_event_handler(self.evt_one, handler)

        for num in (123,456,234,789):
            cap_evt = None
            recv.dispatch_event(self.evt_one, param1=False, param2=num)
            test_utils.run_briefly(self.loop)
            if num in (123, 234):
                self.assertIsNone(cap_evt, msg="num=%d evt=%s" % (num, cap_evt))
            else:
                self.assertIsNotNone(cap_evt, msg="num=%d" % (num,))
                self.assertEqual(cap_evt.param2, num, msg="num=%d evt=%s" % (num, cap_evt))

    def test_dispatch_filter_decorator_lambda(self):
        recv = EventReceiver(loop=self.loop)
        cap_evt = None

        @event.filter_handler(self.evt_one, param2=lambda val: val > 400)
        def handler(evt, **kw):
            nonlocal cap_evt
            cap_evt = evt

        recv.add_event_handler(self.evt_one, handler)

        for num in (123,456,234,789):
            cap_evt = None
            recv.dispatch_event(self.evt_one, param1=False, param2=num)
            test_utils.run_briefly(self.loop)
            if num in (123, 234):
                self.assertIsNone(cap_evt, msg="num=%d evt=%s" % (num, cap_evt))
            else:
                self.assertIsNotNone(cap_evt, msg="num=%d" % (num,))
                self.assertEqual(cap_evt.param2, num, msg="num=%d evt=%s" % (num, cap_evt))

    def test_obj_receiver_filter(self):
        cap_evt = None

        class filtered_receiver(event.Dispatcher):
            @event.filter_handler(self.evt_one, param2=456)
            def recv_evt_one(self, evt, **kw):
                nonlocal cap_evt
                cap_evt = evt

        recv = filtered_receiver(loop=self.loop)
        recv.dispatch_event(self.evt_one, param1=False, param2=100)
        test_utils.run_briefly(self.loop)
        self.assertIsNone(cap_evt)

        recv.dispatch_event(self.evt_one, param1=False, param2=456)
        test_utils.run_briefly(self.loop)
        self.assertIsNotNone(cap_evt)
        self.assertEqual(cap_evt.param2, 456)

    def test_dispatch_parents_to_handler(self):
        # Test dispatching an event subclass to a handler listening to the parent
        recv = EventReceiver(loop=self.loop)
        cap_evts = []
        def capture(evt, **kw):
            nonlocal cap_evts
            cap_evts.append(evt)

        recv.add_event_handler(self.evt_one, capture)
        recv.dispatch_event(self.evt_child2, param1=False, param2=234, param5=567)
        test_utils.run_briefly(self.loop)

        # only the most specific event (EvtChild2) should of been sent to the handler
        self.assertEqual(1, len(cap_evts))
        cap_evt = cap_evts[0]
        self.assertIsInstance(cap_evt, self.evt_child2)
        self.assertEqual(cap_evt.param5, 567)

    def test_dispatch_parents_to_obj(self):
        # Dispatching a subclass event to an object should result in only
        # the most specific receiver being called
        # EventReciver listens to evt_child1, but not evt_child2 so should
        # receive a notification there (and only there)
        recv = EventReceiver(loop=self.loop)
        recv.dispatch_event(self.evt_child2, param1=False, param2=234, param5=567)
        test_utils.run_briefly(self.loop)

        self.assertEqual(recv._result_evt_child1.__class__, self.evt_child2)
        self.assertIsNone(recv._result_evt_one)

    def test_dispatch_oneshot(self):
        count = 0
        @event.oneshot
        def handler(evt, **kw):
            nonlocal count
            count += 1

        recv = event.Dispatcher(loop=self.loop)
        hnd = recv.add_event_handler(self.evt_one, handler)
        self.assertTrue(hnd.oneshot)

        # dispatch twice on the same loop run; should still only be called once
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)

        self.assertEqual(count, 1)

    def test_handler_disable_implicit(self):
        count = 0
        def handler(evt, **kw):
            nonlocal count
            count += 1

        recv = event.Dispatcher(loop=self.loop)
        hnd = recv.add_event_handler(self.evt_one, handler)
        # call twice
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)

        # should no longer be dispatched
        hnd.disable()
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)

        self.assertEqual(count, 2)

    def test_handler_disable_explicit(self):
        count = 0
        def handler(evt, **kw):
            nonlocal count
            count += 1

        recv = event.Dispatcher(loop=self.loop)
        hnd = recv.add_event_handler(self.evt_one, handler)

        # call twice
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)

        # should no longer be dispatched
        recv.remove_event_handler(self.evt_one, hnd)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)

        self.assertEqual(count, 2)

    def test_dispatch_to_children(self):
        class Target(event.Dispatcher):
            def __init__(self, **kw):
                super().__init__(**kw)
                self.count = 0

            def recv_evt_one(self, *a, **kw):
                print("TRAP", self)
                self.count += 1

        parent = Target(loop=self.loop)
        child1 = Target(loop=self.loop)
        child2 = Target(loop=self.loop)
        other = Target(loop=self.loop)
        parent._add_child_dispatcher(child1)
        parent._add_child_dispatcher(child2)

        parent.dispatch_event(self.evt_one, param1=False, param2=123)
        test_utils.run_briefly(self.loop)

        self.assertEqual(parent.count, 1)
        self.assertEqual(child1.count, 1)
        self.assertEqual(child2.count, 1)
        self.assertEqual(other.count, 0)

    def test_dispatch_child_loops(self):
        # ensure that a child event handler cannot create a dispatch loop
        parent = event.Dispatcher(loop=self.loop)
        child = event.Dispatcher(loop=self.loop)
        parent._add_child_dispatcher(child)

        count = 0
        def handler(evt, *a, **kw):
            nonlocal count
            count += 1
            parent.dispatch_event(evt)

        child.add_event_handler(self.evt_one, handler)
        parent.dispatch_event(self.evt_one, param1=False, param2=123)

        test_utils.run_briefly(self.loop)

        # run loop twice to allow a second dispatched event to be delivered
        # (or hopefully not)
        test_utils.run_briefly(self.loop)

        self.assertEqual(count, 1)

    def test_dispatch_child_dupe(self):
        # ensure that a child handler cannot redeliver an event to a sibling
        # child object
        parent = event.Dispatcher(loop=self.loop)
        class Child(event.Dispatcher):
            def __init__(self, **kw):
                super().__init__(**kw)
                self.count = 0

            def recv_evt_one(self, evt, *a, **kw):
                # attempt to deliver to the other child
                self.count += 1
                self.other_child.dispatch_event(evt)

        child1 = Child(loop=self.loop)
        child2 = Child(loop=self.loop)
        child1.other_child = child2
        child2.other_child = child1

        parent._add_child_dispatcher(child1)
        parent._add_child_dispatcher(child2)

        parent.dispatch_event(self.evt_one, param1=False, param2=123)
        for i in range(4):
            test_utils.run_briefly(self.loop)

        self.assertEqual(child1.count, 1)
        self.assertEqual(child2.count, 1)

    def test_stop_dispatcher(self):
        count = 0
        def handler(evt, *a, **kw):
            nonlocal count
            count += 1

        recv = event.Dispatcher(loop=self.loop)
        recv.add_event_handler(self.evt_one, handler)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        recv.dispatch_event(self.evt_one, param1=False, param2=123)
        recv._stop_dispatcher()
        recv.dispatch_event(self.evt_one, param1=False, param2=123)

        test_utils.run_briefly(self.loop)
        self.assertEqual(count, 2)

    def test_obj_abort_futures(self):
        recv = event.Dispatcher(loop=self.loop)
        fut1 = asyncio.Future(loop=self.loop)
        fut2 = asyncio.Future(loop=self.loop)
        fut3 = asyncio.Future(loop=self.loop)
        fut3.set_result('result') # should not be aborted

        exc = ValueError('test exception')

        recv.add_event_handler(self.evt_one, fut1)
        recv.add_event_handler(self.evt_one, fut2)
        recv.add_event_handler(self.evt_one, fut3)
        print(recv._dispatch_handlers)

        recv._abort_event_futures(exc)
        self.assertTrue(fut1.done())
        self.assertTrue(fut2.done())
        self.assertEqual(fut1.exception(), exc)
        self.assertEqual(fut2.exception(), exc)

        # futures should of been removed
        handlers = recv._dispatch_handlers['EvtOne']
        self.assertEqual(len(handlers), 0)

    def test_global_abort_futures(self):
        # check that the global _abort_futures call actually calls
        # each active dispatcher objects' abort_futures method.
        event.active_dispatchers.clear()
        # define two event classes that should auto-register themselves
        class Target(event.Dispatcher):
            def __abort_event_futures(exc):
                self._abort_exc = exc

        recv1 = Target(loop=self.loop)
        recv2 = Target(loop=self.loop)

        self.assertEqual(len(event.active_dispatchers), 2)

        fut1 = asyncio.Future(loop=self.loop)
        fut2 = asyncio.Future(loop=self.loop)
        recv1.add_event_handler(self.evt_one, fut1)
        recv2.add_event_handler(self.evt_one, fut2)

        exc = ValueError('test exception')
        event._abort_futures(exc)

        self.assertTrue(fut1.done())
        self.assertTrue(fut2.done())
        self.assertEqual(fut1.exception(), exc)
        self.assertEqual(fut2.exception(), exc)

    def test_wait_for_first_with_discard1(self):
        # test that uncompleted futures are cancelled
        fut1 = asyncio.Future(loop=self.loop)
        fut2 = asyncio.Future(loop=self.loop)
        self.loop.call_soon(lambda: fut2.set_result("done"))
        co = event.wait_for_first(fut1, fut2, loop=self.loop)
        result = self.loop.run_until_complete(co)
        self.assertEqual(result, "done")
        self.assertTrue(fut1.cancelled())

    def test_wait_for_first_with_discard2(self):
        # test that racing completed futures are marked as done
        class Fut(asyncio.Future):
            def result(self):
                self.result_called = True
                return super().result()

        fut1 = Fut(loop=self.loop)
        fut2 = Fut(loop=self.loop)
        self.loop.call_soon(lambda: fut2.set_result("done"))
        self.loop.call_soon(lambda: fut1.set_result("done"))
        co = event.wait_for_first(fut1, fut2, loop=self.loop)
        result = self.loop.run_until_complete(co)
        self.assertEqual(result, "done") # don't care which future
        self.assertTrue(fut1.result_called)
        self.assertTrue(fut2.result_called)

    def test_wait_for_first_with_discard_exception(self):
        # test that racing completed futures are marked as done
        class Fut(asyncio.Future):
            def result(self):
                self.result_called = True
                return super().result()

        fut1 = Fut(loop=self.loop)
        fut2 = Fut(loop=self.loop)
        self.loop.call_soon(lambda: fut2.set_result("done"))
        self.loop.call_soon(lambda: fut1.set_exception("test exception"))
        co = event.wait_for_first(fut1, fut2, loop=self.loop)
        result = self.loop.run_until_complete(co)
        self.assertEqual(result, "done") # must get result rather than exception
        self.assertTrue(fut1.result_called)
        self.assertTrue(fut2.result_called)

    def test_wait_for_first_no_discard(self):
        fut1 = asyncio.Future(loop=self.loop)
        fut2 = asyncio.Future(loop=self.loop)
        self.loop.call_soon(lambda: fut2.set_result("done"))
        co = event.wait_for_first(fut1, fut2, discard_remaining=False, loop=self.loop)
        result = self.loop.run_until_complete(co)
        self.assertEqual(result, "done")
        self.assertFalse(fut1.cancelled())

    def test_wait_for_first_raise_exc(self):
        # ensure raised exceptions are returned
        fut1 = asyncio.Future(loop=self.loop)
        fut2 = asyncio.Future(loop=self.loop)
        class TestExc(Exception): pass
        exc = TestExc('test exception')

        self.loop.call_soon(lambda: fut2.set_exception(exc))
        co = event.wait_for_first(fut1, fut2, loop=self.loop)
        with self.assertRaises(TestExc):
            result = self.loop.run_until_complete(co)
        self.assertTrue(fut1.cancelled())
