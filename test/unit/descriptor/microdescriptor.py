"""
Unit tests for stem.descriptor.microdescriptor.
"""

import unittest

import stem.descriptor
import stem.exit_policy
import test.require

from stem.descriptor.microdescriptor import Microdescriptor
from test.unit.descriptor import get_resource

FIRST_ONION_KEY = """\
-----BEGIN RSA PUBLIC KEY-----
MIGJAoGBAMhPQtZPaxP3ukybV5LfofKQr20/ljpRk0e9IlGWWMSTkfVvBcHsa6IM
H2KE6s4uuPHp7FqhakXAzJbODobnPHY8l1E4efyrqMQZXEQk2IMhgSNtG6YqUrVF
CxdSKSSy0mmcBe2TOyQsahlGZ9Pudxfnrey7KcfqnArEOqNH09RpAgMBAAE=
-----END RSA PUBLIC KEY-----\
"""

SECOND_ONION_KEY = """\
-----BEGIN RSA PUBLIC KEY-----
MIGJAoGBALCOxZdpMI2WO496njSQ2M7b4IgAGATqpJmH3So7lXOa25sK6o7JipgP
qQE83K/t/xsMIpxQ/hHkft3G78HkeXXFc9lVUzH0HmHwYEu0M+PMVULSkG36MfEl
7WeSZzaG+Tlnh9OySAzVyTsv1ZJsTQFHH9V8wuM0GOMo9X8DFC+NAgMBAAE=
-----END RSA PUBLIC KEY-----\
"""

THIRD_ONION_KEY = """\
-----BEGIN RSA PUBLIC KEY-----
MIGJAoGBAOWFQHxO+5kGuhwPUX5jB7wJCrTbSU0fZwolNV1t9UaDdjGDvIjIhdit
y2sMbyd9K8lbQO7x9rQjNst5ZicuaSOs854XQddSjm++vMdjYbOcVMqnKGSztvpd
w/1LVWFfhcBnsGi4JMGbmP+KUZG9A8kI9deSyJhfi35jA7UepiHHAgMBAAE=
-----END RSA PUBLIC KEY-----\
"""


class TestMicrodescriptor(unittest.TestCase):
  def test_from_str(self):
    sig = Microdescriptor.create()
    self.assertEqual(sig, Microdescriptor.from_str(str(sig)))

  def test_local_microdescriptors(self):
    """
    Checks a small microdescriptor file with known contents.
    """

    descriptor_path = get_resource('cached-microdescs')

    with open(descriptor_path, 'rb') as descriptor_file:
      descriptors = stem.descriptor.parse_file(descriptor_file, 'microdescriptor 1.0')

      router = next(descriptors)
      self.assertEqual(FIRST_ONION_KEY, router.onion_key)
      self.assertEqual(None, router.ntor_onion_key)
      self.assertEqual([], router.or_addresses)
      self.assertEqual([], router.family)
      self.assertEqual(stem.exit_policy.MicroExitPolicy('reject 1-65535'), router.exit_policy)
      self.assertEqual({b'@last-listed': b'2013-02-24 00:18:36'}, router.get_annotations())
      self.assertEqual([b'@last-listed 2013-02-24 00:18:36'], router.get_annotation_lines())

      router = next(descriptors)
      self.assertEqual(SECOND_ONION_KEY, router.onion_key)
      self.assertEqual('r5572HzD+PMPBbXlZwBhsm6YEbxnYgis8vhZ1jmdI2k=', router.ntor_onion_key)
      self.assertEqual([], router.or_addresses)
      self.assertEqual(['$6141629FA0D15A6AEAEF3A1BEB76E64C767B3174'], router.family)
      self.assertEqual(stem.exit_policy.MicroExitPolicy('reject 1-65535'), router.exit_policy)
      self.assertEqual({b'@last-listed': b'2013-02-24 00:18:37'}, router.get_annotations())
      self.assertEqual([b'@last-listed 2013-02-24 00:18:37'], router.get_annotation_lines())

      router = next(descriptors)
      self.assertEqual(THIRD_ONION_KEY, router.onion_key)
      self.assertEqual(None, router.ntor_onion_key)
      self.assertEqual([('2001:6b0:7:125::242', 9001, True)], router.or_addresses)
      self.assertEqual([], router.family)
      self.assertEqual(stem.exit_policy.MicroExitPolicy('accept 80,443'), router.exit_policy)
      self.assertEqual({b'@last-listed': b'2013-02-24 00:18:36'}, router.get_annotations())
      self.assertEqual([b'@last-listed 2013-02-24 00:18:36'], router.get_annotation_lines())

      self.assertEqual('uhCGfIM6RbeD1Z/C6e9ct41+NIl9EbpgP8wG7uZT2Rw', router.digest())
      self.assertEqual('@type microdescriptor 1.0', str(router.type_annotation()))

  def test_minimal_microdescriptor(self):
    """
    Basic sanity check that we can parse a microdescriptor with minimal
    attributes.
    """

    desc = Microdescriptor.create()

    self.assertEqual(None, desc.ntor_onion_key)
    self.assertEqual([], desc.or_addresses)
    self.assertEqual([], desc.family)
    self.assertEqual(stem.exit_policy.MicroExitPolicy('reject 1-65535'), desc.exit_policy)
    self.assertEqual(None, desc.exit_policy_v6)
    self.assertEqual({}, desc.identifiers)
    self.assertEqual({}, desc.protocols)
    self.assertEqual([], desc.get_unrecognized_lines())

  def test_unrecognized_line(self):
    """
    Includes unrecognized content in the descriptor.
    """

    desc = Microdescriptor.create({'pepperjack': 'is oh so tasty!'})
    self.assertEqual(['pepperjack is oh so tasty!'], desc.get_unrecognized_lines())

  def test_proceeding_line(self):
    """
    Includes a line prior to the 'onion-key' entry.
    """

    desc_text = b'family Amunet1\n' + Microdescriptor.content()
    self.assertRaises(ValueError, Microdescriptor, desc_text, True)

    desc = Microdescriptor(desc_text, validate = False)
    self.assertEqual(['Amunet1'], desc.family)

  def test_a_line(self):
    """
    Sanity test with both an IPv4 and IPv6 address.
    """

    desc_text = Microdescriptor.content()
    desc_text += b'\na 10.45.227.253:9001'
    desc_text += b'\na [fd9f:2e19:3bcf::02:9970]:9001'

    expected = [
      ('10.45.227.253', 9001, False),
      ('fd9f:2e19:3bcf::02:9970', 9001, True),
    ]

    desc = Microdescriptor(desc_text)
    self.assertEqual(expected, desc.or_addresses)

  def test_family(self):
    """
    Check the family line.
    """

    desc = Microdescriptor.create({'family': 'Amunet1 Amunet2 Amunet3'})
    self.assertEqual(['Amunet1', 'Amunet2', 'Amunet3'], desc.family)

    # try multiple family lines

    desc_text = Microdescriptor.content()
    desc_text += b'\nfamily Amunet1'
    desc_text += b'\nfamily Amunet2'

    self.assertRaises(ValueError, Microdescriptor, desc_text, True)

    # family entries will overwrite each other
    desc = Microdescriptor(desc_text, validate = False)
    self.assertEqual(1, len(desc.family))

  def test_exit_policy(self):
    """
    Basic check for 'p' lines. The router status entries contain an identical
    field so we're not investing much effort here.
    """

    desc = Microdescriptor.create({'p': 'accept 80,110,143,443'})
    self.assertEqual(stem.exit_policy.MicroExitPolicy('accept 80,110,143,443'), desc.exit_policy)

  def test_protocols(self):
    """
    Basic check for 'pr' lines.
    """

    desc = Microdescriptor.create({'pr': 'Cons=1 Desc=1 DirCache=1 HSDir=1 HSIntro=3 HSRend=1 Link=1-4 LinkAuth=1 Microdesc=1 Relay=1-2'})
    self.assertEqual(10, len(desc.protocols))

  def test_identifier(self):
    """
    Basic check for 'id' lines.
    """

    desc = Microdescriptor.create({'id': 'rsa1024 Cd47okjCHD83YGzThGBDptXs9Z4'})
    self.assertEqual({'rsa1024': 'Cd47okjCHD83YGzThGBDptXs9Z4'}, desc.identifiers)

    # check when there's multiple key types

    desc_text = b'\n'.join((
      Microdescriptor.content(),
      b'id rsa1024 Cd47okjCHD83YGzThGBDptXs9Z4',
      b'id ed25519 50f6ddbecdc848dcc6b818b14d1',
    ))

    desc = Microdescriptor(desc_text, validate = True)
    self.assertEqual({'rsa1024': 'Cd47okjCHD83YGzThGBDptXs9Z4', 'ed25519': '50f6ddbecdc848dcc6b818b14d1'}, desc.identifiers)

    # check when there's conflicting keys

    desc_text = b'\n'.join((
      Microdescriptor.content(),
      b'id rsa1024 Cd47okjCHD83YGzThGBDptXs9Z4',
      b'id rsa1024 50f6ddbecdc848dcc6b818b14d1',
    ))

    desc = Microdescriptor(desc_text)
    self.assertEqual({}, desc.identifiers)

    exc_msg = "There can only be one 'id' line per a key type, but 'rsa1024' appeared multiple times"
    self.assertRaisesWith(ValueError, exc_msg, Microdescriptor, desc_text, validate = True)
