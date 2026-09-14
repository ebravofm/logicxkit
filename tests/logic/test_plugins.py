"""Which plug-ins a project references, and whether this Mac has them: Apple's own are named
by type id; a third-party slot carries its AU component identity in an embedded preset plist."""

import plistlib
import struct
import unittest
import _paths  # noqa: F401
from logicxkit.logic.services.plugins import PluginRef, installed_from_auval, project_plugins, verdict

HDR = 36


def rec(tag: bytes, owner: int, key: int, payload: bytes, ver: int = 5) -> bytes:
    h = bytearray(HDR)
    h[0:4] = tag
    struct.pack_into("<H", h, 4, ver)
    struct.pack_into("<H", h, 14, owner)
    struct.pack_into("<H", h, 18, key)
    struct.pack_into("<I", h, 28, len(payload))
    return bytes(h) + payload


def native_slot(owner: int, key: int, type_id: int, n: int = 8) -> bytes:
    p = bytearray(220)
    p[184:192] = b"GAMETSPP"
    struct.pack_into("<III", p, 172, 24 + n * 4, 1, n)
    struct.pack_into("<I", p, 192, type_id)
    return rec(b"UCuA", owner, key, bytes(p))


def fourcc(s: str) -> int:
    return struct.unpack(">I", s.encode("latin-1"))[0]


def third_party_slot(owner: int, key: int, *, type_="aufx", subtype="FC2p", manu="FabF", name="Pro-C 2") -> bytes:
    pl = plistlib.dumps({"type": fourcc(type_), "subtype": fourcc(subtype), "manufacturer": fourcc(manu),
                         "name": name, "version": 0, "data": b"\0" * 12}, fmt=plistlib.FMT_XML)
    return rec(b"UCuA", owner, key, bytes(64) + pl + bytes(16))


def chan(owner: int, label: str) -> bytes:
    p = bytearray(257)
    p[24] = p[25] = 1
    p[60:60 + len(label) + 1] = b" " + label.encode()
    return rec(b"OCuA", owner, 0xFFFF, bytes(p), 7)


def proj(*records: bytes) -> bytes:
    body = b"".join(records)
    head = bytearray(24)
    struct.pack_into("<I", head, 0x10, len(body))
    return bytes(head) + body


class ProjectPluginsTest(unittest.TestCase):
    def test_native_and_third_party_slots_are_identified(self):
        data = proj(chan(0, "Audio 1"), native_slot(0, 2, 236), third_party_slot(0, 3), chan(1, "Audio 2"))
        refs = project_plugins(data)
        self.assertEqual([(r.channel, r.key, r.name, r.native, r.component) for r in refs],
                         [("Audio 1", 2, "Channel EQ", True, None),
                          ("Audio 1", 3, "FabF/FC2p", False, ("aufx", "FC2p", "FabF"))])


class VerdictTest(unittest.TestCase):
    REFS = [PluginRef("Audio 1", 2, "Channel EQ", True, None),
            PluginRef("Audio 1", 3, "Pro-C 2", False, ("aufx", "FC2p", "FabF")),
            PluginRef("Audio 2", 2, "Gone", False, ("aufx", "Xxxx", "Nono"))]

    def test_missing_third_party_components_are_named(self):
        v = verdict(self.REFS, installed={("aufx", "FC2p", "FabF")})
        self.assertEqual([(r.name, s) for r, s in v.slots], [("Channel EQ", "apple"), ("Pro-C 2", "installed"), ("Gone", "missing")])
        self.assertEqual((v.missing, v.clean), ([self.REFS[2]], False))

    def test_a_project_with_every_component_present_is_clean(self):
        v = verdict(self.REFS[:2], installed={("aufx", "FC2p", "FabF")})
        self.assertTrue(v.clean)


class AuvalTest(unittest.TestCase):
    def test_the_installed_set_comes_from_auval_lines(self):
        text = ("    AU Validation Tool\n    Version: 1.10.0\n\n"
                "aufx Aln2 Srdx  -  Sound Radix: Auto-Align 2\n"
                "aumu Nave Wald  -  Waldorf: Nave\n")
        self.assertEqual(installed_from_auval(text), {("aufx", "Aln2", "Srdx"), ("aumu", "Nave", "Wald")})


if __name__ == "__main__":
    unittest.main()
