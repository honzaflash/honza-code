#!/usr/bin/python

import sys
from os import path
from time import time
import argparse
import json
import urllib.parse as urlp
from base64 import b64encode
from pip._vendor.requests import request, post

# some static globals
TOKEN_PATH = '.spotify_tokens'
CLIENT_INFO_PATH = '.spotify_client_info'



def handle_unok_responses(response):
    sys.stderr.write('something went wrong\n')
    try:
        sys.stderr.write(str(response.json()))
    except json.decoder.JSONDecodeError:
        sys.stderr.write('error ' + str(response.status_code) + ' ~ empty body ~')
    sys.stderr.write('\n')
    sys.exit(1)


# sends an authorized http request to the spotify api 
def spotify_request(
    method, endpoint, token, expected_code, data=None, json=None
):
    response = request(method,
                   'https://api.spotify.com/v1/' + endpoint,
                   headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + token
                   },
                   data=data, json=json)
    if response.status_code == expected_code:
        return response
    
    # this exits the program
    handle_unok_responses(response)


def show_status(args, token):
    rs_dev = spotify_request('get', 'me/player/devices', token, 200).json()
    
    active_dev = list(filter(lambda dev: dev['is_active'], rs_dev['devices']))
    if len(active_dev) < 1:
        print('no active devices')
        print('available device: ', end='')
        for device in rs_dev['devices']:
            print(f"  name: {device['name']}; type: {device['type']};")
        return
    
    if args.devices:
        print('all available devices:')
        for device in rs_dev['devices']:
            state = 'active' if device['is_active'] else 'not active'
            print(f"  name: {device['name']}; type: {device['type']}" +
                  f"; volume: {device['volume_percent']} - {state}")
            print(f"    id: {device['id']}")
    
    rs_player = spotify_request('get', 'me/player', token, 200).json()
    
    item = rs_player['item']
    if not item:
        print('no track is playing *cricet noise*')
        return
    
    print(f"🎵 playing \'{item['name']}\' " + 
          f"by \'{item['artists'][0]['name']}\'", end='')
    if not rs_player['is_playing']: print(' (paused)', end='')
    if args.devices: print(f" on {rs_player['device']['name']}", end='')
    print()
    

def next_track(args, token):
    spotify_request('post', 'me/player/next', token, 204)
    print('⏩ skipped')


def resume(args, token):
    spotify_request('put', 'me/player/play', token, 204)
    print('▶ resumed')

def transfer(args, token):
    sys.stderr.write('this is WIP, wild things may happen :P\n')
    device_id = None
    start_playing = False
    body = {"devices_ids": device_id,
            "play": start_playing}
    spotify_request('put', 'me/player', token, 204, json=body)


def pause(args, token):
    spotify_request('put', 'me/player/pause', token, 204)
    print('⏸ paused')


# reads client id and secret from 'CLIENT_INFO_PATH'
# if needed it will create the file and
# ask the user to provide the information
def get_client_info():
    if not path.exists(CLIENT_INFO_PATH):
        with open(CLIENT_INFO_PATH, 'w') as client_info:
            client_info.write('{\n    "client_id": "",\n    "client_secret": ""\n}')
        print('new file' + CLIENT_INFO_PATH + ' has been created')
        print('please fill into it needed client info')
        print('then press any key to continue...', end='')
        input()

    with open(CLIENT_INFO_PATH, 'r') as client_info:
        info_json = json.loads(client_info.read())
        if not info_json['client_id'] or not info_json['client_secret']:
            sys.stderr.write('missing client information in ' +
                             CLIENT_INFO_PATH + '\n' +
                             'please fill it in and try again\n')
        return (info_json['client_id'], info_json['client_secret'])


# asks for authorization of the client if 'TOKEN_PATH' is missing
# requires user interaction
# requests new access and refresh tokens from spotify api
def request_new_tokens():
    print('no ' + TOKEN_PATH + ' found, running authorization')
    
    client_id, client_secret = get_client_info()
    print('go to: ' + 'https://accounts.spotify.com/authorize?'+
          'client_id=' + client_id + '&' +
          'scope=' + 'user-modify-playback-state+user-read-playback-state&' + 
          'response_type=code&' + 
          'redirect_uri=https%3A%2F%2Fdeveloper.spotify.com%2F')
    
    print('copy the code from the redirect url and paste it here:\n', end='')
    code = input()
    
    id_and_secret_base64 = b64encode(
        (client_id + ':' + client_secret).encode('ascii')
        ).decode('ascii')
    print('sending out request for tokens...')
    response = post('https://accounts.spotify.com/api/token',
                    headers={'Content-Type': 'application/x-www-form-urlencoded',
                             'Authorization': 'Basic ' + id_and_secret_base64}, 
                    data='grant_type=authorization_code&' +
                         'code=' + code + '&' +
                         'redirect_uri=https%3A%2F%2Fdeveloper.spotify.com%2F')
    print('response code:', response.status_code)
    if not response.status_code == 200:
        sys.stderr.write('whoopsie, authorization failed :\'(\n')
        try:
            sys.stderr.write(json.dumps(response.json()), '\n')
        except json.decoder.JSONDecodeError: 
            sys.stderr.write('- no body -\n')
        return
    print('we got \'em')    

    auth_data = response.json()
    auth_data['gained_at'] = int(time())
    with open(TOKEN_PATH, 'w') as token_file:
        token_file.write(json.dumps(auth_data))


# returns access token
# if needed it will ask for authorization by the user
# or will refresh the access token
def get_access_token(verbose):
    if not path.exists(TOKEN_PATH):
        # get tokens and write them into a file
        request_new_tokens()

    auth_data = None
    with open(TOKEN_PATH, 'r') as token_file:
        auth_data = json.loads(token_file.read())

    # if token has not expired
    if time() - auth_data['gained_at'] < auth_data['expires_in'] - 10:
        if verbose: print('token in the file hasn\'t expired yet')
        return auth_data['access_token']

    # token has expired - requires refresh
    client_id, client_secret = get_client_info()
    id_and_secret_base64 = b64encode(
        (client_id + ':' + client_secret).encode('ascii')
        ).decode('ascii')
    if verbose: print('token in the file has expired, refreshing')
    response = post('https://accounts.spotify.com/api/token',
                    headers={'Content-Type': 'application/x-www-form-urlencoded',
                             'Authorization': 'Basic ' + id_and_secret_base64},
                    data='grant_type=refresh_token&refresh_token=' +
                         auth_data['refresh_token']
                    )
    
    if verbose: print('response code:', response.status_code)
    # if reponse code is not OK (200)
    if not response.status_code == 200:
        sys.stderr.write('whoopsie, refreshing token failed :\'(\n')
        try:
            sys.stderr.write(json.dumps(response.json()) + '\n')
        except json.decoder.JSONDecodeError: 
            sys.stderr.write('- no body -\n')
        return
    
    # response code is OK (200)
    auth_data['access_token'] = response.json()['access_token']
    auth_data['gained_at'] = int(time())
    with open(TOKEN_PATH, 'w') as token_file:
        token_file.write(json.dumps(auth_data))

    # returning needed token
    return response.json()['access_token']



def main(argv):
   
    parser = argparse.ArgumentParser(
        description='Controll your Spotify playback through CLI',
        prog='ctlspotify')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-d', '--devices', action='store_true')
    parser.set_defaults(func=show_status)

    subparsers = parser.add_subparsers()
    
    resume_parser = subparsers.add_parser('resume', aliases=['play'])
    resume_parser.set_defaults(func=resume)
    
    pause_parser = subparsers.add_parser('pause')
    pause_parser.set_defaults(func=pause)
    
    next_parser = subparsers.add_parser('next', aliases=['skip', 'n'])
    next_parser.set_defaults(func=next_track)

    args = parser.parse_args(argv)

    if args.verbose: print('authorizing')
    token = get_access_token(args.verbose)
    if args.verbose: print('authorized')
    
    args.func(args, token)

    sys.exit(0)



# when run as a script
if __name__ == "__main__":
   main(sys.argv[1:])


