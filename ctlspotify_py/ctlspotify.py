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



# sends an authorized http request to the spotify api 
def spotify_request(
    method, endpoint, token, expected_code, data=None, json=None, silent=False
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
        return (response, None)
    
    if not silent:
        sys.stderr.write('something went wrong\n')
        try:
            sys.stderr.write(response.json()['error']['message'] + '\n')
            sys.stderr.write('reason: ' + response.json()['error']['reason'])
        except json.decoder.JSONDecodeError:
            sys.stderr.write('error ' + str(response.status_code) + ' ~ empty body ~')
        except KeyError:
            sys.stderr.write(str(response.json()))
        sys.stderr.write('\n')
    
    return (response, response.status_code)


def show_status(args, token):
    resp, err = spotify_request('get', 'me/player/devices', token, 200)
    if err: sys.exit(1)
    
    rs_dev = resp.json()
    
    active_dev = list(filter(lambda dev: dev['is_active'], rs_dev['devices']))

    if args.devices or len(active_dev) < 1:
        print('there are no active devices at the moment')
        print('all available devices:')
        for device in rs_dev['devices']:
            state = '> ' if device['is_active'] else '  '
            print(f"{state}name: {device['name']}, type: {device['type']}", end='')
            if args.devices:
                print(f", volume: {device['volume_percent']}")
                print(f"    id: {device['id']}", end='')
            print()
    
    if len(active_dev) < 1:
        # no active device exists
        return
    
    # some active device exists
    resp, err = spotify_request('get', 'me/player', token, 200)
    if err: sys.exit(1)
    
    rs_player = resp.json()
    
    item = rs_player['item']
    if not item:
        print('no track is playing *cricet noise*')
        return
    
    print(f"🎵 playing \'{item['name']}\' " + 
          f"by \'{item['artists'][0]['name']}\'", end='')
    if not rs_player['is_playing']: print(' (paused)', end='')
    if args.devices: print(f" on {rs_player['device']['name']}", end='')
    print()


def play(args, token):

    if not args.query:
        resume(args, token)
        return
    
    # TODO
    sys.stderr.write('this is WIP\n')
    print(args)
    query = " ".join(args.query)
    if args.query_is_formatted:
        artist_song = ":".split(query)
        artist = artist_song[0].strip()
        songname = artist_song[1].strip()
    print('maybe playing \'' + query + '\'')


def resume(args, token):
    resp, err = spotify_request('put', 'me/player/play', token, 204, silent=True)
    if not err:
        print('▶ resumed')
        return

    elif err != 404 or resp.json()['error']['reason'] != 'NO_ACTIVE_DEVICE':
        sys.exit(1)

    # try to transfer playback if error 404 'no active device'
    resp_dev, err_dev = spotify_request('get', 'me/player/devices', token, 200)
    if err_dev: sys.exit(1) # getting info about devices failed
    
    devices = resp_dev.json()['devices']
    transfer_to_dev_id = None
    
    # determin which device to transfer to
    if args.device:
        fl = filter(lambda dev: dev['name'].lower() == args.device.lower(), devices)
        if len(list(fl)) < 1:
            sys.stderr.write('no available device with that name\n')
            return
        transfer_to_dev_id = list(fl)[0]['id'] # the name ~pobably~ is unique

    elif len(devices) == 1:
        transfer_to_dev_id = devices[0]['id']

    else:
        print('Available devices:')
        i = 1
        for device in devices:
            print(f"{i})  name: {device['name']}, type: {device['type']}")
            i += 1
        print('enter a device number: ', end='')
        while True:
            try:
                d = int(input()) - 1
                transfer_to_dev_id = devices[d]['id']
                break
            except (ValueError, IndexError):
                print('not a valid option, try again: ', end='')
                continue
    
    body = {"device_ids": [transfer_to_dev_id],
            "play": True}
    _, err = spotify_request('put', 'me/player', token, 204, json=body)
    if err: sys.exit(1)
    # playback has been resumed on a previously inactive device
    print('▶ resumed')
    

def transfer(args, token):
    # TODO
    sys.stderr.write('this is WIP, wild things may happen :P\n')
    device_id = None
    start_playing = False
    body = {"devices_ids": device_id,
            "play": start_playing}
    _, err = spotify_request('put', 'me/player', token, 204, json=body)
    if err: sys.exit(1)


def pause(args, token):
    _, err = spotify_request('put', 'me/player/pause', token, 204)
    if err: sys.exit(1)
    
    print('⏸ paused')


def next_track(args, token):
    _, err = spotify_request('post', 'me/player/next', token, 204)
    if err: sys.exit(1)
    
    print('⏩ skipped')


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
    parser.add_argument('-d', '--devices', action='store_true',
                        help="show details about available devices")
    parser.set_defaults(func=show_status)

    subparsers = parser.add_subparsers()
    
    play_parser = subparsers.add_parser('play',
                                        help="start playing first search result for QUERY")
    play_parser.add_argument('query', nargs='*', default=None,
                             help="if omitted it acts the same as \'resume\'")
    play_parser.add_argument('-a', '--artist',
                             help="specify artist of the track")
    play_parser.add_argument('-f', '--formatted', action='store_true', dest='querry_is_formatted',
                             help="QEURY will be interpreted as <artist> : <song_name>")
    play_parser.add_argument('-d', '--device', '--dev',
                             help="specify device to start playing on")
    play_parser.set_defaults(func=play)
    
    resume_parser = subparsers.add_parser('resume',
                                          help="resumes the playback")
    resume_parser.add_argument('-d', '--device', '--dev',
                               help="choose which device will be activatedif no device is active ")
    resume_parser.set_defaults(func=resume)
    
    pause_parser = subparsers.add_parser('pause',
                                         help="pauses the playback")
    pause_parser.set_defaults(func=pause)
    
    next_parser = subparsers.add_parser('next', aliases=['skip', 'n'],
                                        help="skipps the current track")
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


