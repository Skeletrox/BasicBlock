from flask import Flask, request
import requests
import time
import json
from block import BlockChain, Block

# Initialize flask application
app = Flask(__name__)


# Initialize blockchain
blockchain = BlockChain()


# Create peers that communicate with one another to create a true decentralized blockchain
peers = set()


# new POST endpoint to create a new transaction
@app.route('/new', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()
    req_fields = ["author", "content"]

    for field in req_fields:
        if not tx_data.get(field):
            return "Invalid trannsaction data", 400

    tx_data["timestamp"] = time.time()

    blockchain.add_new_transaction(tx_data)
    return "Success", 201


# returns the blockchain
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)

    return json.dumps({
        "peers": list(peers),
        "length": len(chain_data),
        "chain": chain_data
    })


# endpoint to begin mining
# Any client calling this method should remember that this HTTP session can take a shit ton of time
@app.route('/mine', methods=['GET'])
def mine_unconf_tx():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"

    else:
        chain_length = len(blockchain.chain)
        consensus()

        if chain_length == len(blockchain.chain):
            # Announce the recently mined block to the entire network
            # in other cases, it'd just be replaced by the already mined block (which shouldn't technically happen)
            announce_new_block(blockchain.last_block)

    return "Block #{} mined".format(result)


# Get the unconfirmed transactions
@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)


# Register a new peer
@app.route('/register_node', methods=['POST'])
def register_peer():
    # Get address of peer
    address = request.get_json().get("node_address", None)
    if not address:
        return "Invalid data", 400

    # add this node to the peer list
    peers.add(address)

    # Return the blockchain to this node to enable syncing
    return get_chain()


# Register and sync this node with a remote node
@app.route('/register_with', methods=['POST'])
def register_existing():
    """
        Internally calls register_node to register and sync data
    """
    address = request.get_json().get("node_address", None)
    if not address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {"Content-Type": "application/json"}

    # manufacture a request to register with remote node and obtain information
    response = requests.post(address + "/register_node", data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        # Yep, everything works, here's our blockchain
        global blockchain
        global peers
        # update them global variables
        chain_dump = response.json().get("chain", None)
        new_peers = response.json().get("peers", None)
        if not chain_dump or not new_peers:
            raise Exception("No chain/peers in response: ", json.dumps(response.json()))
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(new_peers)
        return "Registration successful", 200

    else:
        # Just transmit whatever error was thrown
        return response.content, response.status_code


# Endpoint to add a block mined by someone else
@app.route("/add", methods=["POST"])
def add_block():
    block_data = request.get_json()
    block = Block(
        block_data["index"],
        block_data["transactions"],
        block_data["timestamp"],
        block_data["previous_hash"]
    )
    proof = block_data["hash"]
    added = blockchain.add_block(block, proof)

    if not added:
        return "Block was discarded by this node", 400

    return "Block added to chain", 201


def create_chain_from_dump(chain_dump):
    """
        Uses a chain dump to (re)create a BlockChain instance
    """
    chain = BlockChain()
    for idx, block_data in enumerate(chain_dump):
        block = Block(
            block_data["index"],
            block_data["transactions"],
            block_data["timestamp"],
            block_data["previous_hash"]
        )
        proof = block_data["hash"]
        if idx > 0:
            # not the genesis block, so pls verify
            added = chain.add_block(block, proof)
            if not added:
                raise Exception("Tampered blockchain dump!")
        else:
            # genesis block, just add
            chain.chain.append(block)

    return chain


def consensus():
    """
        Simple consensus algorithm. If longer valid chain is found, replace.
    """
    global blockchain

    longest_chain = None
    curr_len = len(blockchain.chain)

    for node in peers:
        response = requests.get("{}/chain".format(node))
        length = response.json().get("length", -1)
        if length > curr_len:
            # Longer chain, check validity
            chain = response.json().get("chain", None)
            if chain is not None and blockchain.validate(chain):
                curr_len = length
                longest_chain = chain


    if longest_chain:
        blockchain = create_chain_from_dump(longest_chain)
        return True

    return False


def announce_new_block(block):
    """
        Upon mining a nwew block, broadcast
    """
    for peer in peers:
        url = "{}/add_block".format(peer)
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True))