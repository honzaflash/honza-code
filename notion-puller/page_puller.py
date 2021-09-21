#!/usr/bin/python

import sys
from os import path
from time import time

import argparse
import json

import urllib.parse as urlp
# from base64 import b64encode
from pip._vendor.requests import request, post



# sends an authorized http request to the spotify api 
def notion_request(
    method, endpoint, token, expected_code=200, data=None, json=None, verbose=False
):
    response = request(method,
                   'https://api.notion.com/v1/' + endpoint,
                   headers={
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json",
                        "Notion-Version": "2021-08-16",
                   },
                   data=data,
                   json=json)
    if response.status_code == expected_code:
        return response.json()
    print(response)
    if verbose:
        sys.stderr.write('something went wrong\n')
        sys.stderr.write('ERROR ' + str(response.status_code) + '\n')
    
    #raise (response.json(), response.status_code)
    return None


def read_env(path=".env"):
    env = None
    with open(path, 'r') as env_file:
        env = json.loads(env_file.read())
    return env


# returns a list of children's contents + their id's if they have their own children
def get_block_children(token, block_id, verbose=False):
    resp = notion_request("GET", f"blocks/{block_id}/children", token, verbose=verbose)

    children = []
    for child in resp["results"]:
        contents = get_block_contents(child)
        children.append(contents)
        if child["has_children"]:
            children.extend(map(
                lambda subcontent: "    " + subcontent,
                get_block_children(token, child["id"], verbose=verbose)
                ))
    
    return children


def get_block_contents(block):
    if block["type"] == "paragraph":
        return merge_block_text_chunks(block)
    
    elif block["type"] == "to_do":
        return ("✔ " if block["to_do"]["checked"] else "□ ") + \
            merge_block_text_chunks(block)
    
    elif block["type"] == "toggle":
        return "▼ " + merge_block_text_chunks(block)
    
    elif block["type"] == "bulleted_list_item":
        return "* " + merge_block_text_chunks(block)
    
    elif block["type"] == "numbered_list_item":
        return "1 " + merge_block_text_chunks(block)
    
    elif block["type"] == "heading_1":
        return "### " + merge_block_text_chunks(block) + " ###"
    
    elif block["type"] == "heading_2":
        return "## " + merge_block_text_chunks(block) + " ##"
    
    elif block["type"] == "heading_3":
        return "# " + merge_block_text_chunks(block) + " #"
    
    elif block["type"] == "unsupported":
        return "-- unsupported by the API --"
    
    else:
        sys.stderr.write(json.dumps(block, indent=2, sort_keys=False))
        return "WIP ~ content type unsupported by this script"
    
    
def merge_block_text_chunks(block):
    return "".join(map(lambda txt: txt["plain_text"], block[block["type"]]["text"]))


def print_page(args):
    env = read_env()
    token = env["api_token"]
    page_id = env["page_id"]
    children = get_block_children(token, page_id, verbose=args.verbose)
    
    print("\n".join(children))
    



def main(argv):
   
    parser = argparse.ArgumentParser(
        description='Display contents of a Notion page in CLI',
        prog='page-puller')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.set_defaults(func=print_page)

    args = parser.parse_args(argv)

    args.func(args) # running the program

    sys.exit(0)


# when run as a script
if __name__ == "__main__":
   main(sys.argv[1:])

