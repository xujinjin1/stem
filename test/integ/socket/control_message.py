"""
Integration tests for the stem.socket.ControlMessage class.
"""

import re
import socket
import unittest

import stem.socket
import stem.types
import test.runner

class TestControlMessage(unittest.TestCase):
  """
  Exercises the 'stem.socket.ControlMessage' class with an actual tor instance.
  """
  
  def test_unestablished_socket(self):
    """
    Checks message parsing when we have a valid but unauthenticated socket.
    """
    
    control_socket = test.runner.get_runner().get_tor_socket(False)
    if not control_socket: self.skipTest("(no control socket)")
    control_socket_file = control_socket.makefile()
    
    # If an unauthenticated connection gets a message besides AUTHENTICATE or
    # PROTOCOLINFO then tor will give an 'Authentication required.' message and
    # hang up.
    
    stem.socket.send_message(control_socket_file, "GETINFO version")
    
    auth_required_response = stem.socket.recv_message(control_socket_file)
    self.assertEquals("Authentication required.", str(auth_required_response))
    self.assertEquals(["Authentication required."], list(auth_required_response))
    self.assertEquals("514 Authentication required.\r\n", auth_required_response.raw_content())
    self.assertEquals([("514", " ", "Authentication required.")], auth_required_response.content())
    
    # The socket's broken but doesn't realize it yet. Send another message and
    # it should fail with a closed exception. With a control port we won't get
    # an error until we read from the socket. However, with a control socket
    # the write will cause a SocketError.
    
    try:
      stem.socket.send_message(control_socket_file, "GETINFO version")
    except: pass
    
    self.assertRaises(stem.socket.SocketClosed, stem.socket.recv_message, control_socket_file)
    
    # Additional socket usage should fail, and pulling more responses will fail
    # with more closed exceptions.
    
    self.assertRaises(stem.socket.SocketError, stem.socket.send_message, control_socket_file, "GETINFO version")
    self.assertRaises(stem.socket.SocketClosed, stem.socket.recv_message, control_socket_file)
    self.assertRaises(stem.socket.SocketClosed, stem.socket.recv_message, control_socket_file)
    self.assertRaises(stem.socket.SocketClosed, stem.socket.recv_message, control_socket_file)
    
    # The socket connection is already broken so calling close shouldn't have
    # an impact.
    
    control_socket.close()
    self.assertRaises(stem.socket.SocketError, stem.socket.send_message, control_socket_file, "GETINFO version")
    self.assertRaises(stem.socket.SocketClosed, stem.socket.recv_message, control_socket_file)
    
    # Tries again with the file explicitely closed. In python 2.7 the close
    # call will raise...
    # error: [Errno 32] Broken pipe
    
    try: control_socket_file.close()
    except: pass
    
    self.assertRaises(stem.socket.SocketError, stem.socket.send_message, control_socket_file, "GETINFO version")
    
    # receives: stem.socket.SocketClosed: socket file has been closed
    self.assertRaises(stem.socket.SocketClosed, stem.socket.recv_message, control_socket_file)
  
  def test_invalid_command(self):
    """
    Parses the response for a command which doesn't exist.
    """
    
    control_socket = test.runner.get_runner().get_tor_socket()
    if not control_socket: self.skipTest("(no control socket)")
    control_socket_file = control_socket.makefile()
    
    stem.socket.send_message(control_socket_file, "blarg")
    unrecognized_command_response = stem.socket.recv_message(control_socket_file)
    self.assertEquals('Unrecognized command "blarg"', str(unrecognized_command_response))
    self.assertEquals(['Unrecognized command "blarg"'], list(unrecognized_command_response))
    self.assertEquals('510 Unrecognized command "blarg"\r\n', unrecognized_command_response.raw_content())
    self.assertEquals([('510', ' ', 'Unrecognized command "blarg"')], unrecognized_command_response.content())
    
    control_socket.close()
    control_socket_file.close()
  
  def test_invalid_getinfo(self):
    """
    Parses the response for a GETINFO query which doesn't exist.
    """
    
    control_socket = test.runner.get_runner().get_tor_socket()
    if not control_socket: self.skipTest("(no control socket)")
    control_socket_file = control_socket.makefile()
    
    stem.socket.send_message(control_socket_file, "GETINFO blarg")
    unrecognized_key_response = stem.socket.recv_message(control_socket_file)
    self.assertEquals('Unrecognized key "blarg"', str(unrecognized_key_response))
    self.assertEquals(['Unrecognized key "blarg"'], list(unrecognized_key_response))
    self.assertEquals('552 Unrecognized key "blarg"\r\n', unrecognized_key_response.raw_content())
    self.assertEquals([('552', ' ', 'Unrecognized key "blarg"')], unrecognized_key_response.content())
    
    control_socket.close()
    control_socket_file.close()
  
  def test_getinfo_config_file(self):
    """
    Parses the 'GETINFO config-file' response.
    """
    
    runner = test.runner.get_runner()
    torrc_dst = runner.get_torrc_path()
    
    control_socket = runner.get_tor_socket()
    if not control_socket: self.skipTest("(no control socket)")
    control_socket_file = control_socket.makefile()
    
    stem.socket.send_message(control_socket_file, "GETINFO config-file")
    config_file_response = stem.socket.recv_message(control_socket_file)
    self.assertEquals("config-file=%s\nOK" % torrc_dst, str(config_file_response))
    self.assertEquals(["config-file=%s" % torrc_dst, "OK"], list(config_file_response))
    self.assertEquals("250-config-file=%s\r\n250 OK\r\n" % torrc_dst, config_file_response.raw_content())
    self.assertEquals([("250", "-", "config-file=%s" % torrc_dst), ("250", " ", "OK")], config_file_response.content())
    
    control_socket.close()
    control_socket_file.close()
  
  def test_getinfo_config_text(self):
    """
    Parses the 'GETINFO config-text' response.
    """
    
    if stem.process.get_tor_version() < stem.types.REQ_GETINFO_CONFIG_TEXT:
      self.skipTest("(requires %s)" % stem.types.REQ_GETINFO_CONFIG_TEXT)
    
    # We can't be certain of the order, and there may be extra config-text
    # entries as per...
    # https://trac.torproject.org/projects/tor/ticket/2362
    #
    # so we'll just check that the response is a superset of our config
    
    runner = test.runner.get_runner()
    torrc_contents = []
    
    for line in runner.get_torrc_contents().split("\n"):
      line = line.strip()
      
      if line and not line.startswith("#"):
        torrc_contents.append(line)
    
    control_socket = runner.get_tor_socket()
    if not control_socket: self.skipTest("(no control socket)")
    control_socket_file = control_socket.makefile()
    
    stem.socket.send_message(control_socket_file, "GETINFO config-text")
    config_text_response = stem.socket.recv_message(control_socket_file)
    
    # the response should contain two entries, the first being a data response
    self.assertEqual(2, len(list(config_text_response)))
    self.assertEqual("OK", list(config_text_response)[1])
    self.assertEqual(("250", " ", "OK"), config_text_response.content()[1])
    self.assertTrue(config_text_response.raw_content().startswith("250+config-text=\r\n"))
    self.assertTrue(config_text_response.raw_content().endswith("\r\n.\r\n250 OK\r\n"))
    self.assertTrue(str(config_text_response).startswith("config-text=\n"))
    self.assertTrue(str(config_text_response).endswith("\nOK"))
    
    for torrc_entry in torrc_contents:
      self.assertTrue("\n%s\n" % torrc_entry in str(config_text_response))
      self.assertTrue(torrc_entry in list(config_text_response)[0])
      self.assertTrue("%s\r\n" % torrc_entry in config_text_response.raw_content())
      self.assertTrue("%s" % torrc_entry in config_text_response.content()[0][2])
    
    control_socket.close()
    control_socket_file.close()
  
  def test_bw_event(self):
    """
    Issues 'SETEVENTS BW' and parses a few events.
    """
    
    control_socket = test.runner.get_runner().get_tor_socket()
    if not control_socket: self.skipTest("(no control socket)")
    control_socket_file = control_socket.makefile()
    
    stem.socket.send_message(control_socket_file, "SETEVENTS BW")
    setevents_response = stem.socket.recv_message(control_socket_file)
    self.assertEquals("OK", str(setevents_response))
    self.assertEquals(["OK"], list(setevents_response))
    self.assertEquals("250 OK\r\n", setevents_response.raw_content())
    self.assertEquals([("250", " ", "OK")], setevents_response.content())
    
    # Tor will emit a BW event once per second. Parsing two of them.
    
    for _ in range(2):
      bw_event = stem.socket.recv_message(control_socket_file)
      self.assertTrue(re.match("BW [0-9]+ [0-9]+", str(bw_event)))
      self.assertTrue(re.match("650 BW [0-9]+ [0-9]+\r\n", bw_event.raw_content()))
      self.assertEquals(("650", " "), bw_event.content()[0][:2])
    
    control_socket.close()
    control_socket_file.close()
