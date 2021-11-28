from coin.run_node import run_node
from queue import Queue
from coin.node_context import NodeContext
from coin.node_state import StartupState

if __name__ == "__main__":
    run_node(NodeContext(node_id="a"), Queue(), Queue(), Queue(), INIT_STARTUP_STATE=StartupState.SYNCED)  # type: ignore
