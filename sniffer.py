#!/usr/bin/python
#
# sniffer.py - Feathercoin P2P Network Sniffer
# Modifications to connect to a Feathercoin node has been made by Michael Harrison.
# 
# 
# 
# This is a fork of https://github.com/sebicas/bitcoin-sniffer by @sebicas
#
# This is a Fork of pynode mininode from jgarzik ( https://github.com/jgarzik/pynode )
# But since his version is a little know branch with in pynode I dedided to keep my
# Fork but contribute my changes to his repository.
#
# Distributed under the MIT/X11 software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.



import struct
import socket
import asyncore
import binascii
import time
import sys
import re
import random
import cStringIO
import hashlib
import os;
import httplib;

SNIFFER_VERSION = "0.0.2"

MY_VERSION = 60003
MY_SUBVERSION = ".4"

# Default Settings if no configuration file is given
settings = {
	"host": "127.0.0.1",
	"port": 9336,
	"debug": False,
	"type": 2, # 1 for app 2 for post
	"url" : "http://localhost",
	"page" : "api",
	"app" : "Path"
}

def new_block_event(block):
	if block.is_valid():
		print "\n - Valid Block: %s" % block.hash
	else:
		print "\n - Invalid Block: %s" % block.hash

def new_transaction_event(tx):
	if tx.is_valid():
		print "\n - Valid TX: %s\n" % tx.hash
		for txout in tx.vout:
			print "     To: %s FTC: %.8f" % (txout.address, txout.amount)
			if settings["type"] == 1:
				os.system( settings["app"] +" " + txout.address + " " + str(txout.amount));
			else:
				#try:
				  print "Url %s" % settings["url"]
				  print "/%s" % settings["page"]
				  conn = httplib.HTTPConnection("127.0.0.1", 8080);
				  conn.request("GET",settings["url"]+"/"+settings["page"]+"?address=" + str(txout.address) + "&amount=" + str(txout.amount));
				#except:
				#  pass #server is probably down
		
	else:
		print "\n - Invalid TX: %s" % tx.hash

def sha256(s):
	return hashlib.new('sha256', s).digest()

def hash256(s):
	return sha256(sha256(s))

def b58encode(v):
	b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
	long_value = 0L
	for (i, c) in enumerate(v[::-1]):
		long_value += (256**i) * ord(c)
	result = ''
	while long_value >= 58:
		div, mod = divmod(long_value, 58)
		result = b58chars[mod] + result
		long_value = div
	result = b58chars[long_value] + result
	nPad = 0
	for c in v:
		if c == '\0': nPad += 1
		else: break
	return (b58chars[0]*nPad) + result

def hash_160_to_bc_address(h160, version="\x00"):
	vh160 = version + h160
	h3 = hash256(vh160)
	addr = vh160 + h3[0:4]
	return b58encode(addr)

def deser_string(f):
	nit = struct.unpack("<B", f.read(1))[0]
	if nit == 253:
		nit = struct.unpack("<H", f.read(2))[0]
	elif nit == 254:
		nit = struct.unpack("<I", f.read(4))[0]
	elif nit == 255:
		nit = struct.unpack("<Q", f.read(8))[0]
	return f.read(nit)

def ser_string(s):
	if len(s) < 253:
		return chr(len(s)) + s
	elif len(s) < 0x10000:
		return chr(253) + struct.pack("<H", len(s)) + s
	elif len(s) < 0x100000000L:
		return chr(254) + struct.pack("<I", len(s)) + s
	return chr(255) + struct.pack("<Q", len(s)) + s

def deser_uint256(f):
	r = 0L
	for i in xrange(8):
		t = struct.unpack("<I", f.read(4))[0]
		r += t << (i * 32)
	return r

def ser_uint256(u):
	rs = ""
	for i in xrange(8):
		rs += struct.pack("<I", u & 0xFFFFFFFFL)
		u >>= 32
	return rs

def uint256_from_str(s):
	r = 0L
	t = struct.unpack("<IIIIIIII", s[:32])
	for i in xrange(8):
		r += t[i] << (i * 32)
	return r

def uint256_from_compact(c):
	nbytes = (c >> 24) & 0xFF
	v = (c & 0xFFFFFFL) << (8 * (nbytes - 3))
	return v

def deser_vector(f, c):
	nit = struct.unpack("<B", f.read(1))[0]
	if nit == 253:
		nit = struct.unpack("<H", f.read(2))[0]
	elif nit == 254:
		nit = struct.unpack("<I", f.read(4))[0]
	elif nit == 255:
		nit = struct.unpack("<Q", f.read(8))[0]
	r = []
	for i in xrange(nit):
		t = c()
		t.deserialize(f)
		r.append(t)
	return r

def ser_vector(l):
	r = ""
	if len(l) < 253:
		r = chr(len(l))
	elif len(l) < 0x10000:
		r = chr(253) + struct.pack("<H", len(l))
	elif len(l) < 0x100000000L:
		r = chr(254) + struct.pack("<I", len(l))
	else:
		r = chr(255) + struct.pack("<Q", len(l))
	for i in l:
		r += i.serialize()
	return r

def deser_uint256_vector(f):
	nit = struct.unpack("<B", f.read(1))[0]
	if nit == 253:
		nit = struct.unpack("<H", f.read(2))[0]
	elif nit == 254:
		nit = struct.unpack("<I", f.read(4))[0]
	elif nit == 255:
		nit = struct.unpack("<Q", f.read(8))[0]
	r = []
	for i in xrange(nit):
		t = deser_uint256(f)
		r.append(t)
	return r

def ser_uint256_vector(l):
	r = ""
	if len(l) < 253:
		r = chr(len(l))
	elif len(s) < 0x10000:
		r = chr(253) + struct.pack("<H", len(l))
	elif len(s) < 0x100000000L:
		r = chr(254) + struct.pack("<I", len(l))
	else:
		r = chr(255) + struct.pack("<Q", len(l))
	for i in l:
		r += ser_uint256(i)
	return r

def deser_string_vector(f):
	nit = struct.unpack("<B", f.read(1))[0]
	if nit == 253:
		nit = struct.unpack("<H", f.read(2))[0]
	elif nit == 254:
		nit = struct.unpack("<I", f.read(4))[0]
	elif nit == 255:
		nit = struct.unpack("<Q", f.read(8))[0]
	r = []
	for i in xrange(nit):
		t = deser_string(f)
		r.append(t)
	return r

def ser_string_vector(l):
	r = ""
	if len(l) < 253:
		r = chr(len(l))
	elif len(s) < 0x10000:
		r = chr(253) + struct.pack("<H", len(l))
	elif len(s) < 0x100000000L:
		r = chr(254) + struct.pack("<I", len(l))
	else:
		r = chr(255) + struct.pack("<Q", len(l))
	for sv in l:
		r += ser_string(sv)
	return r

def deser_int_vector(f):
	nit = struct.unpack("<B", f.read(1))[0]
	if nit == 253:
		nit = struct.unpack("<H", f.read(2))[0]
	elif nit == 254:
		nit = struct.unpack("<I", f.read(4))[0]
	elif nit == 255:
		nit = struct.unpack("<Q", f.read(8))[0]
	r = []
	for i in xrange(nit):
		t = struct.unpack("<i", f.read(4))[0]
		r.append(t)
	return r

def ser_int_vector(l):
	r = ""
	if len(l) < 253:
		r = chr(len(l))
	elif len(s) < 0x10000:
		r = chr(253) + struct.pack("<H", len(l))
	elif len(s) < 0x100000000L:
		r = chr(254) + struct.pack("<I", len(l))
	else:
		r = chr(255) + struct.pack("<Q", len(l))
	for i in l:
		r += struct.pack("<i", i)
	return r

def show_debug_msg(msg):
	if settings['debug']:
		print "DEBUG: " + msg

class CAddress(object):
	def __init__(self):
		self.nServices = 1
		self.pchReserved = "\x00" * 10 + "\xff" * 2
		self.ip = "0.0.0.0"
		self.port = 0
	def deserialize(self, f):
		self.nServices = struct.unpack("<Q", f.read(8))[0]
		self.pchReserved = f.read(12)
		self.ip = socket.inet_ntoa(f.read(4))
		self.port = struct.unpack(">H", f.read(2))[0]
	def serialize(self):
		r = ""
		r += struct.pack("<Q", self.nServices)
		r += self.pchReserved
		r += socket.inet_aton(self.ip)
		r += struct.pack(">H", self.port)
		return r
	def __repr__(self):
		return "CAddress(nServices=%i ip=%s port=%i)" % (self.nServices, self.ip, self.port)

class CInv(object):
	typemap = {
		0: "Error",
		1: "TX",
		2: "Block"}
	def __init__(self):
		self.type = 0
		self.hash = 0L
	def deserialize(self, f):
		self.type = struct.unpack("<i", f.read(4))[0]
		self.hash = deser_uint256(f)
	def serialize(self):
		r = ""
		r += struct.pack("<i", self.type)
		r += ser_uint256(self.hash)
		return r
	def __repr__(self):
		return "CInv(type=%s hash=%064x)" % (self.typemap[self.type], self.hash)

class CBlockLocator(object):
	def __init__(self):
		self.nVersion = MY_VERSION
		self.vHave = []
	def deserialize(self, f):
		self.nVersion = struct.unpack("<i", f.read(4))[0]
		self.vHave = deser_uint256_vector(f)
	def serialize(self):
		r = ""
		r += struct.pack("<i", self.nVersion)
		r += ser_uint256_vector(self.vHave)
		return r
	def __repr__(self):
		return "CBlockLocator(nVersion=%i vHave=%s)" % (self.nVersion, repr(self.vHave))

class COutPoint(object):
	def __init__(self):
		self.hash = 0
		self.n = 0
	def deserialize(self, f):
		self.hash = deser_uint256(f)
		self.n = struct.unpack("<I", f.read(4))[0]
	def serialize(self):
		r = ""
		r += ser_uint256(self.hash)
		r += struct.pack("<I", self.n)
		return r
	def __repr__(self):
		return "COutPoint(hash=%064x n=%i)" % (self.hash, self.n)

class CTxIn(object):
	def __init__(self):
		self.prevout = COutPoint()
		self.scriptSig = ""
		self.nSequence = 0
	def deserialize(self, f):
		self.prevout = COutPoint()
		self.prevout.deserialize(f)
		self.scriptSig = deser_string(f)
		self.nSequence = struct.unpack("<I", f.read(4))[0]
	def serialize(self):
		r = ""
		r += self.prevout.serialize()
		r += ser_string(self.scriptSig)
		r += struct.pack("<I", self.nSequence)
		return r
	def __repr__(self):
		return "CTxIn(prevout=%s scriptSig=%s nSequence=%i)" % (repr(self.prevout), binascii.hexlify(self.scriptSig), self.nSequence)

class CTxOut(object):
	def __init__(self):
		self.nValue = 0
		self.scriptPubKey = ""
		self.amount = 0
	def deserialize(self, f):
		self.nValue = struct.unpack("<q", f.read(8))[0]
		self.scriptPubKey = deser_string(f)
		self.amount = float(self.nValue / 1e8)
		self.address = self.build_address()
	def build_address(self):
		return hash_160_to_bc_address(self.scriptPubKey[3:23])
	def serialize(self):
		r = ""
		r += struct.pack("<q", self.nValue)
		r += ser_string(self.scriptPubKey)
		return r
	def __repr__(self):
		return "CTxOut(nValue=%i.%08i scriptPubKey=%s)" % (self.nValue // 100000000, self.nValue % 100000000, binascii.hexlify(self.scriptPubKey))

class CTransaction(object):
	def __init__(self):
		self.nVersion = 1
		self.vin = []
		self.vout = []
		self.nLockTime = 0
		self.sha256 = None
		self.hash = None
	def deserialize(self, f):
		self.nVersion = struct.unpack("<i", f.read(4))[0]
		self.vin = deser_vector(f, CTxIn)
		self.vout = deser_vector(f, CTxOut)
		self.nLockTime = struct.unpack("<I", f.read(4))[0]
	def serialize(self):
		r = ""
		r += struct.pack("<i", self.nVersion)
		r += ser_vector(self.vin)
		r += ser_vector(self.vout)
		r += struct.pack("<I", self.nLockTime)
		return r
	def calc_sha256(self):
		if self.sha256 is None:
			self.sha256 = uint256_from_str(hash256(self.serialize()))
		self.hash = hash256(self.serialize())[::-1].encode('hex_codec')
	def is_valid(self):
		self.calc_sha256()
		for tout in self.vout:
			if tout.nValue < 0 or tout.nValue > 21000000L * 100000000L:
				return False
		return True
	def __repr__(self):
		return "CTransaction(nVersion=%i vin=%s vout=%s nLockTime=%i)" % (self.nVersion, repr(self.vin), repr(self.vout), self.nLockTime)

class CBlock(object):
	def __init__(self):
		self.nVersion = 1
		self.hashPrevBlock = 0
		self.hashMerkleRoot = 0
		self.nTime = 0
		self.nBits = 0
		self.nNonce = 0
		self.vtx = []
		self.sha256 = None
		self.hash = None
	def deserialize(self, f):
		self.nVersion = struct.unpack("<i", f.read(4))[0]
		self.hashPrevBlock = deser_uint256(f)
		self.hashMerkleRoot = deser_uint256(f)
		self.nTime = struct.unpack("<I", f.read(4))[0]
		self.nBits = struct.unpack("<I", f.read(4))[0]
		self.nNonce = struct.unpack("<I", f.read(4))[0]
		self.vtx = deser_vector(f, CTransaction)
	def serialize(self):
		r = ""
		r += struct.pack("<i", self.nVersion)
		r += ser_uint256(self.hashPrevBlock)
		r += ser_uint256(self.hashMerkleRoot)
		r += struct.pack("<I", self.nTime)
		r += struct.pack("<I", self.nBits)
		r += struct.pack("<I", self.nNonce)
		r += ser_vector(self.vtx)
		return r
	def calc_sha256(self):
		if self.sha256 is None:
			r = ""
			r += struct.pack("<i", self.nVersion)
			r += ser_uint256(self.hashPrevBlock)
			r += ser_uint256(self.hashMerkleRoot)
			r += struct.pack("<I", self.nTime)
			r += struct.pack("<I", self.nBits)
			r += struct.pack("<I", self.nNonce)
			self.sha256 = uint256_from_str(hash256(r))
			self.hash = hash256(r)[::-1].encode('hex_codec')
	def is_valid(self):
		self.calc_sha256()
		target = uint256_from_compact(self.nBits)
		if self.sha256 > target:
			return False
		hashes = []
		for tx in self.vtx:
			if not tx.is_valid():
				return False
			tx.calc_sha256()
			hashes.append(ser_uint256(tx.sha256))
		while len(hashes) > 1:
			newhashes = []
			for i in xrange(0, len(hashes), 2):
				i2 = min(i+1, len(hashes)-1)
				newhashes.append(hash256(hashes[i] + hashes[i2]))
			hashes = newhashes
		if uint256_from_str(hashes[0]) != self.hashMerkleRoot:
			return False
		return True
	def __repr__(self):
		return "CBlock(nVersion=%i hashPrevBlock=%064x hashMerkleRoot=%064x nTime=%s nBits=%08x nNonce=%08x vtx=%s)" % (self.nVersion, self.hashPrevBlock, self.hashMerkleRoot, time.ctime(self.nTime), self.nBits, self.nNonce, repr(self.vtx))

class CUnsignedAlert(object):
	def __init__(self):
		self.nVersion = 1
		self.nRelayUntil = 0
		self.nExpiration = 0
		self.nID = 0
		self.nCancel = 0
		self.setCancel = []
		self.nMinVer = 0
		self.nMaxVer = 0
		self.setSubVer = []
		self.nPriority = 0
		self.strComment = ""
		self.strStatusBar = ""
		self.strReserved = ""
	def deserialize(self, f):
		self.nVersion = struct.unpack("<i", f.read(4))[0]
		self.nRelayUntil = struct.unpack("<q", f.read(8))[0]
		self.nExpiration = struct.unpack("<q", f.read(8))[0]
		self.nID = struct.unpack("<i", f.read(4))[0]
		self.nCancel = struct.unpack("<i", f.read(4))[0]
		self.setCancel = deser_int_vector(f)
		self.nMinVer = struct.unpack("<i", f.read(4))[0]
		self.nMaxVer = struct.unpack("<i", f.read(4))[0]
		self.setSubVer = deser_string_vector(f)
		self.nPriority = struct.unpack("<i", f.read(4))[0]
		self.strComment = deser_string(f)
		self.strStatusBar = deser_string(f)
		self.strReserved = deser_string(f)
	def serialize(self):
		r = ""
		r += struct.pack("<i", self.nVersion)
		r += struct.pack("<q", self.nRelayUntil)
		r += struct.pack("<q", self.nExpiration)
		r += struct.pack("<i", self.nID)
		r += struct.pack("<i", self.nCancel)
		r += ser_int_vector(self.setCancel)
		r += struct.pack("<i", self.nMinVer)
		r += struct.pack("<i", self.nMaxVer)
		r += ser_string_vector(self.setSubVer)
		r += struct.pack("<i", self.nPriority)
		r += ser_string(self.strComment)
		r += ser_string(self.strStatusBar)
		r += ser_string(self.strReserved)
		return r
	def __repr__(self):
		return "CUnsignedAlert(nVersion %d, nRelayUntil %d, nExpiration %d, nID %d, nCancel %d, nMinVer %d, nMaxVer %d, nPriority %d, strComment %s, strStatusBar %s, strReserved %s)" % (self.nVersion, self.nRelayUntil, self.nExpiration, self.nID, self.nCancel, self.nMinVer, self.nMaxVer, self.nPriority, self.strComment, self.strStatusBar, self.strReserved)

class CAlert(object):
	def __init__(self):
		self.vchMsg = ""
		self.vchSig = ""
	def deserialize(self, f):
		self.vchMsg = deser_string(f)
		self.vchSig = deser_string(f)
	def serialize(self):
		r = ""
		r += ser_string(self.vchMsg)
		r += ser_string(self.vchSig)
		return r
	def __repr__(self):
		return "CAlert(vchMsg.sz %d, vchSig.sz %d)" % (len(self.vchMsg), len(self.vchSig))

class msg_version(object):
	command = "version"
	def __init__(self):
		self.nVersion = MY_VERSION
		self.nServices = 1
		self.nTime = time.time()
		self.addrTo = CAddress()
		self.addrFrom = CAddress()
		self.nNonce = random.getrandbits(64)
		self.strSubVer = MY_SUBVERSION
		self.nStartingHeight = -1
	def deserialize(self, f):
		self.nVersion = struct.unpack("<i", f.read(4))[0]
		if self.nVersion == 10300:
			self.nVersion = 300
		self.nServices = struct.unpack("<Q", f.read(8))[0]
		self.nTime = struct.unpack("<q", f.read(8))[0]
		self.addrTo = CAddress()
		self.addrTo.deserialize(f)
		if self.nVersion >= 106:
			self.addrFrom = CAddress()
			self.addrFrom.deserialize(f)
			self.nNonce = struct.unpack("<Q", f.read(8))[0]
			self.strSubVer = deser_string(f)
			if self.nVersion >= 60003:
				self.nStartingHeight = struct.unpack("<i", f.read(4))[0]
			else:
				self.nStartingHeight = None
		else:
			self.addrFrom = None
			self.nNonce = None
			self.strSubVer = None
			self.nStartingHeight = None
	def serialize(self):
		r = ""
		r += struct.pack("<i", self.nVersion)
		r += struct.pack("<Q", self.nServices)
		r += struct.pack("<q", self.nTime)
		r += self.addrTo.serialize()
		r += self.addrFrom.serialize()
		r += struct.pack("<Q", self.nNonce)
		r += ser_string(self.strSubVer)
		r += struct.pack("<i", self.nStartingHeight)
		return r
	def __repr__(self):
		return "msg_version(nVersion=%i nServices=%i nTime=%s addrTo=%s addrFrom=%s nNonce=0x%016X strSubVer=%s nStartingHeight=%i)" % (self.nVersion, self.nServices, time.ctime(self.nTime), repr(self.addrTo), repr(self.addrFrom), self.nNonce, self.strSubVer, self.nStartingHeight)

class msg_verack(object):
	command = "verack"
	def __init__(self):
		pass
	def deserialize(self, f):
		pass
	def serialize(self):
		return ""
	def __repr__(self):
		return "msg_verack()"

class msg_addr(object):
	command = "addr"
	def __init__(self):
		self.addrs = []
	def deserialize(self, f):
		self.addrs = deser_vector(f, CAddress)
	def serialize(self):
		return ser_vector(self.addrs)
	def __repr__(self):
		return "msg_addr(addrs=%s)" % (repr(self.addrs))

class msg_alert(object):
	command = "alert"
	def __init__(self):
		self.alert = CAlert()
	def deserialize(self, f):
		self.alert = CAlert()
		self.alert.deserialize(f)
	def serialize(self):
		r = ""
		r += self.alert.serialize()
		return r
	def __repr__(self):
		return "msg_alert(alert=%s)" % (repr(self.alert), )

class msg_inv(object):
	command = "inv"
	def __init__(self):
		self.inv = []
	def deserialize(self, f):
		self.inv = deser_vector(f, CInv)
	def serialize(self):
		return ser_vector(self.inv)
	def __repr__(self):
		return "msg_inv(inv=%s)" % (repr(self.inv))

class msg_getdata(object):
	command = "getdata"
	def __init__(self):
		self.inv = []
	def deserialize(self, f):
		self.inv = deser_vector(f, CInv)
	def serialize(self):
		return ser_vector(self.inv)
	def __repr__(self):
		return "msg_getdata(inv=%s)" % (repr(self.inv))

class msg_getblocks(object):
	command = "getblocks"
	def __init__(self):
		self.locator = CBlockLocator()
		self.hashstop = 0L
	def deserialize(self, f):
		self.locator = CBlockLocator()
		self.locator.deserialize(f)
		self.hashstop = deser_uint256(f)
	def serialize(self):
		r = ""
		r += self.locator.serialize()
		r += ser_uint256(self.hashstop)
		return r
	def __repr__(self):
		return "msg_getblocks(locator=%s hashstop=%064x)" % (repr(self.locator), self.hashstop)

class msg_tx(object):
	command = "tx"
	def __init__(self):
		self.tx = CTransaction()
	def deserialize(self, f):
		self.tx.deserialize(f)
	def serialize(self):
		return self.tx.serialize()
	def __repr__(self):
		return "msg_tx(tx=%s)" % (repr(self.tx))

class msg_block(object):
	command = "block"
	def __init__(self):
		self.block = CBlock()
	def deserialize(self, f):
		self.block.deserialize(f)
	def serialize(self):
		return self.block.serialize()
	def __repr__(self):
		return "msg_block(block=%s)" % (repr(self.block))

class msg_getaddr(object):
	command = "getaddr"
	def __init__(self):
		pass
	def deserialize(self, f):
		pass
	def serialize(self):
		return ""
	def __repr__(self):
		return "msg_getaddr()"

#msg_checkorder
#msg_submitorder
#msg_reply

class msg_ping(object):
	command = "ping"
	def __init__(self):
		pass
	def deserialize(self, f):
		pass
	def serialize(self):
		return ""
	def __repr__(self):
		return "msg_ping()"

class NodeConn(asyncore.dispatcher):
	messagemap = {
		"version": msg_version,
		"verack": msg_verack,
		"addr": msg_addr,
		"alert": msg_alert,
		"inv": msg_inv,
		"getdata": msg_getdata,
		"getblocks": msg_getblocks,
		"tx": msg_tx,
		"block": msg_block,
		"getaddr": msg_getaddr,
		"ping": msg_ping
	}
	def __init__(self, dstaddr, dstport):
		asyncore.dispatcher.__init__(self)
		self.dstaddr = dstaddr
		self.dstport = dstport
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sendbuf = ""
		self.recvbuf = ""
		self.ver_send = 60003
		self.ver_recv = 60003
		self.last_sent = 0
		self.state = "connecting"

		#stuff version msg into sendbuf
		vt = msg_version()
		vt.addrTo.ip = self.dstaddr
		vt.addrTo.port = self.dstport
		vt.addrFrom.ip = "0.0.0.0"
		vt.addrFrom.port = 0
		self.send_message(vt, True)
		print "\n Feathercoin Network Sniffer v" + SNIFFER_VERSION
		print " -------------------------------------------------------------------------"
		print " Connecting to Feathercoin Node IP # " + settings['host'] + ":" + str(settings['port'])
		try:
			self.connect((dstaddr, dstport))
		except:
			self.handle_close()
	def handle_connect(self):
		print " Connected & Sniffing :)\n"
		self.state = "connected"
	def handle_close(self):
		print " Closing Conection ... bye :)"
		self.state = "closed"
		self.recvbuf = ""
		self.sendbuf = ""
		try:
			self.close()
		except:
			pass
	def handle_read(self):
		try:
			t = self.recv(8192)
		except:
			self.handle_close()
			return
		if len(t) == 0:
			self.handle_close()
			return
		self.recvbuf += t
		self.got_data()
	def readable(self):
		return True
	def writable(self):
		return (len(self.sendbuf) > 0)
	def handle_write(self):
		try:
			sent = self.send(self.sendbuf)
		except:
			self.handle_close()
			return
		self.sendbuf = self.sendbuf[sent:]
	def got_data(self):
		while True:
			
			if len(self.recvbuf) < 4:
				return
			if self.recvbuf[:4] != "\xfb\xc0\xb6\xdb":
				raise ValueError("got garbage %s" % repr(self.recvbuf))
			if self.ver_recv < 60003:
				if len(self.recvbuf) < 4 + 12 + 4:
					return
				command = self.recvbuf[4:4+12].split("\x00", 1)[0]
				msglen = struct.unpack("<i", self.recvbuf[4+12:4+12+4])[0]
				checksum = None
				if len(self.recvbuf) < 4 + 12 + 4 + msglen:
					return
				msg = self.recvbuf[4+12+4:4+12+4+msglen]
				self.recvbuf = self.recvbuf[4+12+4+msglen:]
			else:
				if len(self.recvbuf) < 4 + 12 + 4 + 4:
					return
				command = self.recvbuf[4:4+12].split("\x00", 1)[0]
				msglen = struct.unpack("<i", self.recvbuf[4+12:4+12+4])[0]
				checksum = self.recvbuf[4+12+4:4+12+4+4]
				if len(self.recvbuf) < 4 + 12 + 4 + 4 + msglen:
					return
				msg = self.recvbuf[4+12+4+4:4+12+4+4+msglen]
				th = sha256(msg)
				h = sha256(th)
				if checksum != h[:4]:
					raise ValueError("got bad checksum %s" % repr(self.recvbuf))
				self.recvbuf = self.recvbuf[4+12+4+4+msglen:]
			if command in self.messagemap:
				f = cStringIO.StringIO(msg)
				t = self.messagemap[command]()
				t.deserialize(f)
				self.got_message(t)
			else:
				show_debug_msg("Unknown command: '" + command + "' " + repr(msg))
	def send_message(self, message, pushbuf=False):
		if self.state != "connected" and not pushbuf:
			return
		show_debug_msg("Send %s" % repr(message))
		command = message.command
		data = message.serialize()
		tmsg = "\xfb\xc0\xb6\xdb"
		tmsg += command
		tmsg += "\x00" * (12 - len(command))
		tmsg += struct.pack("<I", len(data))
		if self.ver_send >= 60003:
			th = sha256(data)
			h = sha256(th)
			tmsg += h[:4]
		tmsg += data
		self.sendbuf += tmsg
		self.last_sent = time.time()
	def got_message(self, message):
		
		if self.last_sent + 30 * 60 < time.time():
			self.send_message(msg_ping())
		show_debug_msg("Recv %s" % repr(message))
		if message.command  == "version":
			if message.nVersion >= 60003:
				self.send_message(msg_verack())
			self.ver_send = min(MY_VERSION, message.nVersion)
			if message.nVersion < 60003:
				self.ver_recv = self.ver_send
		elif message.command == "verack":
			self.ver_recv = self.ver_send
		elif message.command == "inv":
			want = msg_getdata()
			for i in message.inv:
				if i.type == 1:
					want.inv.append(i)
				elif i.type == 2:
					want.inv.append(i)
			if len(want.inv):
				self.send_message(want)
		elif message.command == "tx":
			new_transaction_event(message.tx)

		elif message.command == "block":
			new_block_event(message.block)

if __name__ == '__main__':
	if len(sys.argv) == 2:
		f = open(sys.argv[1])
		for line in f:
			m = re.search('^(\w+)\s*=\s*(\S.*)$', line)
			if m is None:
				continue
			settings[m.group(1)] = m.group(2)
		f.close()
	settings['port'] = int(settings['port'])
	c = NodeConn(settings['host'], settings['port'])
	asyncore.loop()