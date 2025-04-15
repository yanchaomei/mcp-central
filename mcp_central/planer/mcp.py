from typing import List

from fastmcp import FastMCP

mcp = FastMCP("planer")

query = ''

analysis = ''

plan_stack = []

current_plan = ''

executed_plans = []


@mcp.tool(description='Save the original user query, and save the conditions to '
                      'finish the job and the detail todo list.')
def save_query(user_query: str, conditions_and_todo_list) -> str:
    global query, analysis, current_plan
    if not query:
        query = user_query
    analysis = conditions_and_todo_list
    plan_stack.clear()
    current_plan = ''
    executed_plans.clear()
    return 'Save query done. Please make sure you will make detail plans and save it with `save_plan`.'


@mcp.tool(description='Split the user task to detail plans, and split detail plans to more detail sub-plans, '
                      'and save it with this function. '
                      'plans arg should be a json list of the detail plan instructions, '
                      'the newly added plans will be extended to the existed plans as a stack(pop last). '
                      'You should call `get_plan` when you need to execute a next step. '
                      'The return value will either be a successful message, or the error message.')
def save_plan(plans: List[str], override_plan: bool) -> str:
    try:
        global current_plan
        if isinstance(plans, str):
            plans = [plans]
        # plans: list = json.loads(plans)
        if override_plan:
            plan_stack.clear()
            current_plan = ''
        plan_stack.extend(list(reversed(plans)))
        return 'Save plan done. Please remember get plan when a previous step was done with `get_plan`.'
    except Exception as e:
        return str(e)


@mcp.tool(description='Get your current plan, call this if the previous step '
                      'has finished and you need to execute a next step. ')
def get_plan() -> str:
    global current_plan
    if current_plan:
        executed_plans.append(current_plan)
        current_plan = ''
    if plan_stack:
        current_plan = plan_stack.pop(-1)
    content = ''
    executed_plans_str = '\n'.join(executed_plans)
    plan_stack_str = '\n'.join(list(reversed(plan_stack)))
    content += f'Your history plans:\n{executed_plans_str or "No history plans"}\n\n'
    content += f'Your future plans:\n{plan_stack_str or "No future plans"}\n\n'
    content += f'Your current plan:\n{current_plan or "No current plan"}\n\n'
    if current_plan:
        content += ('You may:\n'
                    '1. Execute the current plan\n'
                    '2. If something wrong with your plans, '
                    'you can give up and override your current and all future plans'
                    '(except the history plans) with '
                    '`save_plan` and args: {"plans": new-plans, "override_plan": **true**}\n'
                    '3. Split the current plan to sub plans and save them with `save_plan` and args: '
                    '{"plans": sub-plans, "override_plan": **false**}\n'
                    'Now make your choice and continue:')
    return content


@mcp.tool(description='Call this after you have finished all your jobs, '
                      'like collect information and output the final result.')
def task_done():
    global query, analysis, plan_stack, current_plan, executed_plans
    plan_stack_str = '\n'.join(list(reversed(plan_stack)))
    if plan_stack_str:
        plan_stack_str = f'You have unfinished tasks: {plan_stack_str}\n\n'
    content = (f'The original user query: {query}\n\n'
               f'The conditions and detail todo list: {analysis}\n\n'
               f'{plan_stack_str}'
               f'Please double-check your answer with the query and todo list, '
               f'Have all the conditions been satisfied? Are there no factual contradictions? '
               f'Have all the necessary plans been completed?'
               f'If you have finished the job, output <task_done> in your next round, '
               f'if not, redo your plans use alternative strategies and call `save_plan` '
               'with args: {"plans": new-plans, "override_plan": true} and restart:')
    return content


if __name__ == "__main__":
    mcp.run(transport="stdio")
