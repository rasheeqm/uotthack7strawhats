from typing import Literal
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState, END
from langgraph.types import Command
from pydantic import BaseModel, Field
import json
import os
import getpass
from langchain_openai import ChatOpenAI

# Initialize OpenAI API key
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

llm = ChatOpenAI(model="gpt-4", temperature=0)

# File handling functions
def extract_json_from_response(content: str) -> str:
    """Extract JSON from markdown code blocks or plain text"""
    if content.startswith('```json\n') and content.endswith('\n```'):
        return content[7:-4]
    elif content.startswith('```\n') and content.endswith('\n```'):
        return content[4:-4]
    return content

def ensure_file_exists(filename: str, default_content: dict = None):
    """Create file if it doesn't exist"""
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump(default_content or {}, f)

def safe_read_json(filename: str, default_content: dict = None):
    """Safely read JSON file with fallback to default content"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_content or {}

def safe_write_json(filename: str, content: dict):
    """Safely write content to JSON file"""
    with open(filename, 'w') as f:
        json.dump(content, f, indent=2)

# Initialize necessary files
def initialize_files():
    ensure_file_exists('agent1_output.json', {"items": [], "budget": 0})
    ensure_file_exists('item_prices.json', {"items": [], "total_price": 0, "budget": 0})

def load_ingredients_data():
    with open('data/ingredient_to_price_and_url.json', 'r') as f:
        return json.load(f)

# Grocery List Generator Agent
grocery_list_prompt = """You are a grocery list generator. Create a list of grocery items with quantities.
The quantities MUST include units (e.g., "2 lbs", "1 gallon", "500g", "3 pieces", etc).
The output must be valid JSON with this structure: 
{
    "items": [{"name": "item_name", "quantity": quantity}],
    "budget": budget_amount
}"""

grocery_list_agent = create_react_agent(
    llm,
    tools=[],
    state_modifier=grocery_list_prompt
)

def grocery_list_node(state: MessagesState) -> Command[Literal["price_checker"]]:
    result = grocery_list_agent.invoke(state)
    
    try:
        content = result["messages"][-1].content
        cleaned_content = extract_json_from_response(content)
        grocery_list = json.loads(cleaned_content)
        print("Parsed grocery list:", json.dumps(grocery_list, indent=2))
        safe_write_json('agent1_output.json', grocery_list)
        
    except Exception as e:
        print(f"Error in grocery list generation: {e}")
        return Command(update={"messages": result["messages"]}, goto="price_checker")
    
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content,
        name="grocery_list_generator"
    )
    
    return Command(
        update={"messages": result["messages"]},
        goto="price_checker"
    )

# Price Checker Tool
from langchain_core.tools import tool

@tool
def find_cheapest():
    """Read the latest grocery list and find prices for items"""
    try:
        print("Reading from agent1_output.json and ingredient data...")
        
        with open('agent1_output.json', 'r') as f:
            grocery_list = json.load(f)
        
        ingredients_data = load_ingredients_data()
        ingredients_dict = {item['name'].lower(): item 
                          for item in ingredients_data.get('ingredients', [])}
        
        results = []
        total_price = 0
        
        for item in grocery_list.get('items', []):
            item_name = item['name'].lower()
            
            if item_name in ingredients_dict:
                item_data = ingredients_dict[item_name]
                quantity = item['quantity']
                if isinstance(quantity, str):
                    numeric_part = ''.join(filter(str.isdigit, quantity))
                    quantity = float(numeric_part) if numeric_part else 1
                
                item_total = item_data['price']
                
                results.append({
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'price_per_unit': item_data['price'],
                    'total_price': item_total,
                    'url': item_data['url']
                })
                total_price += item_total
            else:
                results.append({
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'price_per_unit': None,
                    'total_price': None,
                    'url': None
                })
        
        output_data = {
            'items': results,
            'total_price': total_price,
            'budget': grocery_list.get('budget', 0)
        }
        
        safe_write_json('item_prices.json', output_data)
        return output_data
    except Exception as e:
        print(f"Error in find_cheapest: {str(e)}")
        return {"error": str(e)}

# Price Checker Agent
price_checker_agent = create_react_agent(
    llm,
    tools=[find_cheapest],
    state_modifier="You check prices and suggest substitutions if over budget."
)

def price_checker_node(state: MessagesState) -> MessagesState:
    result = price_checker_agent.invoke(state)
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content,
        name="price_checker"
    )
    return result

def route_by_budget(state: MessagesState) -> Literal["grocery_list_generator", "end"]:
    """Route based on budget comparison"""
    try:
        prices_data = safe_read_json('item_prices.json')
        total_price = prices_data.get('total_price', 0)
        budget = prices_data.get('budget', 0)
        budget_threshold = budget * 1.10
        
        if total_price > budget_threshold:
            # Find most expensive item for suggestion
            items = prices_data.get('items', [])
            valid_items = [item for item in items if item.get('price_per_unit') is not None]
            if valid_items:
                most_expensive = max(valid_items, key=lambda x: x['price_per_unit'])
                state.messages.append(
                    HumanMessage(
                        content=f"The total price ${total_price:.2f} is over budget threshold "
                               f"(${budget_threshold:.2f}). Please replace {most_expensive['name']} "
                               f"(${most_expensive['price_per_unit']:.2f}/unit) with a cheaper alternative.",
                        name="budget_router"
                    )
                )
            return "grocery_list_generator"
        return "end"
    except Exception as e:
        print(f"Error in route_by_budget: {e}")
        return "end"

# Define the Graph
from langgraph.graph import StateGraph, START

workflow = StateGraph(MessagesState)

# Add nodes
workflow.add_node("grocery_list_generator", grocery_list_node)
workflow.add_node("price_checker", price_checker_node)

# Add edges with conditional routing
workflow.add_edge(START, "grocery_list_generator")
workflow.add_edge("grocery_list_generator", "price_checker")
workflow.add_conditional_edges(
    "price_checker",
    route_by_budget,
    {
        "grocery_list_generator": "grocery_list_generator",
        "end": END
    }
)

# Compile the graph
graph = workflow.compile()

def run_grocery_workflow(budget: float):
    """Run the grocery list workflow with specified budget"""
    initialize_files()
    
    initial_state = {
        "messages": [
            HumanMessage(
                content=f"Generate a grocery list for a single person for one week based on a budget of ${budget}."
            )
        ]
    }
    
    events = graph.stream(
        initial_state,
        {"recursion_limit": 150},
    )
    
    for event in events:
        step_type = event.get("type", "")
        if step_type == "start":
            print("\n=== Starting New Workflow ===")
        elif step_type == "end":
            print("\n=== Workflow Complete ===")
            try:
                final_prices = safe_read_json('item_prices.json')
                print("\nFinal Results:")
                print(f"Total Price: ${final_prices.get('total_price', 0):.2f}")
                print(f"Budget: ${final_prices.get('budget', 0):.2f}")
            except Exception as e:
                print(f"Error reading final results: {e}")
        else:
            print("\n--- Step Details ---")
            if "messages" in event:
                print("\nMessages:")
                for msg in event["messages"][-1:]:
                    print(f"{msg.name if hasattr(msg, 'name') else 'Unknown'}: {msg.content[:200]}...")
            for key, value in event.items():
                if key != "messages":
                    print(f"{key}: {value}")
        print("-" * 50)

if __name__ == "__main__":
    run_grocery_workflow(100.0)