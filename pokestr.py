import by

gen1e_map = \
	'________________' +\
	'________________' +\
	'________________' +\
	'________________' +\
	'________________' +\
	'________________' +\
	'________________' +\
	'_______________ ' +\
	'ABCDEFGHIJKLMNOP' +\
	'QRSTUVWXYZ():;[]' +\
	'abcdefghijklmnop' +\
	'qrstuvwxyzé·¸»¼½' +\
	'ÄÖÜäöü__________' +\
	'________________' +\
	'\'´µ-__?!_______♂' +\
	'_¶./,♀0123456789'
def dec1e(s):
	if len(s) == 1 and s == b'\x5D' or len(s) >= 2 and s[0] == 0x5D and s[1] == 0x50:
		return 'TRAINER'
	so = ''
	for c in s:
		if c == 0x50:
			break
		cc = gen1e_map[c]
		if cc == '_':
			raise Exception(f'Decoding error : {c}, ${c:0>2X}')
		so += cc
	return so

def dec1j(s):
	pass

def enc1e(s,l=-1):
	bo = b''
	for c in s:
		if len(bo) == l:
			return bo
		if not c in gen1e_map:
			raise Exception(f'Encoding error : "{c}"')
		cc = gen1e_map.index(c)
		bo += by.eb(cc)
	if len(bo) == l:
		return bo
	bo += b'\x50'
	while len(bo) < l:
		bo += b'\x00'
	return bo

def enc1j(s):
	pass

# A-Za-z_
# -?!/.,
# ():;[]
# pk, mn, x		´µ¶

# 0-9
# male, female, &, e`
# 'd, 'l, 'm, 'r, 's, 't, 'v	·¸¹º»¼½
gen2e_map = \
	'________________' +\
	'_______________ ' +\
	'________________' +\
	'________________' +\
	'______________ _' +\
	'________________' +\
	'________________' +\
	'_______________ ' +\
	'ABCDEFGHIJKLMNOP' +\
	'QRSTUVWXYZ():;[]' +\
	'abcdefghijklmnop' +\
	'qrstuvwxyz______' +\
	'ÄÖÜäöü__________' +\
	'·¸¹º»¼½_1234567_' +\
	'\'´µ-__?!.&é____♂' +\
	'¥¶_/,♀0123456789'
def dec2e(s):
	so = ''
	for c in s:
		if c == 0x50:
			break
		cc = gen2e_map[c]
		if cc == '_':
			raise Exception(f'Decoding error : {c}, ${c:0>2X}')
		so += cc
	return so

def dec2j(s):
	pass

def enc2e(s,l=-1):
	bo = b''
	for c in s:
		if len(bo) == l:
			return bo
		if not c in gen2e_map:
			raise Exception(f'Encoding error : "{c}"')
		cc = gen2e_map.index(c)
		bo += by.eb(cc)
	if len(bo) == l:
		return bo
	bo += b'\x50'
	while len(bo) < l:
		bo += b'\x00'
	return bo

def enc2j(s):
	pass

gen3e_map = \
	' _______________' +\
	'___________é____' +\
	'_____________&__' +\
	'________________' +\
	'________________' +\
	'_____{}<=>_%()__' +\
	'________________' +\
	'________________' +\
	'________________' +\
	'________________' +\
	'_0123456789!?.-_' +\
	'…“”‘’♂♀_,_/ABCDE' +\
	'FGHIJKLMNOPQRSTU' +\
	'VWXYZabcdefghijk' +\
	'lmnopqrstuvwxyz_' +\
	':ÄÖÜäöü_______ _'
def dec3e(s):
	so = ''
	for c in s:
		if c == 0xff:
			break
		cc = gen3e_map[c]
		if cc == '_':
			raise Exception(f'Decoding error : {c}, ${c:0>2X}')
		so += cc
	return so

def enc3e(s,l=-1):
	bo = b''
	for c in s:
		if len(bo) == l:
			return bo
		if not c in gen3e_map:
			raise Exception(f'Encoding error : "{c}"')
		cc = gen3e_map.index(c)
		bo += by.eb(cc)
	if len(bo) == l:
		return bo
	bo += b'\xff'
	while len(bo) < l:
		bo += b'\x00'
	return bo

gen3j_map = \
	' あいうえおかきくけこさしすせそ' +\
	'たちつてとなにぬねのはひふへほま' +\
	'みむめもやゆよらりるれろわをんぁ' +\
	'ぃぅぇぉゃゅょがぎぐげござじずぜ' +\
	'ぞだぢづでどばびぶべぼぱぴぷぺぽ' +\
	'っアイウエオカキクケコサシスセソ' +\
	'タチツテトナニヌネノハヒフヘホマ' +\
	'ミムメモヤユヨラリルレロワヲンァ' +\
	'ィゥェォャュョガギグゲゴザジズゼ' +\
	'ゾダヂヅデドバビブベボパピプペポ' +\
	'ッ0123456789!?。ー・' +\
	'…『』「」♂♀_,_/ABCDE' +\
	'FGHIJKLMNOPQRSTU' +\
	'VWXYZabcdefghijk' +\
	'lmnopqrstuvwxyz_' +\
	'_ÄÖÜäöü'
def dec3j(s):
	so = ''
	for c in s:
		if c == 0xff:
			break
		cc = gen3j_map[c]
		if cc == '_':
			raise Exception(f'Decoding error : {c}, ${c:0>2X}')
		so += cc
	return so

def enc3j(s,l=-1):
	bo = b''
	for c in s:
		if len(bo) == l:
			return bo
		if not c in gen3j_map:
			raise Exception(f'Encoding error : "{c}"')
		cc = gen3j_map.index(c)
		bo += by.eb(cc)
	if len(bo) == l:
		return bo
	bo += b'\xff'
	while len(bo) < l:
		bo += b'\x00'
	return bo

if __name__ == '__main__':
	# ~ test_str = b'\xCE\xDC\xDD\xE7\x00\xDD\xE7\x00\xD5\x00\xCD\xCE\xCC\xC3\xC8\xC1\x00\xDA\xE3\xE6\x00\xE8\xD9\xE7\xE8\xDD\xE2\xDB\xAB\xFF'
	# ~ test_str = b'\xA1\xA2\xA3\xA4\xA5\xA6\xA7\xA8\xA8\xA9\xAA\xAB\xAC\xAD\xAE\xB0\xB1\xB2\xB3\xB4\xB5\xB6\xB8\xBA\xBB\xBC\xBD\xBE\xBF\xC0\xC1\xC2\xC3\xC4\xC5\xC6\xC7\xC8\xC9\xCA\xCB\xCC\xCD\xCE\xCF\xD0\xD1\xD2\xD3\xD4\xD5\xD6\xD7\xD8\xD9\xDA\xDB\xDC\xDD\xDE\xDF\xE0\xE1\xE2\xE3\xE4\xE5\xE6\xE7\xE8\xE9\xEA\xEB\xEC\xED\xEE\xF1\xF2\xF3\xF4\xF5\xF6\xFF'
	test_inp = 'This is a STRING for testing!'
	test_str = enc3e(test_inp)
	test_out = dec3e(test_str)
	test_bin = enc3e(test_out)
	print(test_inp)
	print(test_str)
	print(test_out)
	print(test_bin)
	print(test_inp == test_out, test_str == test_bin)
