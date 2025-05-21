import json

def generate_gost_config(transits: list, servers_map: dict) -> dict:
    """
    Generates a GOST v2.x JSON configuration from a list of Transit objects.
    The configuration is for Server A in the transit definition.

    Args:
        transits: A list of Transits SQLAlchemy model objects.
        servers_map: A dictionary mapping server IDs to Server SQLAlchemy model objects
                     for easy lookup of Server A and Server B details.

    Returns:
        A Python dictionary representing the GOST JSON configuration.
    """
    config = {
        "Debug": True, 
        "Retries": 0,
        "Routes": []
    }

    if not transits:
        return config

    for transit_item in transits: # Renamed to avoid conflict with transit module if any
        # Example: transit_item.status could be 'active', 'pending', 'inactive', 'error'
        # This function assumes that filtering of transits (e.g., only 'active' ones)
        # is done by the caller if needed. Here, we process all passed transits.

        server_a = servers_map.get(transit_item.server_a_id)
        server_b = servers_map.get(transit_item.server_b_id)

        if not server_a:
            print(f"Warning: Could not find Server A (ID: {transit_item.server_a_id}) for Transit ID {transit_item.id} ('{transit_item.name}'). Skipping this transit.")
            continue
        # For direct TCP/UDP forward, server_b is not strictly needed for GOST config on Server A,
        # but the transit rule itself requires it, so we check.
        if not server_b:
            print(f"Warning: Could not find Server B (ID: {transit_item.server_b_id}) for Transit ID {transit_item.id} ('{transit_item.name}'). Skipping this transit.")
            continue


        listen_port_a = transit_item.server_a_listen_port
        
        current_route = {
            "Retries": 0, 
            "ServeNodes": [],
        }

        db_protocol = transit_item.encryption_protocol.lower()

        if db_protocol in ['tcp', 'udp']: 
            # Direct forwarding from Server A to final destination.
            # Server B's details (IP, connect_port) are not used in Server A's GOST config for this type.
            # GOST syntax for direct forward: <tcp|udp>://:LISTEN_PORT/DEST_IP:DEST_PORT
            current_route["ServeNodes"].append(f"tcp://:{listen_port_a}/{transit_item.destination_ip}:{transit_item.destination_port}")
            current_route["ServeNodes"].append(f"udp://:{listen_port_a}/{transit_item.destination_ip}:{transit_item.destination_port}")
            # No ChainNodes for direct forwarding from Server A.
        
        elif db_protocol in ['ws', 'wss', 'relay+tls']:
            # Server A listens (e.g., on TCP/UDP), then relays to Server B using the specified protocol.
            # Server B is then responsible for forwarding to the final destination.
            
            # Server A's listeners for incoming traffic for this transit
            current_route["ServeNodes"].append(f"tcp://:{listen_port_a}") 
            current_route["ServeNodes"].append(f"udp://:{listen_port_a}") # gost.sh often includes both

            chain_protocol_map = {
                'ws': 'relay+ws',
                'wss': 'relay+wss',
                'relay+tls': 'relay+tls'
            }
            gost_chain_protocol = chain_protocol_map[db_protocol]
            
            # ChainNodes define where Server A forwards the traffic to (i.e., Server B)
            # GOST syntax for relay: relay+<protocol>://SERVER_B_IP:SERVER_B_CONNECT_PORT
            current_route["ChainNodes"] = [
                f"{gost_chain_protocol}://{server_b.ip_address}:{transit_item.server_b_connect_port}"
            ]
            # Considerations for TLS/WSS if Server B uses custom certs / SNI:
            # If server_b.ip_address is a hostname, GOST uses it for SNI.
            # If Server B's cert is not trusted by system CAs, GOST might fail TLS handshake.
            # Options: use ` insecure=true` in ChainNode URL query if self-signed cert on Server B.
            # e.g., `relay+wss://{server_b.ip_address}:{transit_item.server_b_connect_port}?insecure=true`
            # This is not currently in the UI but could be an advanced option.
        else:
            print(f"Warning: Unknown or unsupported protocol '{transit_item.encryption_protocol}' for Transit ID {transit_item.id} ('{transit_item.name}'). Skipping.")
            continue
        
        config["Routes"].append(current_route)

    return config

if __name__ == '__main__':
    # Dummy data for testing
    class Server:
        def __init__(self, id, name, ip_address):
            self.id = id
            self.name = name
            self.ip_address = ip_address

    class Transit:
        def __init__(self, id, name, server_a_id, server_a_listen_port, 
                     server_b_id, server_b_connect_port, encryption_protocol, 
                     destination_ip, destination_port, status='active'):
            self.id = id
            self.name = name
            self.server_a_id = server_a_id
            self.server_a_listen_port = server_a_listen_port
            self.server_b_id = server_b_id
            self.server_b_connect_port = server_b_connect_port
            self.encryption_protocol = encryption_protocol
            self.destination_ip = destination_ip
            self.destination_port = destination_port
            self.status = status

    servers_data_map = {
        1: Server(1, "ServerA_VPS", "1.1.1.1"),
        2: Server(2, "ServerB_VPS", "2.2.2.2"),
        3: Server(3, "ServerC_Local", "3.3.3.3"), # Used as a destination, not a relay point in these tests
    }

    transits_list = [
        Transit(1, "WS_Relay_Test", 
                server_a_id=1, server_a_listen_port=8080,
                server_b_id=2, server_b_connect_port=9090,
                encryption_protocol="ws",
                destination_ip="10.0.0.1", destination_port=80),
        Transit(2, "Direct_TCP_Forward",
                server_a_id=1, server_a_listen_port=8081,
                server_b_id=2, # Server B is arbitrary for direct forward config on Server A
                server_b_connect_port=0, 
                encryption_protocol="tcp",
                destination_ip="192.168.1.100", destination_port=443),
        Transit(3, "WSS_Relay_Secure", 
                server_a_id=1, server_a_listen_port=8082,
                server_b_id=2, server_b_connect_port=9091,
                encryption_protocol="wss",
                destination_ip="10.0.0.2", destination_port=8080),
        Transit(4, "TLS_Relay",
                server_a_id=1, server_a_listen_port=8083,
                server_b_id=2, server_b_connect_port=9092,
                encryption_protocol="relay+tls",
                destination_ip="10.0.0.3", destination_port=5000),
        Transit(5, "Direct_UDP_Forward", # Another direct forward example
                server_a_id=1, server_a_listen_port=7070,
                server_b_id=2,
                server_b_connect_port=0,
                encryption_protocol="udp",
                destination_ip="192.168.1.101", destination_port=53),
        Transit(6, "Unsupported_Proto_Relay", # Test unsupported protocol
                server_a_id=1, server_a_listen_port=6060,
                server_b_id=2, server_b_connect_port=9093,
                encryption_protocol="ssh", # This is not one of the GOST relay protocols we map
                destination_ip="10.0.0.4", destination_port=22),
    ]
    
    print("--- Generating config for multiple transits ---")
    generated_json_config = generate_gost_config(transits_list, servers_data_map)
    print(json.dumps(generated_json_config, indent=4))

    print("\n--- Generating config with no transits ---")
    generated_json_config_empty = generate_gost_config([], servers_data_map)
    print(json.dumps(generated_json_config_empty, indent=4))

    print("\n--- Generating config with a transit that has a missing Server B ---")
    transits_missing_server_b = [
         Transit(7, "Missing_ServerB_Relay", 
                server_a_id=1, server_a_listen_port=8888,
                server_b_id=99, # Server 99 doesn't exist in servers_data_map
                server_b_connect_port=9090, 
                encryption_protocol="ws",
                destination_ip="10.0.0.1", destination_port=80)
    ]
    generated_json_config_missing_b = generate_gost_config(transits_missing_server_b, servers_data_map)
    print(json.dumps(generated_json_config_missing_b, indent=4))

    print("\n--- Generating config with a transit that has a missing Server A ---")
    transits_missing_server_a = [
         Transit(8, "Missing_ServerA_Relay", 
                server_a_id=88, # Server 88 doesn't exist
                server_a_listen_port=7777,
                server_b_id=2, 
                server_b_connect_port=9090, 
                encryption_protocol="wss",
                destination_ip="10.0.0.1", destination_port=80)
    ]
    generated_json_config_missing_a = generate_gost_config(transits_missing_server_a, servers_data_map)
    print(json.dumps(generated_json_config_missing_a, indent=4))
