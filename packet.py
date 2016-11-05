#!/usr/bin/env python3

def to_bits(octet, offset, length, n_bits = 8):
    mask = (1 << length) - 1
    return (octet >> (n_bits - offset - length)) & mask


def to_octets(i, n_octets = 1):
    l = []
    for x in range(n_octets):
        l.append(to_bits(i, 8 * x, 8, 8 * n_octets))
    return bytes(l)


def to_integer(octets, n_bits = 8):
    l = len(octets) - 1
    i = 0
    for o in octets:
        i += o << (l * n_bits)
        l -= 1
    return i


class MACAddress:
    def __init__(self, octets):
        self.address = tuple(int(o) for o in octets)
    def __str__(self):
        return ":".join(hex(o)[2:].rjust(2, "0") for o in self.address)
    def __getitem(self, i):
        return self.address[i]


class EthernetFrame:
    def __init__(self, octets):
        self._raw = octets

        self.dest_address = MACAddress(octets[0:6])
        self.source_address = MACAddress(octets[6:12])

        self.ethertype = (octets[12] << 8) + octets[13]
        if self.ethertype != 0x0800:
            raise ValueError("non-ipv4 packet")

        self.payload = IPv4Packet(octets[14:])

        # self.payload = IPv4Packet(octets[14:-4])
        # self.crc = octets[-4:]

    def raw(self):
        return (
            bytes(self.dest_address.address) +
            bytes(self.source_address.address) +
            to_octets(self.ethertype, 2) +
            self.payload.raw()
        )


class IPv4Address:
    def __init__(self, octets):
        self.address = tuple(int(o) for o in octets)
    def __str__(self):
        return ".".join(str(o) for o in self.address)
    def __getitem__(self, i):
        return self.address[i]


class IPv4Packet:
    def __init__(self, octets):
        self._raw = octets

        self.version = to_bits(octets[0], 0, 4)

        if self.version != 4:
            raise ValueError("non-ipv4 packet")

        self.ihl = to_bits(octets[0], 4, 4)

        self.dscp = to_bits(octets[1], 0, 6)
        self.ecn = to_bits(octets[1], 6, 2)

        self.length = to_integer(octets[2:4])

        self.identification = to_integer(octets[4:6])

        flags_and_fragment = to_integer(octets[6:8])
        self.flags = to_bits(flags_and_fragment, 0, 3, 16)
        self.fragment_offset = to_bits(flags_and_fragment, 3, 13, 16)

        self.ttl = octets[8]
        self.protocol = octets[9]
        if self.protocol != 6:
            raise ValueError("non-tcp packet")
        self.checksum = to_integer(octets[10:12])

        self.source_address = IPv4Address(octets[12:16])
        self.dest_address = IPv4Address(octets[16:20])

        option_words = self.ihl - 5
        self.options = to_integer(octets[20:20 + (4 * option_words)])
        self.payload = TCPPacket(octets[20 + (4 * option_words):])

    def raw(self):
        return (
            to_octets(to_integer([self.version, self.ihl], 4)) +
            to_octets((self.dscp << 2) + self.ecn) +
            to_octets(self.length, 2) +
            to_octets(self.identification, 2) +
            to_octets((self.flags << 13) + self.fragment_offset, 2) +
            to_octets(self.ttl) +
            to_octets(self.protocol) +
            to_octets(self.checksum, 2) +
            bytes(self.source_address.address) +
            bytes(self.dest_address.address) +
            to_octets(self.options, (self.ihl - 5) * 4) +
            self.payload.raw()
        )


class TCPPacket:
    def __init__(self, octets):
        self._raw = octets

        self.source_port = to_integer(octets[0:2])
        self.dest_port = to_integer(octets[2:4])

        self.sequence = to_integer(octets[4:8])

        self.ack_number = to_integer(octets[8:12])

        self.data_offset = to_bits(octets[12], 0, 4)
        self.reserved = to_bits(octets[12], 4, 3)

        self.NS = bool(to_bits(octets[12], 7, 1))
        self.CWR = bool(to_bits(octets[13], 0, 1))
        self.ECE = bool(to_bits(octets[13], 1, 1))
        self.URG = bool(to_bits(octets[13], 2, 1))
        self.ACK = bool(to_bits(octets[13], 3, 1))
        self.PSH = bool(to_bits(octets[13], 4, 1))
        self.RST = bool(to_bits(octets[13], 5, 1))
        self.SYN = bool(to_bits(octets[13], 6, 1))
        self.FIN = bool(to_bits(octets[13], 7, 1))

        self.window_size = to_integer(octets[14:16])

        self.checksum = to_integer(octets[16:18])

        self.urgent_pointer = to_integer(octets[18:20])

        option_words = self.data_offset - 5
        self.options = to_integer(octets[20:20 + (4 * option_words)])
        self.payload = octets[20 + (4 * option_words):]

    def raw(self):
        return (
            to_octets(self.source_port, 2) +
            to_octets(self.dest_port, 2) +
            to_octets(self.sequence, 4) +
            to_octets(self.ack_number, 4) +
            to_octets((self.data_offset << 4) + (self.reserved << 1) +
                int(self.NS)) +
            to_octets(
                to_integer([int(f) for f in (
                    self.CWR, self.ECE,
                    self.URG, self.ACK,
                    self.PSH, self.RST,
                    self.SYN, self.FIN
                )], 1)
            ) +
            to_octets(self.window_size, 2) +
            to_octets(self.checksum, 2) + 
            to_octets(self.urgent_pointer, 2) +
            to_octets(self.options, (self.data_offset - 5) * 4) +
            bytes(self.payload)
        )
