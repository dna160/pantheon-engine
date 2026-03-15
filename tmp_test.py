import os
import json
from dotenv import load_dotenv

load_dotenv()

from main import node1_intake_and_query, node2_generate_snapshot

def test():
    print("Starting Node 1 Query...")
    agents = node1_intake_and_query.local(target_demographic="Urban Millennial", limit=1)
    if not agents:
        print("No agents found")
        return
        
    print(f"Agent found. Proceeding to Node 2 Snapshot...")
    result = node2_generate_snapshot.local(agents[0])
    
    snapshot = result.get("runtime_snapshot", {})
    
    print("\n============== EXTRACTED OUTPUT ==============\n")
    print("Emotional State:", snapshot.get("current_emotional_state"))
    print("Financial Pressure:", snapshot.get("current_financial_pressure"))
    print("\n==============================================")

if __name__ == "__main__":
    test()
