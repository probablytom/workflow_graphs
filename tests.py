import unittest
from asp import AdviceBuilder
from workflow_graphs import WorkflowGraph, End, anything_else


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
        flow.run_workflow(ctx, actor)

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
        flow.run_workflow(ctx, actor)

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
        flow.run_workflow(ctx, actor)

        self.assertEqual(ctx["value_was_equal_to_5"], "yes!")


class TestFuzzing(unittest.TestCase):
    def test_asp_fuzzing(self):
        def before():
            pass


        builder = AdviceBuilder()

    def test_pdsf_fuzzing(self):
        pass



