from typing import List, Dict, Union, Any

from fastmcp import FastMCP

mcp = FastMCP("planer")

query = ''

analysis = ''

plan_stack = []

current_plan = ''

executed_plans = []

intermediate_results = {}


@mcp.tool(description='Documents the user\'s original request and task requirements. Use this at the beginning of '
                      'a complex task to record both the user\'s query and the specific success criteria. The '
                      '\'conditions_and_todo_list\' parameter should contain a structured breakdown of completion '
                      'conditions and high-level steps needed. This tool initializes the planning system and clears '
                      'any existing plans.')
def initialize_task(user_query: str, conditions_and_todo_list) -> str:
    global query, analysis, current_plan
    query = user_query
    analysis = conditions_and_todo_list
    plan_stack.clear()
    current_plan = ''
    executed_plans.clear()
    return ('Task initialized successfully. Now you should create a detailed step-by-step plan '
            'to address the user\'s request. Break down the task into specific, actionable steps and save '
            'them using the `create_execution_plan` tool. Support for hierarchical plans is available - '
            'you can create nested plans with main steps and sub-steps for better organization.')


@mcp.tool(description='Creates or updates your execution plan with specific actionable steps. The \'plans\' should be '
                      'either a list of clear, concrete instructions or a hierarchical structure with main steps '
                      'and sub-steps (using dictionaries with "step" and "substeps" keys). When '
                      '\'override_plan=True\', all existing future plans will be replaced; when \'False\', the new plans '
                      'will be added to the end of the existing queue. Plans are executed in the order provided. '
                      'After creating a plan, use `advance_to_next_step` to start executing steps sequentially. '
                      'Example format: [{"step": "Main step 1", "substeps": ["Sub-step 1.1", "Sub-step 1.2"]}, '
                      '"Simple step without substeps", {"step": "Main step 3", "substeps": ["Sub-step 3.1"]}]')
def create_execution_plan(plans: List[Union[str, Dict[str, Any]]], override_plan: bool) -> str:
    try:
        global current_plan

        # Ensure plans is a list even if a single item was provided
        if isinstance(plans, str) or (isinstance(plans, dict) and "step" in plans):
            plans = [plans]

        # Flatten hierarchical plans into a linear sequence
        flattened_plans = []
        for plan in plans:
            if isinstance(plan, str):
                flattened_plans.append(plan)
            elif isinstance(plan, dict) and "step" in plan:
                # Add the main step
                main_step = plan["step"]
                if "substeps" in plan and plan["substeps"]:
                    # Add main step as a header
                    flattened_plans.append(f"MAIN: {main_step}")
                    # Add all substeps with indentation
                    for substep in plan["substeps"]:
                        flattened_plans.append(f"SUB: {substep}")
                else:
                    # Just add the main step if no substeps
                    flattened_plans.append(main_step)
            else:
                raise ValueError(f"Invalid plan format: {plan}")

        if override_plan:
            plan_stack.clear()
            current_plan = ''

        # Add plans in reverse order so they can be popped in the correct sequence
        plan_stack.extend(list(reversed(flattened_plans)))

        return (
            'Execution plan successfully created. Now call `advance_to_next_step` to retrieve your first action item and begin execution. '
            'Remember to call `advance_to_next_step` again after completing each step to progress through your plan.\n\n'
            'Your hierarchical plan has been processed correctly, with main steps and sub-steps properly organized for sequential execution.')
    except Exception as e:
        return f'Error creating execution plan: {str(e)}. Please check your input format and try again.'


@mcp.tool(description='Retrieves the next action from your execution plan and marks the current step as complete. '
                      'Call this after finishing your current task to move to the next step. The tool will show you: '
                      '1) Steps you\'ve already completed, 2) Your upcoming steps, and 3) The specific action to take '
                      'now. If needed, you can further break down the current step into smaller sub-steps or completely '
                      'revise your plan. Hierarchical plan structure is preserved in the display, showing main steps '
                      'and their corresponding sub-steps clearly.')
def advance_to_next_step() -> str:
    global current_plan
    if current_plan:
        executed_plans.append(current_plan)
        current_plan = ''
    if plan_stack:
        current_plan = plan_stack.pop(-1)

    # Format executed plans to show hierarchy with indentation
    executed_plans_str = ""
    for plan in executed_plans:
        if plan.startswith("MAIN: "):
            executed_plans_str += f"✓ {plan[6:]}\n"
        elif plan.startswith("SUB: "):
            executed_plans_str += f"  ✓ {plan[5:]}\n"
        else:
            executed_plans_str += f"✓ {plan}\n"

    executed_plans_str = executed_plans_str.strip() if executed_plans_str else "None"

    # Format upcoming plans to show hierarchy with indentation
    plan_stack_str = ""
    for plan in reversed(plan_stack):
        if plan.startswith("MAIN: "):
            plan_stack_str += f"• {plan[6:]}\n"
        elif plan.startswith("SUB: "):
            plan_stack_str += f"  • {plan[5:]}\n"
        else:
            plan_stack_str += f"• {plan}\n"

    plan_stack_str = plan_stack_str.strip() if plan_stack_str else "None"

    content = f'📋 PLAN STATUS:\n\n'

    # Include original query and analysis
    if query:
        content += f'📝 ORIGINAL USER QUERY:\n"{query}"\n\n'
    if analysis:
        content += f'🎯 TASK REQUIREMENTS:\n{analysis}\n\n'

    content += f'✅ COMPLETED STEPS:\n{executed_plans_str}\n\n'
    content += f'⏭️ UPCOMING STEPS:\n{plan_stack_str}\n\n'

    if current_plan:
        # Display current step, respecting hierarchy
        if current_plan.startswith("MAIN: "):
            display_plan = f"MAIN STEP: {current_plan[6:]}"
        elif current_plan.startswith("SUB: "):
            display_plan = f"SUB-STEP: {current_plan[5:]}"
        else:
            display_plan = current_plan

        content += f'🔄 CURRENT STEP TO EXECUTE:\n"{display_plan}"\n\n'
        content += f'Execute this step now and provide the results:\n'
        # content += ('OPTIONS:\n'
        #             '1️⃣ Execute this step now and provide the results\n'
        #             '2️⃣ If this step is too complex, break it down by using `create_execution_plan` with '
        #             '{"plans": [detailed sub-steps], "override_plan": false}\n'
        #             '3️⃣ If you need to revise your entire plan, use `create_execution_plan` with '
        #             '{"plans": [new complete plan], "override_plan": true}\n\n'
        #             'Please proceed with your chosen option:')
    else:
        content += ('⚠️ NO CURRENT STEP AVAILABLE. You have either:\n'
                    '• Completed all planned steps - use `verify_task_completion` to verify completion\n'
                    '• Not yet created a plan - use `create_execution_plan` to create one\n')

    return content


@mcp.tool(
    description='Validates your completed work against the original requirements. Call this tool when you believe '
                'you\'ve finished all required tasks. It will display the original query, success criteria, and '
                'any remaining plans for verification. Use this final check to ensure all requirements have been '
                'met before delivering your response to the user.')
def verify_task_completion():
    global query, analysis, plan_stack, current_plan, executed_plans

    # Check for unfinished tasks
    unfinished_warning = ""
    if plan_stack or current_plan:
        unfinished_plans = []

        # Format unfinished plans preserving hierarchy
        for plan in reversed(plan_stack):
            if plan.startswith("MAIN: "):
                unfinished_plans.append(plan[6:])
            elif plan.startswith("SUB: "):
                unfinished_plans.append(f"  {plan[5:]}")
            else:
                unfinished_plans.append(plan)

        if current_plan:
            if current_plan.startswith("MAIN: "):
                unfinished_plans.insert(0, current_plan[6:])
            elif current_plan.startswith("SUB: "):
                unfinished_plans.insert(0, f"  {current_plan[5:]}")
            else:
                unfinished_plans.insert(0, current_plan)

        unfinished_warning = (f'⚠️ WARNING: You have {len(unfinished_plans)} unfinished task(s):\n'
                              f'{", ".join(unfinished_plans)}\n\n')

    # Format completed tasks preserving hierarchy
    completed_summary = ""
    for plan in executed_plans:
        if plan.startswith("MAIN: "):
            completed_summary += f"✓ {plan[6:]}\n"
        elif plan.startswith("SUB: "):
            completed_summary += f"  ✓ {plan[5:]}\n"
        else:
            completed_summary += f"✓ {plan}\n"

    completed_summary = completed_summary.strip() if completed_summary else "None"

    content = (f'🔍 FINAL VERIFICATION:\n\n'
               f'📝 ORIGINAL USER QUERY:\n"{query}"\n\n'
               f'📋 SUCCESS CRITERIA:\n{analysis}\n\n'
               f'✅ COMPLETED TASKS:\n{completed_summary}\n\n'
               f'{unfinished_warning}'
               f'📊 COMPLETION CHECKLIST:\n'
               f'1. Have all required conditions been satisfied? (Review success criteria)\n'
               f'2. Is your answer directly responsive to the user\'s query?\n'
               f'3. Have you provided all requested information/deliverables?\n'
               f'4. Is your answer factually accurate with no contradictions?\n\n'
               f'If all requirements are satisfied, include "<task_done>" in your next response.\n'
               f'If requirements are not fully met, create a new plan with `create_execution_plan` using '
               f'{{"plans": [remaining steps], "override_plan": true}} or CONTINUE EXECUTE your current plan:')

    return content


# not work for now
@mcp.tool(description='Stores your previous round tool call results for later reference. '
                      'Use this to save important outputs '
                      'from previous tool calls such as search results, web content, or any data you\'ll need to '
                      'access again. Provide the title of the original call and a clear summary of what '
                      'the data contains. This helps maintain an organized record of important information. '
                      'This will adjust your message history - stored content will appear as IDs and summaries '
                      'rather than full content, reducing token usage and keeping the conversation concise.')
def store_intermediate_results(title: str, data: str, summary: str) -> str:
    global intermediate_results

    # Add to results store with simplified metadata
    intermediate_results[title] = {
        "data": data,
        "summary": summary,
        "timestamp": "timestamp_placeholder"  # In a real implementation, use actual timestamp
    }

    all_keys = list(intermediate_results.keys())

    return (f'✅ Tool result stored successfully with ID: "{title}"\n'
            f'📝 Summary: {summary}\n\n'
            f'Currently stored results ({len(all_keys)}):\n'
            f'{", ".join(all_keys)}\n\n'
            f'You can retrieve this information later using `get_intermediate_results` with the same title.\n'
            f'Note: After storage, only the ID and summary of this result will be kept in the message history, not the full content.')


# not work for now
@mcp.tool(description='Retrieves previously saved tool results. Provide the title of the original call '
                      'you want to reference. If you don\'t remember the ID, call this function without parameters '
                      'to see a list of all stored results with their summaries. This tool helps you access important '
                      'information without having to repeat searches or data collection steps.')
def get_intermediate_results(title: str = None) -> str:
    global intermediate_results

    if not intermediate_results:
        return ("⚠️ No tool results have been stored yet. Use `store_intermediate_results` after "
                "important tool calls to save their outputs.")

    # If no title provided, show a list of all stored items with summaries
    if not title:
        response = f"📋 Available stored tool results ({len(intermediate_results)} items):\n\n"

        for k, v in intermediate_results.items():
            response += f"• Tool call ID: {k}\n  Summary: {v['summary']}\n\n"

        response += "To retrieve a specific result, call this function again with the desired title."
        return response

    # If title provided but not found
    if title not in intermediate_results:
        all_keys = list(intermediate_results.keys())
        return (f"⚠️ No tool result found with ID '{title}'. Available IDs are:\n"
                f"{', '.join(all_keys)}")

    # Return the full data for this specific request
    item = intermediate_results[title]
    return (f"📌 Retrieved tool result: {title}\n"
            f"📝 Summary: {item['summary']}\n\n"
            f"📄 Data:\n{item['data']}")


if __name__ == "__main__":
    mcp.run(transport="stdio")