import struct

readb = lambda r: struct.unpack('B', r.read(1))[0]
readh = lambda r: struct.unpack('H', r.read(2))[0]
readw = lambda r: struct.unpack('I', r.read(4))[0]

PROFILING = False

class LZ77:
	def __init__(self, rom):
		self.rom = rom
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
			# ~ input()
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

def deLZ77(rom):
	decomp = LZ77(rom)
	return decomp.decomp()

def deLZI(rom):
	decomp = LZI(rom)
	return decomp.decomp()

if __name__ == '__main__':
	import sys, romutil, re
	if len(sys.argv) != 5 or sys.argv[3] not in ('lz77', 'gblz'):
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
	else:
		dcmp = LZI(rom)
	dat = dcmp.decomp()[:400]
	import imutil
	im = imutil.make_image_2(dat, ((248,248,248,255),(96,248,88,255),(248,80,48,255),(0,0,0,255)), 5, True)
	im.save(fnout)
