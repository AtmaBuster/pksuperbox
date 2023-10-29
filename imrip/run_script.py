import imutil, decompress
import struct, os, re
from zlib import crc32
from PIL import Image, ImageDraw

OUT_DIR = '../'
# ~ OUT_DIR = './'

import shutil
shutil.copyfile('../gamedb.py', './gamedb.py')
shutil.copyfile('../pokedb.py', './pokedb.py')
import gamedb

readp = lambda r: struct.unpack('I', r.read(4))[0] - 0x8000000
readh = lambda r: struct.unpack('H', r.read(2))[0]
readb = lambda r: struct.unpack('B', r.read(1))[0]

def ba2a(b, a):
	x = a
	if b != 0:
		x -= 0x4000
	return x + b * 0x4000

def match_pair_token(queue, lt, rt):
	lv = 1
	out_queue = []
	while lv:
		nxt = queue.pop(0)
		if nxt == lt:
			lv += 1
		elif nxt == rt:
			lv -= 1
		if lv != 0:
			out_queue.append(nxt)
	return out_queue

def builtin_getdata(rom, args):
	assert len(args) in (1, 2)
	if len(args) == 1:
		game_hdr = gamedb.GAME_CRC[rom.crc]
		game_nam = game_hdr[0]
		game_dat = gamedb.GAME_DATA[game_nam]
	else:
		if args[1] == 'parent':
			game_hdr = gamedb.GAME_CRC[rom.crc]
			game_nam = game_hdr[0]
			game_dat = gamedb.GAME_DATA[game_nam]
			game_nam = game_dat['base_game']
			game_dat = gamedb.GAME_DATA[game_nam]
		else:
			game_dat = gamedb.GAME_DATA[args[1]]
	return game_dat[args[0]]

def builtin_lz77(rom, args):
	assert len(args) == 0
	return decompress.deLZ77(rom.f)

def builtin_lzi(rom, args):
	assert len(args) == 0
	return decompress.deLZI(rom.f)

def builtin_compboy(rom, args):
	assert len(args) == 0
	return decompress.deCompBoy(rom.f)

def builtin_len(rom, args):
	assert len(args) == 1
	return len(args[0])

def builtin_fread(rom, args):
	assert len(args) == 1
	return rom.f.read(args[0])

def builtin_int(rom, args):
	assert len(args) == 1
	val = args[0]
	if isinstance(val, bytes):
		x = 0
		for b in reversed(val):
			x <<= 8
			x += b
		return x
	return int(val)

def builtin_make3(rom, args):
	assert len(args) == 3
	im_raw = args[0]
	pal_raw = args[1]
	w = args[2]
	pal = imutil.pal_from_raw(pal_raw, True)
	im = imutil.make_image_3(im_raw, pal, w)
	return im

def builtin_make2(rom, args):
	assert len(args) == 4
	im_raw = args[0]
	pal_raw = args[1]
	w = args[2]
	t = args[3]
	pal = imutil.pal_from_raw(pal_raw, False)
	im_s = imutil.make_image_2(im_raw, pal, w, t)
	return im_s

def builtin_center2(rom, args):
	assert len(args) in (2, 3)
	im_i = args[0]
	if len(args) == 2:
		base_coord = (0, 0)
	else:
		sz = im_i.size
		if args[2] == 'nw':
			base_coord = (0, 0)
		elif args[2] == 'sw':
			base_coord = (0, sz[1] - 1)
		elif args[2] == 'ne':
			base_coord = (sz[0] - 1, 0)
		elif args[2] == 'se':
			base_coord = (sz[0] - 1, sz[1] - 1)
	w = args[1]
	col_base = im_i.load()[base_coord]
	im = Image.new('RGBA', (64, 64))
	im.paste(col_base, (0, 0, 64, 64))
	im.paste(im_i, (32 - w * 4, 60 - w * 8))
	pxl = im.load()
	return im

def builtin_fileout(rom, args):
	assert len(args) == 3
	bas = args[0]
	val = args[1]
	nam = args[2]
	if bas == 'mon':
		path = OUT_DIR + f'assets/image/mon/{bas}{val:0>3}/'
	elif bas == 'unown':
		path = OUT_DIR + f'assets/image/mon/mon201/'
		nam = nam.format(val)
	else:
		path = OUT_DIR + f'assets/image/mon/{bas}/'
	return path, path + nam

def builtin_array(rom, args):
	return tuple(args)

def builtin_list(rom, args):
	return [*args]

def builtin_dict(rom, args):
	assert len(args) == 0
	return {}

def builtin_sdict(rom, args):
	assert len(args) == 3
	d, k, v = args
	d[k] = v

def builtin_indkey(rom, args):
	assert len(args) == 2
	d, k = args
	return k in d.keys()

def builtin_checkhit(rom, args):
	assert len(args) == 2
	hit = args[0]
	ind = args[1]
	return hit.get(ind)

def builtin_char(rom, args):
	assert len(args) == 1
	return chr(args[0])

def builtin_bpp12(rom, args):
	assert len(args) == 1
	return imutil.conv1bpp2bpp(args[0])

def builtin_bpp24(rom, args):
	assert len(args) == 1
	return imutil.conv2bpp4bpp(args[0])

def builtin_bpp14(rom, args):
	assert len(args) == 1
	return imutil.conv1bpp4bpp(args[0])

def builtin_bytes(rom, args):
	b = b''
	for i in args:
		b += struct.pack('B', i)
	return b

def builtin_make1bpp(rom, args):
	assert len(args) == 3
	im_raw = args[0]
	pal_raw = args[1]
	w = args[2]
	pal = imutil.pal_from_raw(pal_raw, True)
	im = imutil.make_image_1bpp(im_raw, pal, w)
	return im

def builtin_revbits(rom, args):
	assert len(args) == 1
	b = args[0]
	bo = b''
	for bt in b:
		x = 0
		for i in range(8):
			x <<= 1
			x |= bt & 1
			bt >>= 1
		bo += struct.pack('B', x)
	return bo

def builtin_swapbits(rom, args):
	assert len(args) == 1
	b = args[0]
	bo = b''
	for bt in b:
		bo += struct.pack('B', bt ^ 0xFF)
	return bo

def builtin_floodtp(rom, args):
	assert len(args) == 3
	# ~ print(args)
	im = args[0]
	x, y = args[1], args[2]
	new_im = im.copy()
	ImageDraw.floodfill(new_im, (x, y), (0, 0, 0, 0))
	return new_im

def builtin_has(rom, args):
	assert len(args) == 2
	lst = args[0]
	chk = args[1]
	return chk in lst

def builtin_clip(rom, args):
	assert len(args) in (2, 3)
	dat = args[0]
	if len(args) == 2:
		stt = 0
		end = args[1]
	else:
		stt = args[1]
		end = args[2]
	return dat[stt:end]

def builtin_tell(rom, args):
	assert len(args) == 0
	return rom.f.tell()

def builtin_tell2(rom, args):
	assert len(args) == 0
	loc = rom.f.tell()
	bnk = loc // 0x4000
	adr = loc % 0x4000 + (bnk != 0) * 0x4000
	return f'{bnk:0>2X}:{adr:0>4X}'

def builtin_str(rom, args):
	assert len(args) == 1
	return str(args[0])

def builtin_romcrc(rom, args):
	assert len(args) == 0
	loc = rom.f.tell()
	rom.f.seek(0)
	raw = rom.f.read()
	rom.f.seek(loc)
	return crc32(raw)

def builtin_image(rom, args):
	assert len(args) in (2, 3, 5)
	if len(args) == 2:
		col = None
	elif len(args) == 3:
		col = imutil.pal_from_raw(struct.pack('H', args[2]), False)[0]
	else:
		col = (args[2], args[3], args[4])
	w = args[0]
	h = args[1]
	im = Image.new('RGBA', (w, h))
	if not col is None:
		im.paste(col, (0, 0, w, h))
	return im

def builtin_paste(rom, args):
	assert len(args) == 4
	im_i = args[0]
	x = args[1]
	y = args[2]
	im_b = args[3].copy()
	im_b.paste(im_i, (x, y))
	return im_b

token_re = re.compile(r'^(\.?[^ {}()[\]+*-/,!"=<>]+|\{|\}|\[|\]|\(|\)|\+|\*|-|\/|,|!=?|"[^"]*"|<=?|>=?|==|@3)')
def get_s_tkn(s):
	m = token_re.match(s)
	if not m:
		raise Exception('Token error')
	t = m.groups()[0]
	s_o = s[m.span()[1]:]
	return s_o, t

def get_line_tokens(_l):
	l = _l
	tkn = []
	while len(l):
		l, t = get_s_tkn(l)
		tkn.append(t)
		while len(l) and l[0] in (' ', '\t'):
			l = l[1:]
	return tkn

include_re = re.compile(r'^@include "(.+)"$')
def get_script_lins(fn):
	if len(fn.split('/')) == 1:
		base_dir = './'
	else:
		base_dir = fn.rsplit('/', 1)[0] + '/'
	l_o = []
	f_l = open(fn).read().split('\n')
	for l in f_l:
		m = include_re.match(l)
		if m:
			new_fn = m.groups()[0]
			new_ln = get_script_lins(base_dir + new_fn)
			l_o += new_ln
		else:
			l_o.append(l)
	return l_o

class Script:
	builtin_funs = {
		'getdata':  builtin_getdata,
		'lz77':     builtin_lz77,
		'lzi':      builtin_lzi,
		'len':      builtin_len,
		'fread':    builtin_fread,
		'int':      builtin_int,
		'make3':    builtin_make3,
		'make2':    builtin_make2,
		'make1':    builtin_make2,
		'make1bpp': builtin_make1bpp,
		'revbits':  builtin_revbits,
		'swapbits': builtin_swapbits,
		'center2':  builtin_center2,
		'center1':  builtin_center2,
		'fileout':  builtin_fileout,
		'array':    builtin_array,
		'list':     builtin_list,
		'dict':     builtin_dict,
		'sdict':    builtin_sdict,
		'indkey':   builtin_indkey,
		'checkhit': builtin_checkhit,
		'char':     builtin_char,
		'bpp12':    builtin_bpp12,
		'bpp24':    builtin_bpp24,
		'bpp14':    builtin_bpp14,
		'bytes':    builtin_bytes,
		'floodtp':  builtin_floodtp,
		'has':      builtin_has,
		'clip':     builtin_clip,
		'tell':     builtin_tell,
		'tell2':    builtin_tell2,
		'str':      builtin_str,
		'romcrc':   builtin_romcrc,
		'image':    builtin_image,
		'paste':    builtin_paste,

		'fmti': lambda r, a: str(a[0]).rjust(a[1]),

		'id': lambda r, a: f'{id(a[0]):0>16X}',
	}
	block_cmds = (
		'if', 'for', 'while',
	)
	def __init__(self, fn):
		lins = get_script_lins(fn)
		lins = [l.split('#', 1)[0] for l in lins]
		self.lins = [l.strip() for l in lins if l.strip()]
		self.lini = 0
		self.block_stack = []
		self.fun_stack = [('', len(self.lins))]
		self.vars = {}
		self.funs = {}
		self.ret_val = None
		self.namespace = ''

	def run(self, rom):
		while self.lini < len(self.lins):
			l = self.lins[self.lini]
			self.lini += 1
			if self.do_line(l, rom):
				return self.ret_val
		return self.ret_val

	def do_line(self, lin, rom):
		tkn = get_line_tokens(lin)
		cmd = tkn[0]
		args = tkn[1:]

		if cmd == 'return':
			self.cmd_return(args, rom)
			# ~ return self.
			# purge old fun namespace vals
			old_namespace_pre = self.namespace + '.'
			keys = list(self.vars.keys())
			for k in keys:
				if k.startswith(old_namespace_pre):
					del self.vars[k]
			self.namespace, self.lini = self.fun_stack.pop()
			return True
		elif cmd == 'set':
			self.cmd_set(args, rom)
		elif cmd == 'for':
			self.cmd_for(args, rom)
		elif cmd == 'while':
			self.cmd_while(args, rom)
		elif cmd == 'seek3':
			self.cmd_seek3(args, rom)
		elif cmd == 'seek3@':
			self.cmd_seek3at(args, rom)
		elif cmd == 'seek2' or cmd == 'seek1':
			self.cmd_seek2(args, rom)
		elif cmd == 'seek2ba' or cmd == 'seek1ba':
			self.cmd_seek2ba(args, rom)
		elif cmd == 'seek2ab' or cmd == 'seek1ab':
			self.cmd_seek2ab(args, rom)
		elif cmd == 'seek2@' or cmd == 'seek1@':
			self.cmd_seek2at(args, rom)
		elif cmd == 'outim':
			self.cmd_outim(args, rom)
		elif cmd == 'end':
			self.cmd_end(args, rom)
		elif cmd == 'break':
			self.cmd_break(args, rom)
		elif cmd == 'echo':
			self.cmd_echo(args, rom)
		elif cmd == 'push':
			self.cmd_push(args, rom)
		elif cmd == 'if':
			self.cmd_if(args, rom)
		elif cmd == 'else':
			self.cmd_else(args, rom)
		elif cmd == 'def':
			self.cmd_def(args, rom)
		elif cmd == 'purge':
			self.cmd_purge(args, rom)
		elif cmd == 'printvars':
			print(list(self.vars.keys()))
		elif cmd == 'pause':
			input()
		else:
			print(f'Unknown command "{cmd}"')
			exit()
		return False

	def varname(self, n):
		if self.namespace == '':
			return n
		return self.namespace + '.' + n

	def cmd_set(self, args, rom):
		nam = self.varname(args[0])
		num = self.resolve_value(args[1:], rom)
		if nam != '_':
			self.vars[nam] = num

	def cmd_for(self, args, rom):
		var = self.varname(args[0])
		vals = self.make_args_list(args[1:], rom)
		self.vars[var] = vals[0]
		self.block_stack.append(('for', var, vals[1], self.lini, self.get_block_skip()))

	def cmd_while(self, args, rom):
		cond = self.resolve_value(args, rom)
		if cond:
			self.block_stack.append(('while', args, self.lini, self.get_block_skip()))
		else:
			self.skip_block()
			self.lini += 1

	def cmd_seek(self, args, rom):
		pass

	def cmd_seek3(self, args, rom):
		dest = self.resolve_value(args, rom)
		rom.f.seek(dest)

	def cmd_seek3at(self, args, rom):
		dest = readp(rom.f)
		rom.f.seek(dest)

	def cmd_seek2(self, args, rom):
		args_ = self.make_args_list(args, rom)
		if len(args_) == 1:
			dest = args_[0]
		else:
			b, a = args_
			dest = ba2a(b, a)
		rom.f.seek(dest)

	def cmd_seek2ba(self, args, rom):
		b = readb(rom.f)
		a = readh(rom.f)
		dest = ba2a(b, a)
		rom.f.seek(dest)

	def cmd_seek2ab(self, args, rom):
		a = readh(rom.f)
		b = readb(rom.f)
		dest = ba2a(b, a)
		rom.f.seek(dest)

	def cmd_seek2at(self, args, rom):
		cur_loc = rom.f.tell()
		cur_bank = cur_loc // 0x4000
		dest = ba2a(cur_bank, readh(rom.f))
		rom.f.seek(dest)

	def cmd_clip(self, args, rom):
		var = self.get_var(args[0])
		num = self.resolve_value(args[1:], rom)
		var = var[:num]

	def cmd_outim(self, args, rom):
		var = self.get_var(args[0])
		path, path_act = self.resolve_value(args[1:], rom)
		if not os.path.exists(path):
			os.makedirs(path)
		var.save(path_act)

	def cmd_end(self, args, rom):
		block_dat = self.block_stack[-1]
		if block_dat[0] == 'for':
			cur_val = self.vars[block_dat[1]]
			cur_val += 1
			self.vars[block_dat[1]] = cur_val
			if cur_val < block_dat[2]:
				self.lini = block_dat[3]
			else:
				del self.vars[block_dat[1]]
				self.block_stack.pop()
		elif block_dat[0] == 'if':
			self.block_stack.pop()
		elif block_dat[0] == 'while':
			cond = self.resolve_value(block_dat[1], rom)
			if cond:
				self.lini = block_dat[2]
			else:
				self.block_stack.pop()
		else:
			print('ERROR')
			exit()

	def cmd_break(self, args, rom):
		while True:
			block_dat = self.block_stack.pop()
			if block_dat[0] in ('for', 'while'):
				break
		if block_dat[0] == 'for':
			self.lini = block_dat[4]
		elif block_dat[0] == 'while':
			self.lini = block_dat[3]
		self.lini += 1

	def cmd_echo(self, args, rom):
		val = self.resolve_value(args, rom)
		print('-', val)

	def cmd_push(self, args, rom):
		var = self.get_var(args[0])
		val = self.resolve_value(args[1:], rom)
		var.append(val)

	def cmd_if(self, args, rom):
		cond = self.resolve_value(args, rom)
		if cond:
			self.block_stack.append(('if', ))
		else:
			if self.skip_block():
				self.block_stack.append(('if', ))
			self.lini += 1

	def cmd_else(self, args, rom):
		self.skip_block()

	def cmd_def(self, args, rom):
		nam = args[0]
		ext = args[1:]
		assert ext[0] == '{' and ext[-1] == '}'
		ext = ext[1:-1]
		start_lin = self.lini

		self.funs[nam] = (nam, ext, start_lin)

		self.skip_block()
		self.lini += 1

	def cmd_return(self, args, rom):
		val = self.resolve_value(args, rom)
		self.ret_val = val

	def cmd_purge(self, args, rom):
		nam = self.varname(args[0])
		del self.vars[nam]

	def get_block_skip(self):
		store = self.lini
		self.skip_block()
		pos = self.lini
		self.lini = store
		return pos

	def skip_block(self):
		cur_depth = 1
		hit_else = False
		for i in range(self.lini, len(self.lins)):
			cmd = get_line_tokens(self.lins[i])[0]
			if cmd in self.block_cmds:
				cur_depth += 1
			elif cmd == 'end':
				cur_depth -= 1
			elif cmd == 'else':
				cur_depth -= 1
				if cur_depth != 0:
					cur_depth += 1
				else:
					hit_else = True
			if cur_depth == 0:
				break
		self.lini = i
		return hit_else

	def is_fun(self, nam):
		if nam in self.funs.keys(): return True
		return nam in self.builtin_funs.keys()

	def is_var(self, nam):
		if nam in self.vars.keys():
			return True
		return self.namespace + '.' + nam in self.vars.keys()

	def get_var(self, nam):
		if self.namespace + '.' + nam in self.vars.keys():
			return self.vars[self.namespace + '.' + nam]
		return self.vars[nam]

	def call_user_fun(self, rom, fun_dat, args):
		cur_pos = self.lini
		self.fun_stack.append((self.namespace, cur_pos))
		for i,v in enumerate(fun_dat[1]):
			self.vars[fun_dat[0] + '.' + v] = args[i]
		self.namespace = fun_dat[0]
		self.lini = fun_dat[2]
		self.run(rom)
		return self.ret_val
		# ~ print(fun_dat, args)

	def get_fun_by_name(self, nam):
		if nam in self.funs.keys():
			fun_dat = self.funs[nam]
			fun = lambda rom, args: self.call_user_fun(rom, fun_dat, args)
			return fun
			# ~ print(fun_dat, self.lin_i)
			# ~ return self.funs[nam]
		return self.builtin_funs[nam]

	def get_value(self, last_result, queue, rom):
		x = queue.pop(0)
		if x == '(':
			new_queue = match_pair_token(queue, '(', ')')
			eval_in = self.resolve_value(new_queue, rom)
			return eval_in
		elif x == '[':
			new_queue = match_pair_token(queue, '[', ']')
			eval_in = self.resolve_value(new_queue, rom)
			return last_result[eval_in]
		elif len(x) >= 2 and x[0] == '"' and x[-1] == '"':
			return x[1:-1]
		elif x == '+':
			nxt = self.get_value(None, queue, rom)
			return last_result + nxt
		elif x == '-':
			nxt = self.get_value(None, queue, rom)
			if last_result is None:
				return -nxt
			return last_result - nxt
		elif x == '*':
			nxt = self.get_value(None, queue, rom)
			return last_result * nxt
		elif x == '/':
			nxt = self.get_value(None, queue, rom)
			return last_result // nxt
		elif x == '%':
			nxt = self.get_value(None, queue, rom)
			return last_result % nxt
		elif x == '|':
			nxt = self.get_value(None, queue, rom)
			return last_result | nxt
		elif x == '&':
			nxt = self.get_value(None, queue, rom)
			return last_result & nxt
		elif x == '||':
			nxt = self.get_value(None, queue, rom)
			return last_result or nxt
		elif x == '&&':
			nxt = self.get_value(None, queue, rom)
			return last_result and nxt
		elif x == '!':
			nxt = self.get_value(None, queue, rom)
			return not nxt
		elif x == '==':
			nxt = self.get_value(None, queue, rom)
			return last_result == nxt
		elif x == '!=':
			nxt = self.get_value(None, queue, rom)
			return last_result != nxt
		elif x == '>':
			nxt = self.get_value(None, queue, rom)
			return last_result > nxt
		elif x == '>=':
			nxt = self.get_value(None, queue, rom)
			return last_result >= nxt
		elif x == '<':
			nxt = self.get_value(None, queue, rom)
			return last_result < nxt
		elif x == '<=':
			nxt = self.get_value(None, queue, rom)
			return last_result <= nxt
		elif x == '@3':
			# gba ptr
			ptr = self.get_value(None, queue, rom)
			rom.f.seek(ptr)
			# ~ val = struct.unpack('I', rom.read(4))[0] - 0x8000000
			val = readp(rom.f)
			return val
		elif self.is_fun(x):
			if len(queue) and queue[0] == '{':
				# call fun
				queue.pop(0)
				args_queue = match_pair_token(queue, '{', '}')
				args_list = self.make_args_list(args_queue, rom)
				fun = self.get_fun_by_name(x)
				rval = fun(rom, args_list)
				return rval
			return self.get_fun_by_name(x)
		elif self.is_var(x):
			return self.get_var(x)
		# integer
		if x[0] == '$':
			return int(x[1:], 16)
		elif x[0] == '%':
			return int(x[1:], 2)
		return int(x)

	def resolve_value(self, tkns, rom):
		queue = tkns.copy()
		val = None
		while len(queue):
			val = self.get_value(val, queue, rom)
		return val

	def make_args_list(self, queue, rom):
		queue.append(',')
		indiv_queues = []
		cur_queue = []
		for val in queue:
			if val == ',':
				indiv_queues.append(cur_queue)
				cur_queue = []
			else:
				cur_queue.append(val)
		arg_vals = []
		if indiv_queues == [[]]:
			return arg_vals
		for que in indiv_queues:
			arg_vals.append(self.resolve_value(que, rom))
		return arg_vals

class ROMFile:
	def __init__(self, fn):
		self.f = open(fn, 'rb')
		self.crc = crc32(self.f.read())

class HitList:
	def __init__(self):
		self.i = 0
	def set(self, key):
		self.i |= 1 << key
	def clr(self, key):
		sefl.i |= 1 << key
		sefl.i ^= 1 << key
	def get(self, key):
		return bool(self.i & (1 << key))

if __name__ == '__main__':
	import sys
	rom_fn = sys.argv[1]
	scr_fn = sys.argv[2]

	# ~ rom_f = open(rom_fn, 'rb')
	rom_f = ROMFile(rom_fn)
	scr = Script(scr_fn)
	hlst = HitList()
	hlst.set(0)
	scr.vars['hitlist'] = hlst
	scr.run(rom_f)
