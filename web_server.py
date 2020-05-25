import datetime
import json

import requests
from flask import render_template, redirect, request, Flask, jsonify

# The node this web server interfaces to
INTERFACE_NODE_ADDR = "http://127.0.0.1:8000"

posts = []


app = Flask(__name__)

def fetch_posts():
    """
        Fetches posts from the node and stores them locally
    """
    get_chain_url = "{}/chain".format(INTERFACE_NODE_ADDR)
    response = requests.get(get_chain_url)
    if response.status_code == 200:
        content = []
        chain = json.loads(response.content)
        for block in chain.get("chain", []):
            # "Unpack" the index & hash from the block and apply to each transaction
            for tx in block.get("transactions", []):
                tx["index"] = block["index"]
                tx["hash"] = block["hash"]
                content.append(tx)

    global posts
    posts = sorted(content, key = lambda l: l["timestamp"], reverse=True)


@app.route('/fetch', methods=["GET"])
def get_posts():
    """
        Returns the posts to the front-end
    """
    fetch_posts()
    global posts
    return jsonify({
        "posts": posts
    })


@app.route('/new', methods=['POST'])
def add_post():
    """
        Adds a new post to the interface node
    """
    data = request.json
    r = requests.post(
        "{}/new".format(INTERFACE_NODE_ADDR),
        json=data
    )
    if r.status_code != 201:
        return jsonify({
            "success": False,
            "err": r.text
        }), r.status_code

    return jsonify({
        "success": True,
        "err": None
    }), 200