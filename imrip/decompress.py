import struct

readb = lambda r: struct.unpack('B', r.read(1))[0]
readh = lambda r: struct.unpack('H', r.read(2))[0]
readw = lambda r: struct.unpack('I', r.read(4))[0]

PROFILING = False

class LZ77:
	def __init__(self, rom):
		self.rom = rom
		self.outbf = []
	def decomp(self):
		self._decomp()
		return b''.join([struct.pack('B', x) for x in self.outbf])

	def _decomp(self):
		hdr = readw(self.rom)
		chk = hdr & 0xff
		uln = hdr >> 8
		if chk != 0x10:
			print('Decomp error, not compressed data')
			return None
		self.outbf = [0] * uln
		wrt = 0
		while wrt < uln:
			flg = readb(self.rom)
			for i in range(8):
				curbit = flg & (0x80 >> i)
				if curbit:
					# compressed
					val = readh(self.rom)
					disp = ((val & 0xf) << 8) | (val >> 8)
					n = (val >> 4) & 0xf
					for j in range(n + 3):
						self.outbf[wrt] = self.outbf[wrt - disp - 1]
						wrt += 1
				else:
					val = readb(self.rom)
					self.outbf[wrt] = val
					wrt += 1
				if wrt >= uln:
					return
		return

class LZI:
	LZ_END       = 0b1111_1111
	LZ_LONG      = 0b1110_0000

	LZ_CMD       = 0b1110_0000
	LZ_LEN       = 0b0001_1111
	LZ_LONG_HI   = 0b0000_0011
	LZ_RW        = 0b1000_0000

	LZ_LITERAL   = 0b0000_0000
	LZ_ITERATE   = 0b0010_0000
	LZ_ALTERNATE = 0b0100_0000
	LZ_ZERO      = 0b0110_0000
	LZ_REPEAT    = 0b1000_0000
	LZ_FLIP      = 0b1010_0000
	LZ_REVERSE   = 0b1100_0000
	def __init__(self, rom):
		self.rom = rom
		self.outbf = []
	def decomp(self):
		self._decomp()
		return b''.join([struct.pack('B', x) for x in self.outbf])

	def _decomp(self):
		self.outbf = []
		while True:
			cmd_raw = readb(self.rom)
			if cmd_raw == self.LZ_END:
				return
			if cmd_raw & self.LZ_LONG == self.LZ_LONG:
				# long
				cln = ((cmd_raw & self.LZ_LONG_HI) >> 8) + readb(self.rom) + 1
				cmd = (cmd_raw << 3) & self.LZ_CMD
			else:
				# short
				cln = (cmd_raw & self.LZ_LEN) + 1
				cmd = cmd_raw & self.LZ_CMD

			if cmd & self.LZ_RW:
				lookback = readb(self.rom)
				if lookback & 0x80:
					# negative
					pos = len(self.outbf)
					lk = lookback & 0x7f
					lk = lk ^ 0xff
					lk = 0xff00 + lk
					pos = (pos + lk) & 0xffff
					lookback = pos
				else:
					# positive
					lookback = (lookback << 8) + readb(self.rom)

			if PROFILING: print('='*80)
			if PROFILING: print(f'{cmd_raw:>3}  ${cmd_raw:0>2x}  %{cmd_raw:0>8b}')
			if cmd & self.LZ_RW:
				if PROFILING: print(f'{cmd}   {cln}   {lookback}')
			else:
				if PROFILING: print(f'{cmd}   {cln}')
			if cmd == self.LZ_LITERAL:
				for _ in range(cln):
					self.outbf.append(readb(self.rom))
					if PROFILING: print(f'{self.outbf[-1]:0>2x} ', end='')
				if PROFILING: print()
			elif cmd == self.LZ_ITERATE:
				bt = readb(self.rom)
				for _ in range(cln):
					self.outbf.append(bt)
					if PROFILING: print(f'{self.outbf[-1]:0>2x} ', end='')
				if PROFILING: print()
			elif cmd == self.LZ_ALTERNATE:
				bt1 = readb(self.rom)
				bt2 = readb(self.rom)
				for i in range(cln):
					if i & 1:
						self.outbf.append(bt2)
					else:
						self.outbf.append(bt1)
					if PROFILING: print(f'{self.outbf[-1]:0>2x} ', end='')
				if PROFILING: print()
			elif cmd == self.LZ_ZERO:
				for _ in range(cln):
					self.outbf.append(0)
					if PROFILING: print(f'{self.outbf[-1]:0>2x} ', end='')
				if PROFILING: print()
			elif cmd == self.LZ_REPEAT:
				for _ in range(cln):
					self.outbf.append(self.outbf[lookback])
					lookback += 1
					if PROFILING: print(f'{self.outbf[-1]:0>2x} ', end='')
				if PROFILING: print()
			elif cmd == self.LZ_FLIP:
				for _ in range(cln):
					byt = self.outbf[lookback]
					byt = f'{byt:0>8b}'[::-1]
					self.outbf.append(int(byt, 2))
					lookback += 1
					if PROFILING: print(f'{self.outbf[-1]:0>2x} ', end='')
				if PROFILING: print()
			elif cmd == self.LZ_REVERSE:
				for _ in range(cln):
					self.outbf.append(self.outbf[lookback])
					lookback -= 1
					if PROFILING: print(f'{self.outbf[-1]:0>2x} ', end='')
				if PROFILING: print()
			else:
				print('???')

class CompBoy:
	def __init__(self, rom):
		self.rom = rom
		self.outbf = []
		self.cur_byte = 0
		self.cur_bit = 0
	def decomp(self):
		self._decomp()
		return b''.join([struct.pack('B', x) for x in self.outbf])

	def plb(self, n=1):
		if n == 1:
			if self.cur_bit == 0:
				self.cur_bit = 8
				self.cur_byte = readb(self.rom)
			self.cur_bit -= 1
			bt = (self.cur_byte & (1 << self.cur_bit)) >> self.cur_bit
			return bt
		else:
			x = 0
			for i in range(n):
				b = self.plb()
				x = (x << 1) | b
			return x

	def plz(self):
		x = 0
		n = 0
		while True:
			b = self.plb()
			n += 1
			x = (x << 1) | b
			if b == 0:
				break
		return x, n

	def get_bitplane(self, w, h):
		self.bit_offset = 3
		self.pos = 0
		self.pos_cache = 0
		self.pos_xy = [0, 0]
		bf = [0] * 8 * w * h
		wp = w * 8
		hp = h * 8

		def write_bits(a):
			for _ in range(self.bit_offset):
				a <<= 2
			bf[self.pos] |= a

		def move_to_next_pos():
			if self.pos_xy[1] + 1 != hp:
				self.pos_xy[1] += 1
				self.pos += 1
				return False
			self.pos_xy[1] = 0
			if self.bit_offset != 0:
				self.bit_offset -= 1
				self.pos = self.pos_cache
				return False
			self.bit_offset = 3
			if self.pos_xy[0] + 8 != wp:
				self.pos_xy[0] += 8
				self.pos += 1
				self.pos_cache = self.pos
				return False
			return True

		cur_fun = self.plb()
		while True:
			if cur_fun == 0:
				m, n = self.plz()
				o = self.plb(n)
				amt = m + o + 1

				if PROFILING: print(f'RLE : 00 x {amt}\n    : {self.pos} -> {self.pos + amt}')

				for _ in range(amt):
					write_bits(0)
					if move_to_next_pos():
						return bf

			else:
				if PROFILING: print('dat : ', end='')
				if PROFILING: pos_store = self.pos
				while True:
					bt = self.plb(2)
					if bt == 0:
						break
					if PROFILING: print(f'{bt:0>2b} ', end='')
					write_bits(bt)
					if move_to_next_pos():
						return bf
				if PROFILING: print()
				if PROFILING: print(f'    : {pos_store} -> {self.pos}')
			cur_fun ^= 1

	def xor_pln(self, bf1, _bf2):
		bf2 = _bf2.copy()
		for i in range(len(bf1)):
			bf2[i] ^= bf1[i]
		return bf2

	def delta_pln(self, _bf, w, h):
		ht = h
		wi = w

		bf = _bf.copy()
		swap = lambda a: ((a << 4) & 0xF0) | ((a >> 4) & 0xF)

		self.pos_xy = [0, 0]
		self.pos = 0
		self.pos_cache = 0
		def diff_decode(last_bit, cur_byt):
			v = 0
			for _i in range(8):
				i = 7 - _i
				if cur_byt & (1 << i):
					last_bit ^= 1
				v |= (last_bit << i)
			return v

		last_bit = 0
		while True:
			cur_byt = diff_decode(last_bit, bf[self.pos])
			last_bit = cur_byt & 1
			bf[self.pos] = cur_byt
			self.pos += h * 8
			self.pos_xy[0] += 8
			if self.pos_xy[0] != w * 8:
				continue
			last_bit = 0
			self.pos_xy[0] = 0
			self.pos_xy[1] += 1
			if self.pos_xy[1] == h * 8:
				break
			self.pos_cache += 1
			self.pos = self.pos_cache
		return bf

	def _decomp(self):
		w = self.plb(4)
		h = self.plb(4)
		first_bitplane = self.plb()
		bf1 = self.get_bitplane(w, h)
		mode = self.plb()
		if mode:
			mode_1 = self.plb()
			mode = mode * 2 + mode_1 - 1
		bf2 = self.get_bitplane(w, h)

		if mode == 0 or mode == 2:
			bf2 = self.delta_pln(bf2, w, h)
		bf1 = self.delta_pln(bf1, w, h)
		if mode == 1 or mode == 2:
			bf2 = self.xor_pln(bf1, bf2)

		if first_bitplane == 0:
			store = bf1.copy()
			bf1 = bf2.copy()
			bf2 = store.copy()

		for b1, b2 in zip(bf1, bf2):
			self.outbf.append(b2)
			self.outbf.append(b1)

def deLZ77(rom):
	decomp = LZ77(rom)
	return decomp.decomp()

def deLZI(rom):
	decomp = LZI(rom)
	return decomp.decomp()

def deCompBoy(rom):
	decomp = CompBoy(rom)
	return decomp.decomp()

if __name__ == '__main__':
	import sys, romutil, re
	if len(sys.argv) != 5 or sys.argv[3] not in ('lz77', 'lzi', 'compboy'):
		print(f'usage: python {sys.argv[0]} filein address compmethod fileout')
		exit()
	fnin = sys.argv[1]
	cadr = sys.argv[2]
	mthd = sys.argv[3]
	fnout = sys.argv[4]
	rom = romutil.RomFile(fnin)
	# convert address
	m1 = re.match(r'(?:0x|\$)([0-9a-fA-F]*)', cadr)
	m2 = re.match(r'([0-9a-fA-F]{2}):([0-9a-fA-F]{4})', cadr)
	if m1:
		cadr = int(m1.groups()[0], 16)
	elif m2:
		bnk, adr = map(lambda x: int(x, 16), m2.groups())
		if bnk == 0:
			cadr = adr
		else:
			cadr = (bnk - 1) * 0x4000 + adr
	else:
		cadr = int(cadr)
	rom.seek(cadr)
	if mthd == 'lz77':
		dcmp = LZ77(rom)
	elif mthd == 'lzi':
		dcmp = LZI(rom)
	else:
		dcmp = CompBoy(rom)
	dat = dcmp.decomp()[:400]
	import imutil
	im = imutil.make_image_2(dat, ((248,248,248,255),(96,248,88,255),(248,80,48,255),(0,0,0,255)), 5, True)
	im.save(fnout)
