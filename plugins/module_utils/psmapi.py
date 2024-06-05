#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) IBM Corporation 2023
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import socket
import ssl


def call_client(host, port, authuser, authpass, target, apicommand, *args):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ssock = context.wrap_socket(sock, server_hostname=host)
    server_address = (host, port)
    print("Connecting to server %s port %s" % server_address)
    ssock.connect(server_address)

    readback = 0
    numzeros = 0
    resp_length = 9999
    request_num = 9999
    return_code = 9999
    reason_code = 9999
    message_lines = ""
    thecommand = ""

    # print("num of args is %s" % len(args))
    if len(args) == 1:
        thecommand = args[0]
    if len(args) > 1:
        print("ERROR: What the heck more than 1 command string ?")
        return (return_code)

    print(thecommand)

    cmdstring = bytes()
    cmdbytes = bytes()

    print("Assembling the command string")
    cmdstring += len(apicommand).to_bytes(4, byteorder='big') + apicommand.encode('ASCII')
    # print(cmdstring)
    cmdstring += len(authuser).to_bytes(4, byteorder='big') + authuser.encode('ASCII')
    # print(cmdstring)
    cmdstring += len(authpass).to_bytes(4, byteorder='big') + authpass.encode('ASCII')
    # be careful exposing the full cmdstring from this point on, it contains the unencrypted password
    # print(cmdstring)
    cmdstring += len(target).to_bytes(4, byteorder='big') + target.encode('ASCII')
    # print(cmdstring)
    cmdstring += thecommand.encode('ASCII')
    # print(len(cmdstring))
    # print(cmdstring)
    cmdbytes = len(cmdstring).to_bytes(4, byteorder='big') + cmdstring
    # print(cmdbytes)

    try:
        # be careful with exposing the full cmdbytes because it contains the unencrypted password
        # print("Sending %s" % cmdbytes)
        print("Sending the command string to SMAPI")
        ssock.sendall(cmdbytes)
        message = ""
        while numzeros < 1:
            print("Reading a response from SMAPI")
            reqnum = ssock.recv(4096)
            print("pulling off request number")
            request_num = int.from_bytes(reqnum, byteorder='big')
            # print("raw reqnum: %s" % reqnum)
            # print("int reqnum: %i" % request_num)
            print("pulling off full response")
            response = ssock.recv(4096)
            # print("Response:")
            # print(response)
            # print("\n")
            resp_length = int.from_bytes(response[0:4], byteorder='big')
            # print(response[0:4])
            # print("response totlen: %i" % resp_length)
            request_num = int.from_bytes(response[4:8], byteorder='big')
            # print(response[4:8])
            # print("response reqid: %i" % request_num)
            return_code = int.from_bytes(response[8:12], byteorder='big')
            # print(response[8:12])
            # print("response rc: %i" % return_code)
            reason_code = int.from_bytes(response[12:16], byteorder='big')
            # print(response[12:16])
            # print("response rs: %i" % reason_code)
            num_messages = int.from_bytes(response[16:20], byteorder='big')
            # print("number of message lines: %i" % num_messages )

            # messages is a pointer into the response string, we will move it along
            # the string to pull apart the individual message lines
            messages = response[20:]
            print("SMAPI Response contained VM command response messages, parsing")
            i = 0
            while i < num_messages:
                # message format is <mesg_line_length><message>
                # print("message left:")
                # print(messages)
                line_len = int.from_bytes(messages[0:4], byteorder='big')
                # print("line length: %i" % line_len)
                if line_len == 0:
                    break
                stopchar = line_len + 4
                # line = the message line up to the next message line length value
                line = messages[4:stopchar]
                # print(">" + line.decode('ASCII') + "<")
                messages = messages[stopchar:]
                message_lines += line.decode('ASCII') + "\n"
                i += 1

            numzeros += 1

    except socket.error as e:
        print("Socket Error %s" % str(e))
    except Exception as e:
        print("Some Exception %s" % str(e))
    finally:
        print("Closing connection")
        ssock.close()

    results = []
    results.append(return_code)
    results.append(reason_code)
    results.append(message_lines)
    return (results)
