# chapter-02/ooda_agent.py
# A complete agent that demonstrates Observe-Orient-Decide-Act

from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

# Step 1: Define tools (the "Act" phase)
@tool
def get_order_status(order_id: str) -> str:
    """Get the current status of an order from the database."""
    # Simulated database
    orders = {
        "ORD-123": {"status": "shipped", "carrier": "UPS", "tracking": "1Z999AA10123456784"},
        "ORD-456": {"status": "processing", "estimated_ship": "2026-04-05"},
        "ORD-789": {"status": "shipped", "carrier": "FedEx", "tracking": "789456123012"}
    }
    return str(orders.get(order_id, {"status": "not found"}))

@tool
def check_carrier_status(tracking_number: str, carrier: str) -> str:
    """Check the current status of a shipment with the carrier."""
    # Simulated carrier API
    if carrier == "UPS" and tracking_number == "1Z999AA10123456784":
        return "Weather delay in Louisville. New ETA: March 20"
    return "In transit. On time."

# Step 2: Create the agent (observe → orient → decide → act)
llm = ChatOpenAI(model="gpt-4", temperature=0)

prompt = PromptTemplate.from_template("""
You are a customer support agent. Your goal is to help customers find their orders.

You have these tools:
- get_order_status: Check the database for order status
- check_carrier_status: Check with the carrier for delays

Follow this process for EVERY request:
1. First, use get_order_status to find the order
2. If the status shows "shipped" but more than 3 days have passed, use check_carrier_status
3. Provide a helpful answer that addresses any issues

Customer question: {input}

{agent_scratchpad}
""")

agent = create_react_agent(llm, [get_order_status, check_carrier_status], prompt)
executor = AgentExecutor(agent=agent, tools=[get_order_status, check_carrier_status], verbose=True)

# Step 3: Run the agent
result = executor.invoke({
    "input": "Where is my order ORD-123? It was supposed to be here yesterday."
})
print(result["output"])
