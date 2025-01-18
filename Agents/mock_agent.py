import json
from typing import List, TypedDict, Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from IPython.display import Image, display
import matplotlib.pyplot as plt
# ---------------------------------
# Static User Profile Schema
# ---------------------------------
class UserProfile(BaseModel):
    age: int = Field(..., description="Age in years")
    sex: str = Field(..., description="Sex of the user (male, female, etc.)")
    height_cm: float = Field(..., description="Height in centimeters")
    weight_kg: float = Field(..., description="Weight in kilograms")
    budget: float = Field(..., description="Weekly grocery budget in local currency")

# ---------------------------------
# Grocery List Schema
# ---------------------------------
class GroceryList(BaseModel):
    items: List[str] = Field(
        ..., description="List of grocery items for one person, 1 week. Stay under user budget."
    )
    notes: str = Field(
        default="", description="Any notes or assumptions in generating the grocery list."
    )

# ---------------------------------
# Priced List Schema
# ---------------------------------
class PricedItem(BaseModel):
    name: str
    price: float
    found: bool = True

class PricedList(BaseModel):
    priced_items: List[PricedItem] = Field(
        ..., description="Priced version of the grocery list items."
    )
    total_price: float = Field(..., description="Sum of the priced items that are found.")
    under_budget: bool = Field(
        ..., description="Whether or not total_price fits under the user's budget."
    )
    message_to_agent1: str = Field(
        default="", description="Message to Agent1 if adjustments are needed."
    )

# ---------------------------------
# Mocked Agent1 Responder with Static Data
# ---------------------------------
class MockedAgent1Responder:
    def respond(self, state: dict, message: str = "Replace expensive items"):
        print("Agent1 received message to modify grocery list:", message)
        # Modify the grocery list based on the message
        grocery_list = GroceryList(
            items=[
                "rice (2kg)",
                "lentils (1kg)",  # Replace beans with cheaper lentils
                "chicken (1kg)",   # Reduce chicken quantity
                "vegetables (variety - 2kg)",  # Reduce vegetable quantity
                "milk (1L)",       # Reduce milk quantity
                "bread (1 loaf)",
                "eggs (6-pack)"     # Reduce egg quantity
            ],
            notes="Modified to fit within a tighter budget."
        )
        print("Agent1 generated grocery list:", grocery_list.dict())
        # Append static response to state
        state["messages"].append({"type": "ai", "content": json.dumps(grocery_list.dict())})
        return state

# ---------------------------------
# Mocked Agent2 Responder with Static Data
# ---------------------------------
class MockedAgent2Responder:
    def respond(self, state: dict, user_budget: float):
        print("Agent2 received grocery list to price out.")
        # Simulate pricing the modified grocery list
        priced_list = PricedList(
            priced_items=[
                PricedItem(name="rice (2kg)", price=5.0),
                PricedItem(name="lentils (1kg)", price=2.5),
                PricedItem(name="chicken (1kg)", price=8.0),
                PricedItem(name="vegetables (2kg)", price=6.0),
                PricedItem(name="milk (1L)", price=2.0),
                PricedItem(name="bread (1 loaf)", price=3.0),
                PricedItem(name="eggs (6-pack)", price=2.0),
            ],
            total_price=28.5,
            under_budget=user_budget - 28.5 >= 5.0,  # Check if it's within $5 of the budget
            message_to_agent1="Replace expensive items" if user_budget - 28.5 < 5.0 else ""
        )
        print("Agent2 priced list:", priced_list.dict())
        # Append static response to state
        state["messages"].append({"type": "ai", "content": json.dumps(priced_list.dict())})
        return state

# ---------------------------------
# Tool: Total Cost Checker
# ---------------------------------
def total_cost(state: dict, user_budget: float):
    print("Total Cost Checker invoked.")
    for msg in reversed(state["messages"]):
        if isinstance(msg, dict) and "PricedList" in msg.get("content", ""):
            priced_list = json.loads(msg["content"])
            total = priced_list["total_price"]
            print(f"Total cost: {total}, Budget + $5: {user_budget + 5.0}")
            if total > user_budget + 5.0:
                print("Total cost exceeds the budget + $5. Routing to Agent1 for modifications.")
                state["next_node"] = "agent1"
            else:
                print("Total cost is within budget. Ending process.")
                state["next_node"] = END
            return state
    print("No valid PricedList found. Routing to Agent1 by default.")
    state["next_node"] = "agent1"
    return state


# ---------------------------------
# Mocked Graph Construction
# ---------------------------------
class State(TypedDict):
    messages: Annotated[list, add_messages]

mocked_builder = StateGraph(State)

mocked_builder.add_node("agent1", lambda state: MockedAgent1Responder().respond(state))
mocked_builder.add_node("agent2", lambda state: MockedAgent2Responder().respond(state, user_budget=50.0))
mocked_builder.add_node("total_cost", lambda state: total_cost(state, user_budget=50.0))

# Add edges
mocked_builder.add_edge(START, "agent1")
mocked_builder.add_edge("agent1", "agent2")
mocked_builder.add_edge("agent2", "total_cost")
mocked_builder.add_conditional_edges(
    "total_cost",
    lambda state: state["next_node"],  # Use next_node set in total_cost
    ["agent1", END]
)

mocked_builder.add_edge("total_cost", END)

mocked_graph = mocked_builder.compile()

# ---------------------------------
# Run Example with Mocked Responses and Static Data
# ---------------------------------
def run_mocked_agentic_system(user_profile: UserProfile):
    # Initial user message
    user_msg = {
        "type": "user",
        "content": (
            f"User Profile:\nAge={user_profile.age}, "
            f"Sex={user_profile.sex}, Height={user_profile.height_cm}cm, "
            f"Weight={user_profile.weight_kg}kg, Budget=${user_profile.budget:.2f}"
        )
    }
    print("Initial user profile:", user_msg["content"])
    # Initializing state
    state = {"messages": [user_msg]}
    output_events = mocked_graph.stream(state, stream_mode="values")
    final_state = None
    for evt in output_events:
        final_state = evt
    return final_state

# Plot the graph
from IPython.display import Image
if __name__ == "__main__":
    # Static user profile
    profile = UserProfile(
        age=30,
        sex="male",
        height_cm=175,
        weight_kg=70,
        budget=50.0  # Weekly grocery budget
    )
    # Run the system
    result = run_mocked_agentic_system(profile)

    # Save and display graph
    print("Generating and saving the graph...")
    graph_path = "graph.png"
    png = mocked_graph.get_graph(xray=True).draw_mermaid_png()
    with open(graph_path, "wb") as f:
        f.write(png)
    print(f"Graph saved as {graph_path}")
    img = plt.imread(graph_path)
    plt.imshow(img)
    plt.axis('off')
    plt.show()

    # Print final messages
    print("\nFINAL STATE MESSAGES\n")
    for m in result["messages"]:
        if isinstance(m, dict) and m.get("type") == "ai":
            print("AI:", json.loads(m["content"]))
        elif isinstance(m, dict) and m.get("type") == "user":
            print("USER:", m["content"])
        else:
            print("OTHER:", m)
