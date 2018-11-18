import unittest
from asp import AdviceBuilder
from workflow_graphs import WorkflowGraph, End, anything_else, do_nothing
from workflow_graphs.workflow_utilities import Action


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

    def test_subworkflow(self):

        subflow = WorkflowGraph()
        subflow.begin_with(add_one_to_value).then(add_one_to_value)

        flow = WorkflowGraph()
        flow.begin_with(add_value_to_ctx(1)) \
            .then(subflow) \
            .then(End)

        ctx = dict()
        actor = dict()
        flow.run_workflow(ctx, actor)

        self.assertEqual(ctx["stored_value"], 3)


class TestWorkflowGraphMethods(unittest.TestCase):

    def test_simple_index_of(self):

        flow = WorkflowGraph()
        add_one_action = Action(add_one_to_value)
        flow.begin_with(add_value_to_ctx(1)) \
            .then(add_one_action) \
            .then(End)

        self.assertEqual(flow.index_of(add_one_action), [1])

    def test_complex_index_of(self):

        action_to_find = Action(add_one_to_value)

        subflow = WorkflowGraph()
        subflow.begin_with(add_one_to_value).then(action_to_find)

        flow = WorkflowGraph()
        flow.begin_with(add_value_to_ctx(1)) \
            .decide_on(value_in_context("stored_value")) \
            .when(1).then(subflow) \
            .when(anything_else).then(do_nothing) \
            .join()

        flow.then(End)

        # [1, 1, 0, 1] because index should represent decision, case 1, enter subflow, second subflow step
        self.assertEqual(flow.index_of(action_to_find), [1, 1, 0, 1])




