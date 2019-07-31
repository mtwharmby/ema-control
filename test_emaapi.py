import os
import socket
import sys

import pytest
from mock import call, Mock, patch

from emaapi import robot_begin, robot_end, mount_sample, unmount_sample, Robot

pathlib_path = False  # As this doesn't work with python < 3.6
if sys.version_info[0] >= 3:
    if sys.version_info[1] > 5:
        from pathlib import Path
        pathlib_path = True

# These tests are for the  basic start-up/shutdown methods
@patch('emaapi.ema')
def test_robot_begin(ema_mock):
    with patch('builtins.input'):
        robot_begin()
    assert ema_mock.mock_calls == [call.send('powerOn;',
                                             wait_for='powerOn:done;')]


@patch('emaapi.ema')
def test_robot_end(ema_mock):
    robot_end()
    assert ema_mock.mock_calls == [call.send('powerOff;',
                                             wait_for='powerOff:done;')]


# Methods inside the implementation of the robot class
def test_init():
    ema = Robot()
    assert ema.sample_index is None
    assert ema.x_coord is None
    assert ema.y_coord is None
    assert ema.connected is False
    assert ema.address is None
    assert ema.port is None
    if pathlib_path:
        home_dir = Path.home()
    else:
        home_dir = os.path.expanduser('~')
    assert ema.config_file == os.path.join(home_dir, '.robot.ini')
    assert ema.sock is None


@patch('socket.socket')
def test__send__(sock_mock):
    message = 'ACommandWithParameters:#P1#P2;'
    msg_reply = 'ACommandWithParameters:done;'
    sock_mock().send.return_value = len(message)
    sock_mock().recv.return_value = msg_reply.encode()

    ema = Robot(robot_host='127.0.0.3', robot_port=10006)
    reply = ema.__send__(message)

    assert reply == msg_reply
    sock_calls = [call.connect(('127.0.0.3', 10006)),
                  call.send(message.encode()),
                  call.shutdown(socket.SHUT_WR),
                  call.recv(1024),
                  call.close()]
    sock_mock().assert_has_calls(sock_calls)

    # Same again, but now the messages are sent and received in pieces
    sock_mock().reset_mock(return_value=True, side_effect=True)
    sock_mock().send.side_effect = [5, 10, 7, 8]
    sock_mock().recv.side_effect = [b'ACommandWithP',
                                    b'arameters:',
                                    b'done;']

    ema = Robot(robot_host='127.0.0.3', robot_port=10006)
    reply = ema.__send__(message)

    assert reply == msg_reply

    # Now test what happens when no message delimiter is received
    sock_mock().reset_mock(return_value=True, side_effect=True)
    sock_mock().send.reset_mock(return_value=True, side_effect=True)
    sock_mock().recv.reset_mock(return_value=True, side_effect=True)

    msg_reply = 'ACommandWithParameters:done'  # N.B. Removed delimiter
    sock_mock().send.return_value = len(message)
    sock_mock().recv.return_value = msg_reply.encode()

    ema = Robot(robot_host='127.0.0.3', robot_port=10006, socket_timeout=0.5)
    with pytest.raises(RuntimeError, match=r".*delimiter.*"):
        reply = ema.__send__(message)


@patch('configparser.ConfigParser')
def test_set_sample_coords(conf_mock):
    with patch('emaapi.Robot.send') as send_mock:
        ema = Robot()
        ema.set_sample_coords(75)
        send_mock.assert_called_with('setAxis:#X7#Y4;',
                                     wait_for='setAxis:done;')


def test_read_config():
    ema = Robot(config_file='./example_config.ini')
    ema.__read_config__()
    assert ema.address == '127.0.0.2'
    assert ema.port == 10005


@patch('socket.socket')
def test_connect(sock_mock):
    ema = Robot()
    ema.address = '127.0.0.3'
    ema.port = 10006
    assert ema.connected is False
    ema.connect()
    assert ema.connected is True
    sock_calls = [call(socket.AF_INET, socket.SOCK_STREAM),
                  call().connect(('127.0.0.3', 10006))]
    assert sock_mock.mock_calls == sock_calls


@patch('socket.socket')
def test_disconnect(sock_mock):
    ema = Robot()
    ema.address = '127.0.0.3'
    ema.port = 10006
    assert ema.connected is False
    ema.connect()
    ema.disconnect()
    assert ema.connected is False


# Method supports set_sample_coords
def test_sample_to_coords():

    # Some specific examples of coords calculated...
    assert (0, 0) == Robot.samplenr_to_xy(1)
    assert (0, 1) == Robot.samplenr_to_xy(2)
    assert (1, 0) == Robot.samplenr_to_xy(11)

    # ...and all values for 300 samples
    n = 1
    for i in range(0, 30):
        for j in range(0, 10):
            assert (i, j) == Robot.samplenr_to_xy(n)
            n += 1

    with pytest.raises(ValueError, match=r".*greater than 0"):
        Robot.samplenr_to_xy(0)


# The following tests are for functions which wait for a message to return from
# the robot before continuing
@patch('emaapi.ema')
def test_mount_sample(ema_mock):
    samcoords_mock = Mock()
    send_mock = Mock()
    ema_mock.connected = True
    ema_mock.set_sample_coords = samcoords_mock
    ema_mock.send = send_mock

    mount_sample(75,)
    # Preparation for mounting...
    samcoords_mock.assert_called_with(75, verbose=False)
    # ... and the actual process:
    send_calls = [call('next;', wait_for='moveNext:done;'),
                  call('pick;', wait_for='pickSample:done;'),
                  call('gate;', wait_for='moveGate:done;'),
                  call('spinner;', wait_for='moveSpinner:done;'),
                  call('release;', wait_for='releaseSample:done;'),
                  call('offside;', wait_for='moveOffside:done;')
                  ]
    send_mock.assert_has_calls(send_calls)

    ema_mock.connected = False
    with pytest.raises(Exception, match=r".*Did you run the robot_begin.*"):
        mount_sample(75)


@patch('emaapi.ema')
def test_unmount_sample(ema_mock):
    ema_mock.connected = True
    unmount_sample()
    send_calls = [call.send('spinner;', wait_for='moveSpinner:done;'),
                  call.send('pick;', wait_for='pickSample:done;'),
                  call.send('gate;', wait_for='moveGate:done;'),
                  call.send('current;', wait_for='returnCurrent:done;'),
                  call.send('release;', wait_for='releaseSample:done;')
                  ]
    ema_mock.assert_has_calls(send_calls)

    ema_mock.connected = False
    with pytest.raises(Exception, match=r".*Did you run the robot_begin.*"):
        unmount_sample()
