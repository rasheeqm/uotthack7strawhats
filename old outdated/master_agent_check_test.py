from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from langchain.globals import set_debug
import json
set_debug(True)
import getpass
import os

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")
# Define structured output schema
class GroceryList(BaseModel):
    items: list[str] = Field(..., description="List of grocery items with quantities")
    notes: str = Field(..., description="Any notes about the grocery list")


# Load ingredients data
def load_ingredients_data():
    with open('data/ingredient_to_price_and_url.json', 'r') as f:
        return json.load(f)

# Save prices to file
def save_prices(prices):
    with open('item_prices.json', 'w') as f:
        json.dump(prices, f, indent=2)  # Correct usage of json.dump

# Create the output parser
# parser = StrOutputParser.from_pydantic(GroceryList)

# Define the prompt template
prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a grocery list generator. Please create a list of grocery items along with their respective quantities. Ensure that the output strictly follows the JSON format below. Do not include any additional text outside of the JSON structure. The JSON will look like this: \"items\": [\"name\": \"item_to_buy\", \"quantity\": quantity_to_buy], \"budget\": budget."),
        ("human", "Generate a grocery list for a single person for one week based on a budget of $budget.")
    ]
)


# Create the chain
model = ChatOpenAI(model="gpt-4o", temperature=0)
def agent1_chain(budget):
    formatted_prompt = prompt_template.format_prompt(budget=budget)
    messages = formatted_prompt.to_messages()
    response = model.invoke(messages)

    try:
        # Clean up the response to make it valid JSON
        print(response.content)
        raw_response = response.content.strip()

        # Add budget to the cleaned-up JSON
        response_dict = json.loads(raw_response)
        response_dict["budget"] = budget

        # Validate if required keys are in the response
        if "items" not in response_dict:
            raise ValueError("Response is missing required fields: 'items'.")

        # Save the response to a JSON file
        with open('agent1_output.json', 'w') as f:
            json.dump(response_dict, f, indent=2)

        # Convert response_dict to a JSON string
        response_str = json.dumps(response_dict)
        return {"role": "assistant", "content": response_str}

    except json.JSONDecodeError:
        return {"role": "assistant", "content": json.dumps({"error": "Failed to decode JSON from response."})}

    except Exception as e:
        return {"role": "assistant", "content": json.dumps({"error": str(e)})}
# ------------------------------
# Agent2: React Agent for Price Checking
# ------------------------------
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Define a tool to find the cheapest price for grocery items
# Define a tool to find the cheapest price for grocery items
@tool
def find_cheapest():
    """Read the latest grocery list and find prices for items"""
    try:
        # Load the latest agent1 output
        with open('agent1_output.json', 'r') as f:
            grocery_list = json.load(f)
        
        # Load ingredients data
        ingredients_data = load_ingredients_data()
        ingredients_dict = {item['name'].lower(): item for item in ingredients_data['ingredients']}
        
        # Store results
        results = []
        total_price = 0
        
        # Process each item
        for item in grocery_list['items']:
            item_name = item['name'].lower()  # Extract item name
            if item_name in ingredients_dict:
                item_data = ingredients_dict[item_name]
                results.append({
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'price_per_unit': item_data['price'],
                    'total_price': item_data['price'] * item['quantity'],
                    'url': item_data['url']
                })
                total_price += item_data['price'] * item['quantity']
            else:
                results.append({
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'price_per_unit': None,
                    'total_price': None,
                    'url': None
                })
        
        # Save results
        output_data = {
            'items': results,
            'total_price': total_price,
            'budget': grocery_list['budget']
        }
        save_prices(output_data)  # Ensure this writes correctly
        
        print("Prices saved successfully:", output_data)  # Debug print
        return output_data
    except Exception as e:
        print(f"Error in find_cheapest: {e}")
        return {"error": str(e)}



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
    try:
        with open('item_prices.json', 'r') as f:
            prices_data = json.load(f)
            
        total_price = prices_data['total_price']
        budget = state.budget
        
        if total_price > budget + 5:
            # Find most expensive item
            most_expensive = max(prices_data['items'], key=lambda x: x['price'] if x['price'] is not None else 0)
            
            # Add context about the expensive item to Agent1
            state.messages.append({
                "role": "system",
                "content": f"The current list is over budget. Please substitute {most_expensive['name']} (${most_expensive['price']}) with a cheaper alternative."
            })
            return "agent1"
            
        return END
    except Exception as e:
        print(f"Error in budget check: {e}")
        return END

# Add nodes and edges
builder.add_node("agent1", lambda state: {"messages": state.messages + [agent1_chain(state.budget)]})
builder.add_node("agent2", lambda state: {"messages": state.messages + [agent2.invoke({"messages": state.messages})]})
builder.add_edge(START, "agent1")
builder.add_edge("agent1", "agent2")
builder.add_edge(START, "agent1")
builder.add_conditional_edges("agent2", check_budget_and_loop, ["agent1", END])

# Compile the graph
graph = builder.compile()


budget = 50.0
# final_state = run_system(budget)

events = graph.stream(
    {
        "messages": [
            (
                "user",
                "First, get the UK's GDP over the past 5 years, then make a line chart of it. "
                "Once you make the chart, finish.",
            )
        ],
    },
    # Maximum number of steps to take in the graph
    {"recursion_limit": 150},
)
for s in events:
    print(s)
    print("----")



# # Print final messages
# if hasattr(final_state, "messages"):
#     for message in final_state.messages:
#         print(message["role"].upper(), ":", message["content"])
# else:
#     print("No messages in final state.")
