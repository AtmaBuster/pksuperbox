import pokestr, by, math, random
import json, base64, zlib
import pokedb, gamedb, textdb

sqrt = lambda x: math.ceil(math.sqrt(x))

G3SUBORDER = ((0,1,2,3),(0,1,3,2),(0,2,1,3),(0,2,3,1),(0,3,1,2),(0,3,2,1),(1,0,2,3),(1,0,3,2),(1,2,0,3),(1,2,3,0),(1,3,0,2),(1,3,2,0),(2,0,1,3),(2,0,3,1),(2,1,0,3),(2,1,3,0),(2,3,0,1),(2,3,1,0),(3,0,1,2),(3,0,2,1),(3,1,0,2),(3,1,2,0),(3,2,0,1),(3,2,1,0))

def gen_pid_normal(gr, gn, ab, nt, sh, tid, sid):
	if gr in (0, 254, 255):
		low_byte = random.randint(0, 127) * 2 + ab
	else:
		while True:
			if gn == 'f':
				low_byte = random.randint(0, gr - 1)
			else:
				low_byte = random.randint(gr, 255)
			if ab == -1: break
			if low_byte & 1 != ab: continue
			break

	while True:
		mid_byte = random.randint(0, 255)

		pid_lo = (mid_byte << 8) | low_byte
		shiny_key = pid_lo ^ tid ^ sid

		for _ in range(1000):
			i = random.randint(0, 65535)
			pid = pid_lo | (i << 16)
			if pid % 25 != nt: continue
			if sh:
				if shiny_key ^ i < 8:
					break
			else:
				if shiny_key ^ i >= 8:
					break
		else:
			continue
		return pid

def gen_pid_unown(nt, sh, ltr, tid, sid):
	ltr_i = ord(ltr) - ord('A')
	ltr_vals = []
	ltr_v = ltr_i
	while ltr_v < 0x100:
		b1 = (ltr_v >> 6) & 0b11
		b2 = (ltr_v >> 4) & 0b11
		b3 = (ltr_v >> 2) & 0b11
		b4 = (ltr_v >> 0) & 0b11
		ltr_vals.append((b1 << 24) | (b2 << 16) | (b3 << 8) | (b4 << 0))
		ltr_v += 28
	ltr_anti_mask = 0xFCFCFCFC
	while True:
		pid = (random.randint(0, 0xFFFFFFFF) & ltr_anti_mask) | random.choice(ltr_vals)
		if pid % 25 != nt:
			continue
		sv = (pid >> 16) ^ (pid & 0xFFFF) ^ tid ^ sid
		if sh:
			if sv < 8:
				break
		else:
			if sv >= 8:
				break
	return pid

def gen_pid(spc, dvs, tid, sid):
	nt = (dvs ^ tid ^ sid) % 25
	sh = (dvs & 0xFF2F == 0xAA2A)
	if spc == 201: # unown
		ltr1 = (dvs >>  5) & 0b11
		ltr2 = (dvs >>  1) & 0b11
		ltr3 = (dvs >> 13) & 0b11
		ltr4 = (dvs >>  9) & 0b11
		ltrv = (ltr1 << 6) | (ltr2 << 4) | (ltr3 << 2) | (ltr4 << 0)
		ltr = chr((ltrv // 10) + ord('A'))
		return gen_pid_unown(nt, sh, ltr, tid, sid)
	ab = (dvs >> 4) & 1
	gr = pokedb.BASE_STATS[spc].gend_ratio
	if gr in (0, 254, 255):
		gn = None
	else:
		gn = 'fm'[int((dvs & 0xF0) >= gr)]
	return gen_pid_normal(gr, gn, ab, nt, sh, tid, sid)

class Mon:
	def __init__(self):
		self.species = 0
		self.nickname = ''
		self.tid = 0
		self.sid = 0
		self.pid = 0
		self.language = None
		self.ot_name = ''
		self.marking = 0
		self.held_item = 0
		self.exp = 0
		self.moves = [0, 0, 0, 0]
		self.pp    = [0, 0, 0, 0]
		self.pp_up = [0, 0, 0, 0]
		self.friendship = 0
		self.ev = [0, 0, 0, 0, 0, 0]
		self.condition = [0, 0, 0, 0, 0, 0]
		self.pokerus = 0
		self.met_location = 255
		self.met_time = ''
		self.ot_gender = ''
		self.ball = ''
		self.game = ''
		self.game_id = 0
		self.met_lv = 0
		self.is_egg = False
		self.ability = 0
		self.ability_ind = 0
		self.iv = [0, 0, 0, 0, 0, 0]
		self.ribbons = []
		self.extra = {}

	def copy(self):
		new_poke = Mon()
		new_poke.load(self.save())
		return new_poke

	def save(self):
		d = {}
		d['game'] = self.game
		d['s'] = self.species
		d['n'] = self.nickname
		d['p'] = self.pid
		d['id'] = (self.tid, self.sid)
		d['l'] = self.language
		d['ot'] = (self.ot_name, self.ot_gender)
		d['mrk'] = self.marking
		d['itm'] = self.held_item
		d['x'] = self.exp
		d['mov'] = (self.moves, self.pp, self.pp_up)
		d['fr'] = self.friendship
		d['stt'] = (self.ev, self.iv, self.condition)
		d['rus'] = self.pokerus
		d['met'] = (self.met_location, self.met_time, self.ball, self.game_id, self.met_lv)
		d['egg'] = self.is_egg
		d['ab'] = (self.ability, self.ability_ind)
		d['rib'] = self.ribbons
		if self.extra != {}:
			d['ex'] = self.extra
		s = json.dumps(d, separators=(',',':'))
		s_c = zlib.compress(s.encode('ascii'))
		s_b = base64.b64encode(s_c).decode('ascii')
		return s_b

	def load(self, s_b):
		s_c = base64.b64decode(s_b.encode('ascii'))
		s = zlib.decompress(s_c).decode('ascii')
		d = json.loads(s)
		self.game = d['game']
		self.species = d['s']
		self.nickname = d['n']
		self.pid = d['p']
		self.tid, self.sid = d['id']
		self.language = d['l']
		self.ot_name, self.ot_gender = d['ot']
		self.marking = d['mrk']
		self.held_item = d['itm']
		self.exp = d['x']
		self.moves, self.pp, self.pp_up = d['mov']
		self.friendship = d['fr']
		self.ev, self.iv, self.condition = d['stt']
		self.pokerus = d['rus']
		self.met_location, self.met_time, self.ball, self.game_id, self.met_lv = d['met']
		self.is_egg = d['egg']
		self.ability, self.ability_ind = d['ab']
		self.ribbons = d['rib']
		self.extra = d.get('ex', {})

	def update_game_inds(self):
		self.species = gamedb.get_mon_index(self.game, self.species)
		for i in range(4):
			self.moves[i] = gamedb.get_move_index(self.game, self.moves[i])
		self.held_item = gamedb.get_item_index(self.game, self.held_item)
		self.ability = pokedb.BASE_STATS[self.species].abils[self.ability_ind]
		if self.met_location != 0xFF:
			self.met_location = gamedb.get_landmark_index(self.game, self.met_location)
		if self.met_location == -1:
			self.met_location = 0xFF

	def apply_extras(self, *args):
		if self.game == 'clover':
			dat, sub = args
			self.extra['hiddenability'] = bool(sub[0][10])

	def get_origins_string(self):
		if self.met_lv == -1:
			return 'Unknown origins.'
		if not self.met_time is None:
			time_s = {'morn':'in the morning','day':'during the day','night':'at night'}[self.met_time]
		if self.met_location == 0xFF:
			loc = 'a fateful encounter'
		elif self.met_location == 0xFE:
			loc = 'a trade'
		else:
			loc = textdb.landmark(self.met_location)[1]
		if self.met_lv == 0:
			# hatched
			if self.met_time is None:
				return f'Hatched at {loc}.'
			return f'Hatched in {loc} {time_s}.'
		if self.met_time is None:
			return f'Met in {loc} at Lv{self.met_lv}.'
		return f'Met in {loc} at Lv{self.met_lv} {time_s}.'

	def print_profile(self):
		base_data = pokedb.BASE_STATS[self.species]
		lv = pokedb.get_mon_level(self.exp, base_data.exp_gp_id)
		stats = self.stats
		abil_info = textdb.ability(self.ability)
		print(f' {self.nickname:<10} / {base_data.name}')
		print(f'    Lv{lv}')
		print('.---------------.--------------.')
		print(f'| HP      : {stats[0]:>3} | Sp.Atk : {stats[4]:>3} |')
		print(f'| Attack  : {stats[1]:>3} | Sp.Def : {stats[5]:>3} |')
		print(f'| Defense : {stats[2]:>3} | Speed  : {stats[3]:>3} |')
		print('\'---------------\'--------------\'')
		print(f'Ability : {abil_info[0]}')
		print(f'        : {abil_info[1]}')
		print(self.get_origins_string())

	@property
	def stats(self):
		base_data = pokedb.BASE_STATS[self.species]
		base_stat = base_data.base_val
		lv = pokedb.get_mon_level(self.exp, base_data.exp_gp_id)
		if gamedb.get_game_info(self.game, 'gen') == 3:
			nature_mul = [10, 10, 10, 10, 10, 10]
			nature = self.pid % 25
			nature_mul[(nature % 5) + 1] -= 1
			nature_mul[(nature // 5) + 1] += 1
			nature_mul = tuple(nature_mul)
		else:
			nature_mul = (10, 10, 10, 10, 10, 10)

		stats = []
		# calc hp
		stats.append(((2 * base_stat[0] + self.iv[0] + (sqrt(self.ev[0]) // 4)) * lv) // 100 + lv + 10)
		# other stats
		for i in range(1, 6):
			stats.append(((((2 * base_stat[i] + self.iv[i] + (sqrt(self.ev[i]) // 4)) * lv) // 100 + 5) * nature_mul[i]) // 10)
		return tuple(stats)

	@property
	def shiny(self):
		return ((self.pid & 0xFFFF) ^ (self.pid >> 16) ^ self.tid ^ self.sid) < 8

	@property
	def level(self):
		return pokedb.get_mon_level(self.exp, pokedb.BASE_STATS[self.species].exp_gp_id)

	@property
	def gender(self):
		gr = pokedb.BASE_STATS[self.species].gend_ratio
		if gr == 0: return 'male'
		if gr == 254: return 'female'
		if gr == 255: return 'unknown'
		pid_lo = self.pid & 0xFF
		if pid_lo < gr:
			return 'female'
		return 'male'

	@property
	def letter(self):
		b1 = (self.pid >> 24) & 0b11
		b2 = (self.pid >> 16) & 0b11
		b3 = (self.pid >>  8) & 0b11
		b4 = (self.pid >>  0) & 0b11
		b = (b1 << 6) | (b2 << 4) | (b3 << 2) | b4
		li = b % 28
		if li == 26: return '!'
		if li == 27: return '?'
		return chr(li + ord('A'))

	def to_gen1(self):
		b_out = b''
		b_out += by.eb(gamedb.get_mon_index_r(self.game, self.species))
		b_out += by.ehe(self.stats[0])
		b_out += by.eb(self.level)
		b_out += b'\x00\x00\x00'
		b_out += by.eb(gamedb.get_item_index_r(self.game, self.held_item))
		b_out += by.eb(gamedb.get_move_index_r(self.game, self.moves[0]))
		b_out += by.eb(gamedb.get_move_index_r(self.game, self.moves[1]))
		b_out += by.eb(gamedb.get_move_index_r(self.game, self.moves[2]))
		b_out += by.eb(gamedb.get_move_index_r(self.game, self.moves[3]))
		b_out += by.ehe(self.tid)
		b_out += by.eb(self.exp >> 16)
		b_out += by.ehe(self.exp & 0xFFFF)
		b_out += by.eh(self.ev[0])
		b_out += by.eh(self.ev[1])
		b_out += by.eh(self.ev[2])
		b_out += by.eh(self.ev[3])
		b_out += by.eh(self.ev[4])
		atk_def = (self.iv[1] // 2) * 0x10 + (self.iv[2] // 2)
		spd_spc = (self.iv[3] // 2) * 0x10 + (self.iv[4] // 2)
		b_out += by.eb(atk_def)
		b_out += by.eb(spd_spc)
		for i in range(4):
			pp_val = (self.pp_up[i] << 6) | self.pp[i]
			b_out += by.eb(pp_val)
		return b_out

	def to_gen2(self):
		b_out = b''
		b_out += by.eb(gamedb.get_mon_index_r(self.game, self.species))
		b_out += by.eb(gamedb.get_item_index_r(self.game, self.held_item))
		b_out += by.eb(gamedb.get_move_index_r(self.game, self.moves[0]))
		b_out += by.eb(gamedb.get_move_index_r(self.game, self.moves[1]))
		b_out += by.eb(gamedb.get_move_index_r(self.game, self.moves[2]))
		b_out += by.eb(gamedb.get_move_index_r(self.game, self.moves[3]))
		b_out += by.ehe(self.tid)
		b_out += by.eb(self.exp >> 16)
		b_out += by.ehe(self.exp & 0xFFFF)
		b_out += by.eh(self.ev[0])
		b_out += by.eh(self.ev[1])
		b_out += by.eh(self.ev[2])
		b_out += by.eh(self.ev[3])
		b_out += by.eh(self.ev[4])
		atk_def = (self.iv[1] // 2) * 0x10 + (self.iv[2] // 2)
		spd_spc = (self.iv[3] // 2) * 0x10 + (self.iv[4] // 2)
		b_out += by.eb(atk_def)
		b_out += by.eb(spd_spc)
		for i in range(4):
			pp_val = (self.pp_up[i] << 6) | self.pp[i]
			b_out += by.eb(pp_val)
		b_out += by.eb(self.friendship)
		b_out += by.eb(self.pokerus)
		#
		try:
			landmark_out = gamedb.get_landmark_index_r(self.game, self.met_location)
		except:
			landmark_out = 0x00
		if self.met_time == 'morn':
			time_i = 1
		elif self.met_time == 'day':
			time_i = 2
		elif self.met_time == 'night':
			time_i = 3
		else:
			time_i = 0
		if self.met_lv == 0:
			met_lv = 1
		else:
			met_lv = self.met_lv
		if self.ot_gender == 'male':
			gend = 0x00
		else:
			gend = 0x80
		byt1 = (time_i << 6) | met_lv
		byt2 = landmark_out | gend
		b_out += by.eh(byt2 * 0x100 + byt1)
		#
		b_out += by.eb(self.level)
		return b_out

	def to_gen3(self):
		if self.language == 'JPN':
			enc_fun = pokestr.enc3j
		else:
			enc_fun = pokestr.enc3e
		b_out = b''
		b_out += by.ew(self.pid)
		b_out += by.eh(self.tid)
		b_out += by.eh(self.sid)
		b_out += enc_fun(self.nickname, 10)
		lang_id = (None, 'JPN', 'ENG', 'FRE', 'ITA', 'GER', 'KOR', 'SPA').index(self.language)
		b_out += by.eb(lang_id)
		egg_flag = 0b10
		if self.is_egg:
			egg_flag |= 0b100
		b_out += by.eb(egg_flag)
		b_out += enc_fun(self.ot_name, 7)
		b_out += by.eb(self.marking)

		substructs = [b'', b'', b'', b'']

		substructs[0] += by.eh(gamedb.get_mon_index_r(self.game, self.species))
		substructs[0] += by.eh(gamedb.get_item_index_r(self.game, self.held_item))
		substructs[0] += by.ew(self.exp)
		pp_up_b = (self.pp_up[0] << 0) | (self.pp_up[1] << 2) | (self.pp_up[2] << 4) | (self.pp_up[3] << 6)
		substructs[0] += by.eb(pp_up_b)
		substructs[0] += by.eb(self.friendship)
		if self.game == 'clover':
			if self.extra.get('hiddenability', False):
				b1 = 1
			else:
				b1 = 0
			if self.shiny:
				b2 = 1
			else:
				b2 = 0
			substructs[0] += by.eb(b1)
			substructs[0] += by.eb(b2)
		else:
			substructs[0] += b'\x00\x00'
		# ~ print(self.game)
		# ~ import struct
		# ~ substructs[0] += struct.pack('H', 0b0000_0001_0000_0000)

		substructs[1] += by.eh(gamedb.get_move_index_r(self.game, self.moves[0]))
		substructs[1] += by.eh(gamedb.get_move_index_r(self.game, self.moves[1]))
		substructs[1] += by.eh(gamedb.get_move_index_r(self.game, self.moves[2]))
		substructs[1] += by.eh(gamedb.get_move_index_r(self.game, self.moves[3]))
		substructs[1] += by.eb(self.pp[0])
		substructs[1] += by.eb(self.pp[1])
		substructs[1] += by.eb(self.pp[2])
		substructs[1] += by.eb(self.pp[3])

		# balance evs
		ev_out = [sqrt(e) for e in self.ev]
		if sum(ev_out) > 510:
			ev_sum = sum(ev_out)
			new_ev = [int(510 * (e / ev_sum)) for e in ev_out]
			while sum(new_ev) < 510:
				new_ev[new_ev.index(min(new_ev))] += 1
			ev_out = new_ev
		for i in range(6):
			substructs[2] += by.eb(ev_out[i])
		for i in range(6):
			substructs[2] += by.eb(self.condition[i])

		substructs[3] += by.eb(self.pokerus)
		try:
			landmark_out = gamedb.get_landmark_index_r(self.game, self.met_location)
		except:
			landmark_out = 0xFF
		substructs[3] += by.eb(landmark_out)
		origins = 0
		if self.ot_gender == 'female':
			origins |= 0x8000
		origins |= pokedb.CAUGHT_BALL.index(self.ball) << 11
		origins |= pokedb.GAME_OF_ORIGIN.index(self.game_id) << 7
		origins |= self.met_lv
		substructs[3] += by.eh(origins)
		iv_dat = 0
		abils = pokedb.BASE_STATS[self.species].abils
		if self.ability in abils:
			abil_ind = abils.index(self.ability)
		else:
			abil_ind = self.ability_ind
		iv_dat |= (abil_ind << 31)
		if self.is_egg:
			iv_dat |= (1 << 30)
		for i,iv in enumerate(self.iv):
			iv_dat |= (iv << (i * 5))
		substructs[3] += by.ew(iv_dat)
		ribbon_i = self.get_ribbon_flags()
		substructs[3] += by.ew(ribbon_i)

		chk = by.sum_b(b''.join(substructs), 2)
		b_out += by.eh(chk)
		b_out += b'\x00\x00'
		# ~ b_out += b'\xFF\xFF'

		enc_key = self.pid ^ (self.sid * 0x10000 + self.tid)
		for o in G3SUBORDER[self.pid % 24]:
			b_out += by.xor_b(substructs[o], enc_key, 4)

		return b_out

	def get_contest_ribbon_ct(self, ind0):
		if ind0 + 3 in self.ribbons: return 4
		if ind0 + 2 in self.ribbons: return 3
		if ind0 + 1 in self.ribbons: return 2
		if ind0 + 0 in self.ribbons: return 1
		return 0

	def get_ribbon_flags(self):
		cool_ct = self.get_contest_ribbon_ct(0)
		beau_ct = self.get_contest_ribbon_ct(4)
		cute_ct = self.get_contest_ribbon_ct(8)
		smrt_ct = self.get_contest_ribbon_ct(12)
		toug_ct = self.get_contest_ribbon_ct(16)
		ribbon_i = (cool_ct << 0) | (beau_ct << 3) | (cute_ct << 6) | (smrt_ct << 9) | (toug_ct << 12)
		for i in range(20, 32):
			if i in self.ribbons:
				ribbon_i |= (1 << (i - 5))
		return ribbon_i

def open_mon(dat):
	if dat is None: return None
	if isinstance(dat, Mon): return dat
	mn = Mon()
	mn.load(dat)
	return mn

def name_hash(nam):
	i = 0
	for c in nam:
		i <<= 3
		i ^= ord(c)
	j = 0
	while i:
		j ^= (i & 0xFFFF)
		i >>= 16
	return j ^ 22222

CATCH_RATE_ITEMS = {
	25:146,45:83,50:174,90:173,100:173,120:173,135:173,190:173,
	195:173,220:173,250:173,255:173,
}
def gen1_to_mon(dat, nick, otname):
	# takes the 33-byte boxmon struct from Gen 1, as well as the pair of names, and converts it to Mon
	mon = Mon()

	mon.species = by.gb(dat, 0)
	mon.nickname = nick
	mon.tid = by.ghe(dat, 12)
	mon.sid = name_hash(otname) ^ mon.tid
	mon.ot_name = otname
	itm_id = by.gb(dat, 7)
	mon.held_item = CATCH_RATE_ITEMS.get(itm_id, itm_id)
	exp_hi = by.gb(dat, 14)
	exp_lo = by.ghe(dat, 15)
	mon.exp = (exp_hi << 16) | exp_lo
	mon.moves = [by.gb(dat, i) for i in range(8, 12)]
	pp_dat = [by.gb(dat, i) for i in range(29, 33)]
	mon.pp = [x & 0x3F for x in pp_dat]
	mon.pp_up = [x >> 6 for x in pp_dat]
	mon.friendship = 70
	for i in range(5):
		mon.ev[i] = by.ghe(dat, 17 + i * 2)
	mon.ev[5] = mon.ev[4]
	mon.pokerus = 0
	mon.met_location = 0
	mon.met_time = 0
	mon.ot_gender = 'male'
	mon.met_lv = -1
	mon.ball = 'POKé'
	raw_dv = by.ghe(dat, 27)
	mon.iv[1] = ((raw_dv >> 12) & 0xF) * 2
	mon.iv[2] = ((raw_dv >>  8) & 0xF) * 2
	mon.iv[3] = ((raw_dv >>  4) & 0xF) * 2
	mon.iv[4] = ((raw_dv >>  0) & 0xF) * 2
	mon.iv[5] = mon.iv[4]
	mon.iv[0] = ((((raw_dv>>12)&1)<<3)|(((raw_dv>>8)&1)<<2)|(((raw_dv>>4)&1)<<1)|(raw_dv&1))*2

	return mon

def gen2_to_mon(dat, nick, otname):
	# takes the 32-byte boxmon struct from Gen 2, as well as the pair of names, and converts it to Mon
	mon = Mon()

	mon.species = by.gb(dat, 0)
	mon.nickname = nick
	mon.tid = by.ghe(dat, 6)
	mon.sid = name_hash(otname) ^ mon.tid
	mon.ot_name = otname
	mon.held_item = by.gb(dat, 1)
	exp_hi = by.gb(dat, 8)
	exp_lo = by.ghe(dat, 9)
	mon.exp = (exp_hi << 16) | exp_lo
	mon.moves = [by.gb(dat, i) for i in range(2, 6)]
	pp_dat = [by.gb(dat, i) for i in range(23, 27)]
	mon.pp = [x & 0x3F for x in pp_dat]
	mon.pp_up = [x >> 6 for x in pp_dat]
	mon.friendship = by.gb(dat, 27)
	for i in range(5):
		mon.ev[i] = by.ghe(dat, 11 + i * 2)
	mon.ev[5] = mon.ev[4]
	mon.pokerus = by.gb(dat, 28)
	met_data = by.gh(dat, 29)
	if met_data != 0:
		lvl = met_data & 0x3F
		time = (met_data >> 6) & 0x3
		loc = (met_data >> 8) & 0x7F
		otg = met_data >> 15
		mon.met_location = loc
		mon.met_time = (None,'morn','day','night')[time]
		mon.ot_gender = ('male','female')[otg]
		if lvl == 1:
			mon.met_lv = 0
		else:
			mon.met_lv = lvl
	else:
		mon.met_lv = -1
	mon.ball = 'POKé'
	raw_dv = by.ghe(dat, 21)
	mon.iv[1] = ((raw_dv >> 12) & 0xF) * 2
	mon.iv[2] = ((raw_dv >>  8) & 0xF) * 2
	mon.iv[3] = ((raw_dv >>  4) & 0xF) * 2
	mon.iv[4] = ((raw_dv >>  0) & 0xF) * 2
	mon.iv[5] = mon.iv[4]
	mon.iv[0] = ((((raw_dv>>12)&1)<<3)|(((raw_dv>>8)&1)<<2)|(((raw_dv>>4)&1)<<1)|(raw_dv&1))*2

	return mon

def gen3_to_mon(dat):
	# takes the 80-byte boxmon struct from Gen 3 and converts it to Mon
	egg_flag = by.gb(dat, 19)
	if egg_flag & 0x01:
		# bad egg, uh oh
		return None
	if egg_flag & 0x02 == 0:
		# no species, also uh oh
		return None
	mon = Mon()
	lang = by.gb(dat, 18)
	if lang == 1:
		mon.language = 'JPN'
		gets = lambda d, i, l: pokestr.dec3j(d[i:i+l])
	else:
		mon.language = ('ENG','FRE','ITA','GER','KOR','SPA')[lang - 2]
		gets = lambda d, i, l: pokestr.dec3e(d[i:i+l])
	mon.pid = by.gw(dat, 0)
	mon.tid = by.gh(dat, 4)
	mon.sid = by.gh(dat, 6)
	mon.nickname = gets(dat, 8, 10)
	mon.ot_name = gets(dat, 20, 7)
	if egg_flag & 0x04:
		# use egg name
		mon.nickname = ('タマゴ','EGG','OEUF','UOVO','EI','','HUEVO')[lang - 1]
	mon.marking = by.gb(dat, 27)

	enc_key = mon.pid ^ (mon.sid * 0x10000 + mon.tid)
	substructs = [None, None, None, None]
	sub_ord = G3SUBORDER[mon.pid % 24]
	substructs[sub_ord[0]] = by.xor_b(dat[0x20:0x2C], enc_key, 4)
	substructs[sub_ord[1]] = by.xor_b(dat[0x2C:0x38], enc_key, 4)
	substructs[sub_ord[2]] = by.xor_b(dat[0x38:0x44], enc_key, 4)
	substructs[sub_ord[3]] = by.xor_b(dat[0x44:0x50], enc_key, 4)

	mon.species = by.gh(substructs[0], 0)
	mon.held_item = by.gh(substructs[0], 2)
	mon.exp = by.gw(substructs[0], 4)
	pp_up = by.gb(substructs[0], 8)
	mon.pp_up = [(pp_up >> (i * 2)) & 3 for i in range(4)]
	mon.friendship = by.gb(substructs[0], 9)
	mon.moves = [by.gh(substructs[1], i * 2) for i in range(4)]
	mon.pp = [by.gb(substructs[1], 8 + i) for i in range(4)]
	mon.ev = [by.gb(substructs[2], i) ** 2 for i in range(6)]
	mon.condition = [by.gb(substructs[2], 6 + i) for i in range(6)]
	mon.pokerus = by.gb(substructs[3], 0)
	met_loc_id = by.gb(substructs[3], 1)
	mon.met_location = met_loc_id
	mon.met_time = None
	origins = by.gh(substructs[3], 2)
	mon.met_lv = origins & 0b1111111
	game_id = (origins >> 7) & 0b1111
	mon.game_id = pokedb.GAME_OF_ORIGIN[game_id]
	mon.ball = pokedb.CAUGHT_BALL[(origins >> 11) & 0b1111]
	mon.ot_gender = ('male','female')[origins >> 15]
	iv_ex_dat = by.gw(substructs[3], 4)
	iv_dat = iv_ex_dat & 0x3fffffff
	mon.is_egg = bool((iv_ex_dat >> 30) & 1)
	abil_id = iv_ex_dat >> 31
	mon.ability_ind = abil_id
	mon.ability = pokedb.BASE_STATS[mon.species].abils[abil_id]
	mon.iv = [(iv_dat >> (i * 5)) & 0b11111 for i in range(6)]

	# ribbons
	ribbon_i = by.gw(substructs[3], 8)
	cool_ct = (ribbon_i >> 0)  & 0b111
	beau_ct = (ribbon_i >> 3)  & 0b111
	cute_ct = (ribbon_i >> 6)  & 0b111
	smrt_ct = (ribbon_i >> 9)  & 0b111
	toug_ct = (ribbon_i >> 12) & 0b111
	for i in range(cool_ct):
		mon.ribbons.append(i + 0)
	for i in range(beau_ct):
		mon.ribbons.append(i + 4)
	for i in range(cute_ct):
		mon.ribbons.append(i + 8)
	for i in range(smrt_ct):
		mon.ribbons.append(i + 12)
	for i in range(toug_ct):
		mon.ribbons.append(i + 16)
	for i in range(15, 27):
		if (ribbon_i >> i) & 1:
			mon.ribbons.append(i + 5)

	return mon, substructs

def get_decoded_gen3_mon(dat):
	enc_key = by.gw(dat, 0) ^ by.gw(dat, 4)
	hdr = dat[:0x20]
	sbs = dat[0x20:]
	sbs_d = by.xor_b(sbs, enc_key, 4)
	return hdr + sbs_d

if __name__ == '__main__':
	test_str = 'D178A72E4ED39949C0CCBFBEBFCCC3BDC5FF0202BBCEC7BBFF0000008B3800003FAF4C8F9FAB3E679FAB3E679FF33BC5E2AECD5E9F2B3E67D4AB2867D6AB786786A134689CAB8367BBD333679F543E67'
	# ~ test_str = 'CE7ECD6F89E7CA9F0C884686559987952682E7817EEE7F14281E0FFF00442C5D'
	# ~ test_str = 'CB00A8F25E17CA9F0F4240C1B5C570BB8AA3AC9ECD212ED00F0A14FF008F2564'
	# ~ test_str = '280008920907CA9F02F75D45654EE6462459B6417D00000F0A0F0FFE00C1103E'
	poke_test = by.s2b(test_str)

	mn = gen3_to_mon(poke_test)
	mn.game = 'firered_e'
	# ~ mn = gen2_to_mon(poke_test, 'EL JEFE', 'ATMA')
	# ~ mn.game = 'crystal_e'

	mn.update_game_inds()

	mn.print_profile()

	# ~ ttt = mn.save()
	# ~ mn2 = Mon()
	# ~ mn2.load(ttt)
	# ~ print(mn.__dict__)
	# ~ print(mn2.__dict__)
	# ~ print(mn.__dict__ == mn2.__dict__)
	# ~ for k in mn.__dict__.keys():
		# ~ if mn.__dict__[k] != mn2.__dict__[k]:
			# ~ print(k)
