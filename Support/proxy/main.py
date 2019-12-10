#!/usr/bin/env python3
import json
import logging
import socket
import sys
import os
import pprint
import socket
import urllib.request


SUPPORT_PATH = os.environ.get('TM_BUNDLE_SUPPORT', ('/Users/user/Library/Application Support'
                                                    '/TextMate/Bundles/LSP.tmbundle/Support'))
sys.path.append(SUPPORT_PATH)

from proxy.events import ProxyEvent
from proxy.errors import IncompleteResponseError

from client.client import Client
from client.errors import IncompleteResponseError
from client.events import Initialized, Shutdown, ShowMessageRequest, Completion
from client.structs import (
    CompletionTriggerKind,
    TextDocumentItem,
    TextDocumentPosition,
    CompletionContext,
    TextDocumentIdentifier,
    VersionedTextDocumentIdentifier,
    TextDocumentContentChangeEvent,
    TextDocumentSaveReason,
    Position,
)


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

PROXY_HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PROXY_PORT = 65432        # Port to listen on (non-privileged ports are > 1023)
LS_HOST = '127.0.0.1'
LS_PORT = 8098


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as proxy_sock, \
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as lsp_sock:
    
    # For proxy socket we are server,
    # for ls server we are client
    proxy_sock.bind((PROXY_HOST, PROXY_PORT))
    proxy_sock.listen()
    
    lsp_sock.connect((LS_HOST, LS_PORT))

    # Client initialized and generated init message
    lsp_client = Client()
    
    # Send initialize message to LS socket
    lsp_sock.sendall(lsp_client.send())
    logging.debug('Sent INITIALIZE message to LS')
    
    # Handle init message reponse
    # We are not reading messages from proxy socket
    # unless we ensure LS is ready
    while True:
        try:
            data = lsp_sock.recv(4096)
            if not data:
                logging.error('Can\'t recieve response for INITIALIZE message from LSP!')
                sys.exit()
            
            # Look for initilized message
            events = list(lsp_client.recv(data))
            for event in events:
                if isinstance(event, Initialized):
                    logging.debug('Revieved response for INITIALIZE message')
                    break
            break
        except IncompleteResponseError as e:
            continue

    logging.info('LS initialized. Ready to accept connections from proxy')
    
    # Request listen for new incomming messages
    while True:
        logging.info('Start handling editor connection cycle')
        logging.debug('Waiting to incomming editor connection...')
        conn, addr = proxy_sock.accept()
        logging.debug('Incomming connection from editor recieved')
        
        # Socket should be closed after handling message
        # otherwise socket client (editor) will hang
        with conn:
            logging.debug('Trying to read data from editor socket...')
            data = conn.recv(1024)
            logging.debug('Recieved new data chunk from editor: %s' % data)
            
            message = json.loads(data)
            if message.get('type') == ProxyEvent.COMPLETE:
                logging.debug('Recieved %s message from editor' % ProxyEvent.COMPLETE)
                
                logging.debug('Builing request to LS server')
                request_params = message.get('params')
                if not request_params:
                    assert False
                
                lsp_client.completions(
                    text_document_position=TextDocumentPosition(
                        textDocument=TextDocumentIdentifier(
                            uri=request_params['file']),
                            position=Position(line=request_params['line'],
                                              character=request_params['index']
                        ),
                    ),
                    context=CompletionContext(
                        triggerKind=CompletionTriggerKind.INVOKED
                    ),
                )
                
                logging.debug('Sending message to LS socket')
                lsp_sock.sendall(lsp_client.send())
                
                logging.debug('Waiting for response from LS socket')
                event = None
                while True:
                    try:
                        data = lsp_sock.recv(4096)
                        if not data:
                            logging.error('Can\'t recieve response for COMPLETE message from LSP!')
                            sys.exit()
            
                        # Look for complete message
                        events = list(lsp_client.recv(data))
                        events = [event for event in events if isinstance(event, Completion)]
                        if not events:
                            logging.error('Can\'t recieve response for COMPLETE message from LSP!')
                        
                        event = events[0]
                        logging.debug('Recievend response from LS for COMPLETE message')        
                        break
                    except IncompleteResponseError as e:
                        continue
                
                logging.debug('Sending response back to editor for COMPLETE request...')
                completion_items = json.dumps(
                    [item.label for item in event.completion_list.items]
                ).encode('utf-8')
                conn.sendall(completion_items)
                logging.debug('Response to editor for COMPLETE request sent OK')
                

            logging.debug('Closing listening editor socket...')

        logging.info('End handling editor connection cycle')
        