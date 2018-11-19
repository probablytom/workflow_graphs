import unittest
from asp import AdviceBuilder
from workflow_graphs import WorkflowGraph, End, anything_else, do_nothing
from workflow_graphs.workflow_utilities import Action
from copy import copy
from pydysofu import duplicate_last_step, fuzz


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


class TestFuzzing(unittest.TestCase):
    def test_asp_fuzzing(self):
        # Skip the second action.
        def skip_second_action(_, workflow, *args, **kwargs):
            workflow.graph[1] = Action(do_nothing)

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



