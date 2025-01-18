from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from langchain.globals import set_debug

set_debug(True)
import getpass
import os

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")
# Define structured output schema
class GroceryList(BaseModel):
    items: list[str] = Field(..., description="List of grocery items with quantities")
    notes: str = Field(..., description="Any notes about the grocery list")

# Create the output parser
# parser = StrOutputParser.from_pydantic(GroceryList)

# Define the prompt template
prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a grocery list generator. Provide a structured list of items and quantities."),
        ("human", "Generate a grocery list for a single person for one week based on a budget of {budget}.")
    ]
)

# Create the chain
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
def agent1_chain(budget):
    formatted_prompt = prompt_template.format_prompt(budget=budget)
    messages = formatted_prompt.to_messages()
    response = model.invoke(messages)
    return {"role": "assistant", "content": response.content}


# ------------------------------
# Agent2: React Agent for Price Checking
# ------------------------------
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Define a tool to find the cheapest price for grocery items
@tool
def find_cheapest(item: str):
    """Give the item name it returns the price for the items"""
    prices = {"Rice": 3.0, "Chicken": 5.5, "Vegetables": 7.0}
    return {"item": item, "price": prices.get(item, 999.99), "found": item in prices}

tools = [find_cheapest]

# Define the prompt for Agent2
agent2_prompt = (
    "You are a price checker. Take the grocery list and check the total cost.\n"
    "If the total price exceeds the budget by more than $5, suggest substitutions."
)

# Create the Agent2 React Agent
agent2 = create_react_agent(model=model, tools=tools, state_modifier=agent2_prompt)

from langgraph.graph import StateGraph, START, END

class State(BaseModel):
    messages: list[dict] = Field(default_factory=list)
    budget: float = Field(..., description="User's budget for the grocery list")

# Graph construction
builder = StateGraph(State)

# Define logic to check budget and decide flow
def check_budget_and_loop(state: State):
    # Check Agent2's output for the total price
    for message in reversed(state.messages):
        if "total_price" in message.get("content", {}):
            total_price = message["content"].get("total_price")
            budget = state.budget
            if total_price > budget + 5:
                return "agent1"  # Loop back to Agent1 for substitution
            return END
    return END

# Add nodes and edges
builder.add_node("agent1", lambda state: {"messages": state.messages + [agent1_chain(state.budget)]})
builder.add_node("agent2", lambda state: {"messages": state.messages + [agent2.invoke({"messages": state.messages})]})
builder.add_edge(START, "agent1")
builder.add_edge("agent1", "agent2")
builder.add_conditional_edges("agent2", check_budget_and_loop, ["agent1", END])

# Compile the graph
graph = builder.compile()

# Example Usage
def run_system(budget: float):
    initial_state = State(messages=[], budget=budget)
    output_events = graph.stream(initial_state, stream_mode="values")
    final_state = None

    for event in output_events:
        final_state = event

    return final_state

# Example run
budget = 50.0
final_state = run_system(budget)

# Print final messages
if hasattr(final_state, "messages"):
    for message in final_state.messages:
        print(message["role"].upper(), ":", message["content"])
else:
    print("No messages in final state.")
