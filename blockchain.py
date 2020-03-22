import hashlib
import json

from textwrap import dedent
from time import time
from uuid import uuid4
from urllib.parse import urlparse

from flask import Flask, jsonify, request

class Blockchain(object):

    # Initialize the blockchain
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        self.nodes = set()

        # create the genesis block
        self.new_block(previous_hash=1, proof=100)

    # Register a new node into the network
    def register_node(self, address):

        paresed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    # Add a new block into the blockchain
    def new_block(self, proof, previous_hash=None):

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        # reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    # Create a new transaction
    def new_transaction(self, sender, recipient, amount):

        # append the transaction
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })

        # return the nect block to be mined
        return self.last_block['index'] + 1

    # Find a number p' such that hash(pp') contains 4 leading zeores
    # p is the previous proof, p' is the new proof
    def proof_of_work(self, last_proof):

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    # Check if the current blockchain is valid or not
    def valid_chain(self, chain):

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")

            # check if the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # cehck if PoW of the block is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):

        neighbors = self.nodes
        new_chain = None

        # set max_length to the current chain, replace if longer chain found
        max_length = len(self.chain)

        # iterate through each node
        for node in neighbors:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # check if a longer chain exists and is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    max_chain = chain

        # replace the current chain if a longer chain is found
        if new_chain:
            self.chain = new_chain
            return True

        return False

    @staticmethod
    def valid_proof(last_proof, proof):

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    @staticmethod
    def hash(block):

        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]


# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

# GET endpoint for mining
@app.route('/mine', methods=['GET'])
def mine():

    # run PoW algorithm to get the next proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # give a rewardto sender '0' signifying that the block has been mined
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # create a new block and add it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New block created",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

# POST endpoint for creating a new transaction
@app.route('/transactions/new', methods=['POST'])
def new_transaction():

    return "Adding a new transaction"
    values = request.get_json()

    # check that all the required fields are present in the request
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # create a new transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Adding the transaction to block {index}'}
    return jsonify(response), 201

# GET endpoint to return the current chain
@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

# POST endpoint to register a new node in the network
@app.route('/nodes/register', methods=['POST'])
def register_nodes():

    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return "Error: Invalid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': "New node added"
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

# GET endpoint to resolve the current blockchain
@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Chain was not replaced',
            'chain': blockchain.chain
        }

    return jsonify(response), 200
