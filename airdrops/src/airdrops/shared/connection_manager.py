import time
from typing import Dict, Any
from web3 import Web3

class ConnectionManager:
    def __init__(self, config: Dict[str, Any], web3_factory=None):
        self.config = config
        self.connections: Dict[str, Web3] = {}
        self.web3_factory = web3_factory or (lambda rpc_url: Web3(Web3.HTTPProvider(rpc_url)))

    def add_connection(self, network: str, web3: Web3):
        self.connections[network] = web3

    def get_web3(self, network: str, max_retries: int = 3) -> Web3:
        if network in self.connections and self.connections[network].is_connected():
            return self.connections[network]

        network_config = self.config["networks"].get(network)
        if not network_config:
            raise ValueError(f"Network configuration for {network} not found.")

        rpc_urls = [network_config["rpc_url"]] + network_config.get("fallback_rpcs", [])

        for attempt in range(max_retries):
            for rpc_url in rpc_urls:
                try:
                    web3 = self.web3_factory(rpc_url)
                    if web3.is_connected():
                        self.connections[network] = web3
                        print(f"Successfully connected to {network} via {rpc_url}")
                        return web3
                except Exception as e:
                    print(f"Connection attempt to {rpc_url} failed: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise ConnectionError(f"Failed to connect to {network} after {max_retries} attempts.")