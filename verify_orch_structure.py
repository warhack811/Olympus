import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from core_v2.orchestrator.graph import create_graph
    
    print("Attempting to compile graph...")
    graph = create_graph()
    print("Graph compiled successfully!")
    
    print("Graph structure:", graph)
    
except ImportError as e:
    print(f"ImportError: {e}")
    print("Please ensure dependencies are installed: pip install -r requirements.txt")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
