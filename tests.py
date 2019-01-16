import unittest
from asp import AdviceBuilder
from workflow_graphs import WorkflowGraph, End, anything_else, do_nothing
from workflow_graphs import Actor, Department
from au import Clock, default_cost
from pydysofu import duplicate_last_step, fuzz


# There's gotta be an easier way.
def send_message(other_actor, message):
    @default_cost(1)
    def _send_message(ctx, actor, env):
        other_actor.recieve_message(message)
    return _send_message


def write_to_env(key, val):
    @default_cost(1)
    def _write_to_env(ctx, actor, env):
        env[key] = val
    return _write_to_env


def append_to_env(key, val):
    '''
    assumes a string val.
    :param key:
    :param val:
    :return:
    '''
    @default_cost(1)
    def _append_to_env(ctx, actor, env):
        if key not in env.keys():
            env[key] = ""
        env[key] += val
    return _append_to_env


@default_cost(1)
def set_actor_value(ctx, actor, env):
    actor["val"] = 1


@default_cost(1)
def increment_actor_value(ctx, actor, env):
    actor["val"] += 1


# Kipple that would live somewhere else in the final product
def add_value_to_ctx(val=5):
    def add_val(ctx, actor, env):
        ctx["stored_value"] = val
    return add_val


def add_one_to_value(ctx, actor, env):
    ctx["stored_value"] += 1


def value_held_in_context(ctx, actor, env):
    return ctx["stored_value"] == 2


def value_in_context(key):
    def get_value_from_context(ctx, actor, env):
        return ctx[key]
    return get_value_from_context


def write_to_context(k, v):
    def writer(ctx, actor, env):
        ctx[k] = v
    return writer


class TestBasicFlows(unittest.TestCase):
    def test_simplest_flow(self):
        flow = WorkflowGraph()
        flow.begin_with(add_value_to_ctx())
        flow.then(add_one_to_value)
        flow.then(End)

        ctx = dict()
        actor = dict()
        flow(ctx, actor)

        self.assertEqual(ctx["stored_value"], 6)

    def test_decision_flow(self):
        flow = WorkflowGraph()

        flow.begin_with(add_value_to_ctx(1)) \
            .then(add_one_to_value) \
            .decide_on(value_in_context("stored_value")) \
            .when(2) \
            .then(write_to_context("value_was_equal_to_2", "yes!")) \
            .when(anything_else) \
            .then(write_to_context("value_was_equal_to_2", "no!")) \
            .join() \
            .then(End)

        ctx = dict()
        actor = dict()
        flow(ctx, actor)

        self.assertEqual(ctx["value_was_equal_to_2"], "yes!")

    def test_labelling_on_flows(self):
        flow = WorkflowGraph()

        # The actual workflow! Set an initial value of 1, and increment it (labelling the incrementing node)
        flow.begin_with(add_value_to_ctx(1)) \
            .then(write_to_context("value_was_equal_to_5", "unknown")) \
            .then(add_one_to_value) \
            .call_that_step("incrementing") \

        # If we have the value 5, then write "yes"; if not, move to "incrementing".
        flow.decide_on(value_in_context("stored_value")) \
            .when(5) \
            .then(write_to_context("value_was_equal_to_5", "yes!")) \
            .when(anything_else) \
            .move_to_step_called("incrementing") \
            .join()

        # End the workflow.
        flow.then(End)

        ctx = dict()
        actor = dict()
        flow(ctx, actor)

        self.assertEqual(ctx["value_was_equal_to_5"], "yes!")

    def test_subworkflow(self):

        subflow = WorkflowGraph()
        subflow.begin_with(add_one_to_value).then(add_one_to_value)

        flow = WorkflowGraph()
        flow.begin_with(add_value_to_ctx(1)) \
            .then(subflow) \
            .then(End)

        ctx = dict()
        actor = dict()
        flow(ctx, actor)

        self.assertEqual(ctx["stored_value"], 3)


class TestWorkflowGraphMethods(unittest.TestCase):

    def test_simple_index_of(self):

        flow = WorkflowGraph()
        flow.begin_with(add_value_to_ctx(1)) \
            .then(add_one_to_value) \
            .then(End)

        self.assertEqual(flow.index_of(add_one_to_value), [1])

    def test_complex_index_of(self):

        action_to_find = add_value_to_ctx(2)

        subflow = WorkflowGraph()
        subflow.begin_with(add_value_to_ctx(1)).then(action_to_find)

        flow = WorkflowGraph()
        flow.begin_with(add_value_to_ctx(1)) \
            .decide_on(value_in_context("stored_value")) \
            .when(1).then(subflow) \
            .when(anything_else).then(do_nothing) \
            .join()

        flow.then(End)

        # [1, 1, 0, 1] because index should represent decision, case 1, enter subflow, second subflow step
        self.assertEqual(flow.index_of(action_to_find), [1, 1, 0, 1])


class TestFuzzing(unittest.TestCase):
    def test_asp_fuzzing(self):
        # Skip the second action.
        def skip_second_action(_, workflow, *args, **kwargs):
            workflow.graph[1] = do_nothing

        # A workflow to fuzz
        flow = WorkflowGraph().begin_with(add_value_to_ctx(3)).then(add_one_to_value).then(End)

        # TODO: Fix this so I can just call `flow()`, rather than `flow.run_workflow()`.
        #     ^ This is tricky because __call__ doesn't seem to go through __get_attribute,
        #       so ASP can't catch its lookup and weave.
        builder = AdviceBuilder()
        builder.add_prelude(flow.run_workflow, skip_second_action)
        builder.apply()

        # Run the flow-fuzzed workflow.
        ctx, actor = dict(), dict()
        flow.run_workflow(ctx, actor)

        # If we did skip the second step, then the flow's context should contain 3 and not 4.
        self.assertEqual(ctx["stored_value"], 3)

    def test_pdsf_fuzzing(self):

        @fuzz(duplicate_last_step)
        def action_to_fuzz(ctx, actor, env):
            ctx["val"] = 1
            ctx["val"] += 1

        # Set up the flow to fuzz
        flow = WorkflowGraph().begin_with(action_to_fuzz).then(End)

        ctx, actor = dict(), dict()
        flow.run_workflow(ctx, actor)

        self.assertTrue(ctx["val"] is 3)


class TestAUTimingModel(unittest.TestCase):
    def test_single_actor_simple_workflow(self):
        # Construct a flow
        flow = WorkflowGraph()
        flow.begin_with(set_actor_value)
        flow.then(increment_actor_value)
        flow.then(End)

        # Make a clock for syncing actors
        clock = Clock(max_ticks=5)

        # Set up actors to execute flow against clock
        actor = Actor(clock)
        actor.recieve_message(flow)

        # BEGIN TIME ITSELF
        clock.tick()

        # Did the workflow execute successfully?
        self.assertEqual(actor.actor_state["val"], 2)

    def test_multiple_actor_ping_pong(self):

        # Time to sync against
        clock = Clock(max_ticks=5)

        # Set up actors
        a_ping = Actor(clock, name="ping")
        a_pong = Actor(clock, name="pong")

        ping_flow = WorkflowGraph()\
            .begin_with(append_to_env("message", 'ping ')) \
            .then(send_message(a_pong, "PONG"))

        pong_flow = WorkflowGraph()\
            .begin_with(append_to_env("message", "pong "))\
            .then(send_message(a_ping, "PING"))

        # Allocate workflows
        a_ping.on_signal_process_workflow("PING", ping_flow)
        a_pong.on_signal_process_workflow("PONG", pong_flow)
        a_ping.recieve_message("PING")  # Something to get the ball rolling

        # BEGIN TIME ITSELF
        clock.tick()

        self.assertTrue(WorkflowGraph.environment["message"] == "ping pong ping pong ")


    def test_department_ping_pong(self):

        # Time to sync against
        clock = Clock(max_ticks=5)

        # Set up actors
        a_ping = Actor(clock, name="ping")
        a_pong = Actor(clock, name="pong")

        ping_dept = Department()
        ping_dept.add_member(a_ping)

        pong_dept = Department()
        pong_dept.add_member(a_pong)

        ping_flow = WorkflowGraph() \
            .begin_with(append_to_env("message", 'ping ')) \
            .then(send_message(pong_dept, "PONG"))

        pong_flow = WorkflowGraph() \
            .begin_with(append_to_env("message", "pong ")) \
            .then(send_message(ping_dept, "PING"))

        # Allocate workflows
        a_ping.on_signal_process_workflow("PING", ping_flow)
        a_pong.on_signal_process_workflow("PONG", pong_flow)
        a_ping.recieve_message("PING")  # Something to get the ball rolling

        # BEGIN TIME ITSELF
        clock.tick()

        self.assertTrue(WorkflowGraph.environment["message"] == "ping pong ping pong ")

