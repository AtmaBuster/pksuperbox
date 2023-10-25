import struct

def peek(f, n):
	s = f.tell()
	d = f.read(n)
	f.seek(s)
	return d

rb = lambda r: struct.unpack('B', r.read(1))[0]
rh = lambda r: struct.unpack('H', r.read(2))[0]
rw = lambda r: struct.unpack('I', r.read(4))[0]
rhe = lambda r: struct.unpack('>H', r.read(2))[0]
rwe = lambda r: struct.unpack('>I', r.read(4))[0]

wb = lambda r, x: r.write(struct.pack('B', x))
wh = lambda r, x: r.write(struct.pack('H', x))
ww = lambda r, x: r.write(struct.pack('I', x))

gb = lambda b, i: struct.unpack('B', b[i:i+1])[0]
gh = lambda b, i: struct.unpack('H', b[i:i+2])[0]
gw = lambda b, i: struct.unpack('I', b[i:i+4])[0]
ghe = lambda b, i: struct.unpack('>H', b[i:i+2])[0]
gwe = lambda b, i: struct.unpack('>I', b[i:i+4])[0]

eb = lambda x: struct.pack('B', x)
eh = lambda x: struct.pack('H', x)
ew = lambda x: struct.pack('I', x)
ehe = lambda x: struct.pack('>H', x)
ewe = lambda x: struct.pack('>I', x)

def s2b(s):
	b = b''
	if ' ' in s:
		for i in s.split(' '):
			h = int(i, 16)
			b += struct.pack('B', h)
	else:
		for i in range(0, len(s), 2):
			h = int(s[i:i+2], 16)
			b += struct.pack('B', h)
	return b

def b2s(b):
	return ' '.join([f'{x:0>2X}' for x in b])

def sum_b(b, z):
	assert len(b) % z == 0
	typ = 'BH_I'[z-1]
	assert typ != '_'
	typ *= len(b) // z
	s = sum(struct.unpack(typ, b))
	return s & ((1 << (z * 8)) - 1)

def xor_b(b, k, z):
	assert len(b) % z == 0
	typ = 'BH_I'[z-1]
	assert typ != '_'
	typ *= len(b) // z
	nums = struct.unpack(typ, b)
	nums = [x ^ k for x in nums]
	out = struct.pack(typ, *nums)
	return out

def bitct(i):
	c = 0
	while i:
		if i & 1:
			c += 1
		i >>= 1
	return c

a2gb = lambda a: f'{a // 0x4000:0>2X}:{(a % 0x4000) + (int((a // 0x4000) != 0) * 0x4000):0>4X}'
a2ba = lambda a: (a // 0x4000, (a % 0x4000) + (int((a // 0x4000) != 0) * 0x4000))
gb2a = lambda s: int(s.split(':')[0], 16) * 0x4000 + int(s.split(':')[1], 16) - 0x4000 * int(int(s.split(':')[0], 16) != 0)
ba2a = lambda b,a: b * 0x4000 + a - 0x4000 * int(b != 0)

# not byte-related, but oh well
ROMAJILIST = (
	('a', 'あかさたなはまやらわがざだばぱ', '_kstnhmyrwgzdbp'),
	('i', 'いきしちにひみ＿り＿ぎじぢびぴ', '_kstnhmyrwgzdbp'),
	('u', 'うくすつぬふむゆる＿ぐずぢぶぷ', '_kstnhmyrwgzdbp'),
	('e', 'えけせてねへめ＿れ＿げぜでべぺ', '_kstnhmyrwgzdbp'),
	('o', 'おこそとのほもよろをごぞどぼぽ', '_kstnhmyrwgzdbp'),
	('A', 'アカサタナハマヤラワガザダバパ', '_KSTNHMYRWGZDBP'),
	('I', 'イキシチニヒミ＿リ＿ギジヂビピ', '_KSTNHMYRWGZDBP'),
	('U', 'ウクスツㇴフムユル＿グズヅブプ', '_KSTNHMYRWGZDBP'),
	('E', 'エケセテネヘメ＿レ＿ゲゼデベペ', '_KSTNHMYRWGZDBP'),
	('O', 'オコソトノホモヨロヲゴゾドボポ', '_KSTNHMYRWGZDBP'),
)
ROMAJIDIRECT = (
	'んンぁぃぅぇぉァィゥェォーゃゅょャュョ',
	('n','N','a','i','u','e','o','A','I','U','E','O','-','ya','yu','yo','YA','YU','YO'),
)
def getromaji(c):
	for l in ROMAJILIST:
		if c in l[1]:
			i = l[1].index(c)
			if l[2][i] == '_':
				return l[0]
			return l[2][i] + l[0]
	return None
def kana2romaji(s):
	so = ''
	for c in s:
		g = getromaji(c)
		if c in ROMAJIDIRECT[0]:
			i = ROMAJIDIRECT[0].index(c)
			so += ROMAJIDIRECT[1][i]
		elif g:
			so += g
		else:
			so += c
	return so
