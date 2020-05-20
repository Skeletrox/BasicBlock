from hashlib import sha256
import json
import time

class Block:

    def __init__(self, index, transactions, timestamp, previous_hash):
        """
            Constructor for the `Block` class
            :param index: Unique ID of the block
            :param transactions: A list of transactions
            :param timestamp: Time at which this block was generated
            :param previous_hash: The hash of the previous block of this chain
        """
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash

    
    def compute_hash(self):
        """
            Serialize this into a json string and then compute a hash from that string
        """
        block_string = json.dumps(self.__dict__, sort_keys=True) # Ensures consistency across runs
        return sha256(block_string.encode()).hexdigest()


class BlockChain:

    # set a proof-of-work difficulty
    difficulty = 2

    def __init__(self):
        """
            Constructor for the `Blockchain` class.
        """
        self.unconfirmed_transactions = [] # data yet to be "nonced" and added to blockchain
        self.chain = []
        self.create_genesis_block()

    
    def create_genesis_block(self):
        """
            The genesis block is the root block of a blockchain system. It contains
            dummy data that does not necessarily need to make sense
        """
        genesis_block = Block(0, [], time.time(), "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    
    @property
    def last_block(self):
        """
            A quick, apparently pythonic way to return the last block in the chain.
            The last block always exists; it is the genesis block in the edge case
        """
        return self.chain[-1]


    def proof_of_work(self, block):
        """
            Brute-force nonce creation in order to ensure satisfaction of difficulty criteria
            Getting this nonce is what constitutes mining of crypto
        """
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0'*BlockChain.difficulty): # for a difficulty of n, ensure n leading zeroes
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash


    def add_block(self, block, proof):
        """
            Adds the block to the chain after verification, which includes:
                -> Checking proof validity
                -> previous_hash is, indeed, the previous_hash
        """
        previous_hash = self.last_block.hash

        # Ensure that the previous hash is true
        if previous_hash != block.previous_hash:
            return False

        # Check if proof is valid
        if not BlockChain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True


    def is_valid_proof(self, block, block_hash):
        """
            Check if block_hash is valid hash of said block and satisfies the difficulty criterion
        """
        return (block_hash.startswith("0" * BlockChain.difficulty) and block_hash == block.compute_hash())


    def add_new_transaction(self, transaction):
        """
            Adds a new transaction to the list of unconfirmed transactions to be mined later
        """
        self.unconfirmed_transactions.append(transaction)


    def mine(self):
        """
            This is used to add pending transactions to the blockchain by adding them to the block and
            figuring out the proof of work.
        """
        if not self.unconfirmed_transactions: # Nothing to mine
            return None

        last_block = self.last_block
        new_block = Block(index = last_block.index + 1,
                          transactions = self.unconfirmed_transactions, # dump all unconfirmed transactions into this block
                          timestamp = time.time(),
                          previous_hash = last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)
        self.unconfirmed_transactions = [] # all unconfirmed transactions have been mined!
        return new_block.index


    def validate(self, chain):
        """
            A helper method to validate chain, passed as a list of dicts
        """
        previous_hash = "0"

        # Iterate through each block ensuring it works
        for block in chain:
            bl_hash = block.hash
            # remove hash and compute hash again to ensure that it's legit
            delattr(block, "hash")
            if not BlockChain.is_valid_proof(block, bl_hash) or previous_hash != block.previous_hash:
                return False

            block.hash, previous_hash = bl_hash, bl_hash

        return True