import poke, pokedb, by, pokestr, gamedb, random
from zlib import crc32

sseek = lambda f, a, p: f.seek(p[a[0]] + a[1])

class Save1:
	def __init__(self, rom_path, sav_path):
		self.sav_path = sav_path
		# get rom crc, so we know which game we're targeting
		rom_f = open(rom_path, 'rb')
		crc = crc32(rom_f.read())
		if not crc in gamedb.GAME_CRC.keys():
			raise Exception(f'Invalid ROM CRC : {crc:0>8X}')
		self.game, self.is_jpn, self.v_id, self.game_name = gamedb.GAME_CRC[crc]

		save_f = open(self.sav_path, 'rb')
		self.valid = True

		if not self.verify_all_checksums(save_f):
			self.valid = False
			return

		self.game_data = {
			'player_name': self.read_data_from_save(save_f, 'player_name', 'n'),
			'player_gender': 'male',
			'player_tid': self.read_data_from_save(save_f, 'player_tid', 'h'),
			'player_sid': None,
			'player_playtime': self.read_data_from_save(save_f, 'player_playtime', 't'),
		}
		self.game_data['player_sid'] = poke.name_hash(self.game_data['player_name']) ^ self.game_data['player_tid']

		self.pokedex_data = self.get_pokedex_data(save_f)
		self.box_data = self.get_box_data(save_f)

	def read_data_from_save(self, save_f, key, typ):
		addr = gamedb.get_game_info(self.game, 'A_' + key)
		save_f.seek(addr)
		if typ == 'n':
			# name
			if self.is_jpn:
				raw = save_f.read(5)
				return pokestr.dec1j(raw)
			raw = save_f.read(7)
			return pokestr.dec1e(raw)
		elif typ == 'b':
			# byte
			return by.rb(save_f)
		elif typ == 'h':
			# half
			return by.rhe(save_f)
		elif typ == 't':
			# playtime
			hr = by.rb(save_f)
			by.rb(save_f)
			mn, sc, fr = by.rb(save_f), by.rb(save_f), by.rb(save_f)
			return (hr, mn, sc, fr)
		else:
			raise Exception

	def get_pokedex_data(self, save_f):
		dex_size = len(gamedb.get_game_info(self.game, 'nat_dex')) - 1
		bit_size = dex_size // 8
		if dex_size % 8 != 0:
			bit_size += 1

		seen_a = gamedb.get_game_info(self.game, 'A_pokedex_seen')
		save_f.seek(seen_a)
		seen_dat = save_f.read(bit_size)

		seen_flag = 0
		for b in seen_dat[::-1]:
			seen_flag <<= 8
			seen_flag |= b

		own_a = gamedb.get_game_info(self.game, 'A_pokedex_own')
		save_f.seek(own_a)
		own_dat = save_f.read(bit_size)

		own_flag = 0
		for b in own_dat[::-1]:
			own_flag <<= 8
			own_flag |= b

		return [True, seen_flag, own_flag]

	def get_name_list(self, save_f, dfun, siz, n1, n2):
		lst = []
		for _ in range(n1):
			lst.append(dfun(save_f.read(siz)))
		for _ in range(n2 - n1):
			lst.append(None)
			save_f.read(siz)
		return lst

	def get_one_box(self, save_f, addr, max_mons):
		save_f.seek(addr)
		mon_ct = by.rb(save_f)
		spc = [by.rb(save_f) for _ in range(max_mons + 1)]
		mons = [save_f.read(33) for _ in range(max_mons)]
		if self.is_jpn:
			name_size = 6
			name_fun = pokestr.dec1j
		else:
			name_size = 11
			name_fun = pokestr.dec1e
		ot_ns = self.get_name_list(save_f, name_fun, name_size, mon_ct, max_mons)
		nicks = self.get_name_list(save_f, name_fun, name_size, mon_ct, max_mons)

		dat = []
		for i in range(max_mons):
			if i >= mon_ct:
				dat.append(None)
				continue
			species, raw, ot, nick = spc[i], mons[i], ot_ns[i], nicks[i]
			mon = poke.gen1_to_mon(raw, nick, ot)
			mon.language = gamedb.get_game_info(self.game, 'language')
			mon.is_egg = False
			mon.game = self.game
			mon.update_game_inds()
			mon.pid = poke.gen_pid(mon.species, by.gh(raw, 27), mon.tid, mon.sid)
			dat.append(mon)
		return dat

	def get_box_data(self, save_f):
		box_addrs = gamedb.get_game_info(self.game, 'A_box_data')
		cur_box_addr = gamedb.get_game_info(self.game, 'A_cur_box')
		max_mons = gamedb.get_game_info(self.game, 'box_data_size')
		cur_box_data_addr = gamedb.get_game_info(self.game, 'A_cur_box_data')
		boxes = []
		names = []
		papers = []

		save_f.seek(cur_box_addr)
		cur_data = by.rb(save_f)
		has_switched_boxes = bool(cur_data & 0x80)
		current_box = cur_data & 0x7F
		for i,adr in enumerate(box_addrs):
			names.append(f'Box {i+1}')
			if max_mons == 20:
				papers.append(-2)
			elif max_mons == 30:
				papers.append(15)
			if i == current_box:
				adr = cur_box_data_addr
			else:
				if not has_switched_boxes:
					boxes.append([None] * max_mons)
					continue
			boxes.append(self.get_one_box(save_f, adr, max_mons))
		return (boxes, names, papers, current_box)

	def check_mon_valid(self, mon):
		game_mons = gamedb.get_game_info(self.game, 'nat_dex')
		game_movs = gamedb.get_game_info(self.game, 'move_list')
		game_item = gamedb.get_game_info(self.game, 'item_list')
		if not mon.species in game_mons:
			return False
		if not mon.held_item in game_item:
			return False
		for mv in mon.moves:
			if not mv in game_movs:
				return False
		# verify DVs
		if mon.iv[1] % 2 != 0: return False
		if mon.iv[2] % 2 != 0: return False
		if mon.iv[3] % 2 != 0: return False
		if mon.iv[4] % 2 != 0: return False
		if mon.iv[5] != mon.iv[4]: return False
		return True

	def verify_main_checksum(self, save_f):
		chk_val, chk_dest = self.calc_main_checksum(save_f)
		save_f.seek(chk_dest)
		return by.rb(save_f) == chk_val

	def verify_box_checksum(self, save_f, box0, boxn, dest):
		chk_vals = self.calc_box_checksum(save_f, box0, boxn)
		save_f.seek(dest)
		for i in range(boxn - box0 + 1):
			if by.rb(save_f) != chk_vals[i]: return False
		return True

	def verify_all_checksums(self, save_f):
		if not self.verify_main_checksum(save_f): return False

		cur_box_addr = gamedb.get_game_info(self.game, 'A_cur_box')
		save_f.seek(cur_box_addr)
		has_switched_boxes = bool(by.rb(save_f) & 0x80)
		if not has_switched_boxes: return True
		for b0, bn, d in gamedb.get_game_info(self.game, 'box_checksum'):
			if not self.verify_box_checksum(save_f, b0, bn, d): return False
		return True

	def calc_checksum(self, save_f, ranges):
		chk = 0
		for sp, ep in ranges:
			save_f.seek(sp)
			for _ in range(ep - sp):
				chk += by.rb(save_f)
		return 0xFF ^ (chk & 0xFF)

	def calc_main_checksum(self, save_f):
		r, d = gamedb.get_game_info(self.game, 'checksum_range')
		return (self.calc_checksum(save_f, r), d)

	def calc_box_checksum(self, save_f, box0, boxn):
		chks = []
		addrs = gamedb.get_game_info(self.game, 'A_box_data')
		datl = gamedb.get_game_info(self.game, 'box_data_len')
		chks.append(self.calc_checksum(save_f, ((addrs[box0], addrs[box0] + ((boxn - box0) * datl)),)))
		for i in range(box0, boxn):
			adr = addrs[i]
			chks.append(self.calc_checksum(save_f, ((adr, adr + datl),)))
		return chks

	def fix_main_checksum(self, save_f):
		chk_val, chk_dest = self.calc_main_checksum(save_f)
		save_f.seek(chk_dest)
		save_f.write(by.eh(chk_val))

	def fix_box_checksum(self, save_f, box0, boxn, dest):
		chk_vals = self.calc_box_checksum(save_f, box0, boxn)
		save_f.seek(dest)
		for i in range(boxn - box0 + 1):
			by.wb(save_f, chk_vals[i])

	def fix_all_checksums(self, save_f):
		self.fix_main_checksum(save_f)
		for b0, bn, d in gamedb.get_game_info(self.game, 'box_checksum'):
			self.fix_box_checksum(save_f, b0, bn, d)

	def save_to_file(self, target_game=None):
		for j,box in enumerate(self.box_data[0]):
			for i in range(len(box)):
				if isinstance(box[i], str):
					mon = poke.Mon()
					box[i] = mon.load(box[i])
		self.add_owned_mons_to_dex()
		save_f = open(self.sav_path, 'rb+')
		self.write_pokedex_data(save_f)
		self.write_box_data(save_f, target_game)
		self.fix_all_checksums(save_f)

	def add_owned_mons_to_dex(self):
		for bx in self.box_data[0]:
			for mon in bx:
				if mon is None: continue
				if mon.is_egg: continue
				mon_dex = gamedb.get_dex_number(self.game, mon.species)
				old_own = self.pokedex_data[1] & (1 << (mon_dex - 1))
				self.pokedex_data[1] |= (1 << (mon_dex - 1))
				self.pokedex_data[2] |= (1 << (mon_dex - 1))

	def write_pokedex_data(self, save_f):
		dex_size = len(gamedb.get_game_info(self.game, 'nat_dex')) - 1
		bit_size = dex_size // 8
		if dex_size % 8 != 0:
			bit_size += 1

		seen_a = gamedb.get_game_info(self.game, 'A_pokedex_seen')
		own_a = gamedb.get_game_info(self.game, 'A_pokedex_own')

		seen_b = b''
		own_b = b''
		for i in range(bit_size):
			seen_b += by.eb((self.pokedex_data[1] >> (i * 8)) & 0xff)
			own_b += by.eb((self.pokedex_data[2] >> (i * 8)) & 0xff)

		save_f.seek(seen_a)
		save_f.write(seen_b)
		save_f.seek(own_a)
		save_f.write(own_b)

	def write_box_data(self, save_f, target_game=None):
		box_addrs = gamedb.get_game_info(self.game, 'A_box_data')
		max_mons = gamedb.get_game_info(self.game, 'box_data_size')
		# ~ print(self.box_data[-1])

		for i,adr in enumerate(box_addrs):
			cur_box_raw = self.make_game_box_data(self.box_data[0][i], max_mons, target_game)
			save_f.seek(adr)
			save_f.write(cur_box_raw)
			if self.box_data[-1] == i:
				save_f.seek(gamedb.get_game_info(self.game, 'A_cur_box_data'))
				save_f.write(cur_box_raw)

	def make_game_box_data(self, _mons, max_mons, target_game=None):
		mons = [mon for mon in _mons if not mon is None]
		mon_ct = len(mons)
		spc = b''
		mon_data = b''
		ot_names = b''
		monnicks = b''
		if self.is_jpn:
			strlen = 6
		else:
			strlen = 11
		for mon in mons:
			if not target_game is None:
				mon.game = target_game
			spc_id = gamedb.get_mon_index_r(mon.game, mon.species)
			spc += by.eb(spc_id)
			if mon.language == 'JPN':
				strfun = pokestr.enc1j
			else:
				strfun = pokestr.enc1e
			mon_data += mon.to_gen1()
			ot_names += strfun(mon.ot_name, strlen)
			monnicks += strfun(mon.nickname, strlen)
		spc += b'\xFF'
		leftover_space = max_mons - len(mons)
		spc += b'\x00' * leftover_space
		mon_data += b'\x00' * (0x21 * leftover_space)
		ot_names += b'\x00' * (strlen * leftover_space)
		monnicks += b'\x00' * (strlen * leftover_space)
		# ~ print(list(map(len, (by.eb(mon_ct), spc, mon_data, ot_names, monnicks))))
		return by.eb(mon_ct) + spc + mon_data + ot_names + monnicks

class Save2:
	def __init__(self, rom_path, sav_path):
		self.sav_path = sav_path
		# get rom crc, so we know which game we're targeting
		rom_f = open(rom_path, 'rb')
		crc = crc32(rom_f.read())
		if not crc in gamedb.GAME_CRC.keys():
			raise Exception(f'Invalid ROM CRC : {crc:0>8X}')
		self.game, self.is_jpn, self.v_id, self.game_name = gamedb.GAME_CRC[crc]

		save_f = open(self.sav_path, 'rb')
		self.valid = True

		if not self.verify_checksum(save_f):
			self.valid = False
			return

		self.game_data = {
			'player_name': self.read_data_from_save(save_f, 'player_name', 'n'),
			'player_gender': None,
			'player_tid': self.read_data_from_save(save_f, 'player_tid', 'h'),
			'player_sid': None,
			'player_playtime': self.read_data_from_save(save_f, 'player_playtime', 't'),
		}
		if 'A_player_gender' in gamedb.GAME_DATA[self.game].keys():
			self.game_data['player_gender'] = ('male','female')[self.read_data_from_save(save_f, 'player_gender', 'b')]
		else:
			self.game_data['player_gender'] = 'male'
		self.game_data['player_sid'] = poke.name_hash(self.game_data['player_name']) ^ self.game_data['player_tid']

		self.pokedex_data = self.get_pokedex_data(save_f)
		self.box_data = self.get_box_data(save_f)

	def read_data_from_save(self, save_f, key, typ):
		addr = gamedb.get_game_info(self.game, 'A_' + key)
		save_f.seek(addr)
		if typ == 'n':
			# name
			if self.is_jpn:
				raw = save_f.read(5)
				return pokestr.dec2j(raw)
			raw = save_f.read(7)
			return pokestr.dec2e(raw)
		elif typ == 'b':
			# byte
			return by.rb(save_f)
		elif typ == 'h':
			# half
			return by.rhe(save_f)
		elif typ == 't':
			# playtime
			return (by.rb(save_f), by.rb(save_f), by.rb(save_f), by.rb(save_f))
		else:
			raise Exception

	def get_pokedex_data(self, save_f):
		dex_size = len(gamedb.get_game_info(self.game, 'nat_dex')) - 1
		bit_size = dex_size // 8
		if dex_size % 8 != 0:
			bit_size += 1

		seen_a = gamedb.get_game_info(self.game, 'A_pokedex_seen')
		save_f.seek(seen_a)
		seen_dat = save_f.read(bit_size)

		seen_flag = 0
		for b in seen_dat[::-1]:
			seen_flag <<= 8
			seen_flag |= b

		own_a = gamedb.get_game_info(self.game, 'A_pokedex_own')
		save_f.seek(own_a)
		own_dat = save_f.read(bit_size)

		own_flag = 0
		for b in own_dat[::-1]:
			own_flag <<= 8
			own_flag |= b

		return [True, seen_flag, own_flag]

	def get_name_list(self, save_f, dfun, siz, n1, n2):
		lst = []
		for _ in range(n1):
			lst.append(dfun(save_f.read(siz)))
		for _ in range(n2 - n1):
			lst.append(None)
			save_f.read(siz)
		return lst

	def get_one_box(self, save_f, addr, max_mons):
		save_f.seek(addr)
		mon_ct = by.rb(save_f)
		spc = [by.rb(save_f) for _ in range(max_mons + 1)]
		mons = [save_f.read(32) for _ in range(max_mons)]
		if self.is_jpn:
			name_size = 6
			name_fun = pokestr.dec2j
		else:
			name_size = 11
			name_fun = pokestr.dec2e
		ot_ns = self.get_name_list(save_f, name_fun, name_size, mon_ct, max_mons)
		nicks = self.get_name_list(save_f, name_fun, name_size, mon_ct, max_mons)

		dat = []
		for i in range(max_mons):
			if i >= mon_ct:
				dat.append(None)
				continue
			species, raw, ot, nick = spc[i], mons[i], ot_ns[i], nicks[i]
			mon = poke.gen2_to_mon(raw, nick, ot)
			mon.language = gamedb.get_game_info(self.game, 'language')
			if species == 0xFD:
				mon.is_egg = True
			else:
				mon.is_egg = False
			mon.game = self.game
			mon.update_game_inds()
			mon.pid = poke.gen_pid(mon.species, by.gh(raw, 21), mon.tid, mon.sid)
			dat.append(mon)
		return dat

	def get_box_data(self, save_f):
		box_addrs = gamedb.get_game_info(self.game, 'A_box_data')
		nam_addrs = gamedb.get_game_info(self.game, 'A_box_name')
		max_mons = gamedb.get_game_info(self.game, 'box_data_size')
		boxes = []
		names = []
		papers = []

		for i,adr in enumerate(box_addrs):
			boxes.append(self.get_one_box(save_f, adr, max_mons))
			save_f.seek(nam_addrs + 9 * i)
			raw_name = save_f.read(9)
			if self.is_jpn:
				names.append(pokestr.dec2j(raw_name))
			else:
				names.append(pokestr.dec2e(raw_name))
			if max_mons == 20:
				papers.append(-2)
			elif max_mons == 30:
				papers.append(15)
		save_f.seek(gamedb.get_game_info(self.game, 'A_cur_box'))
		current_box = by.rb(save_f)
		return (boxes, names, papers, current_box)

	def check_mon_valid(self, mon):
		game_mons = gamedb.get_game_info(self.game, 'nat_dex')
		game_movs = gamedb.get_game_info(self.game, 'move_list')
		game_item = gamedb.get_game_info(self.game, 'item_list')
		if not mon.species in game_mons:
			return False
		if not mon.held_item in game_item:
			return False
		for mv in mon.moves:
			if not mv in game_movs:
				return False
		# verify DVs
		if mon.iv[1] % 2 != 0: return False
		if mon.iv[2] % 2 != 0: return False
		if mon.iv[3] % 2 != 0: return False
		if mon.iv[4] % 2 != 0: return False
		if mon.iv[5] != mon.iv[4]: return False
		return True

	def verify_checksum(self, save_f):
		chk_val, chk_dest = self.calc_checksum(save_f)
		save_f.seek(chk_dest)
		return by.rh(save_f) == chk_val

	def calc_checksum(self, save_f):
		r, d = gamedb.get_game_info(self.game, 'checksum_range')
		chk = 0
		for s, e in r:
			save_f.seek(s)
			for _ in range(e - s):
				chk += by.rb(save_f)
		return (chk & 0xFFFF, d)

	def fix_checksum(self, save_f):
		chk_val, chk_dest = self.calc_checksum(save_f)
		save_f.seek(chk_dest)
		save_f.write(by.eh(chk_val))

	def save_to_file(self, target_game=None):
		for j,box in enumerate(self.box_data[0]):
			for i in range(len(box)):
				if isinstance(box[i], str):
					mon = poke.Mon()
					box[i] = mon.load(box[i])
		self.add_owned_mons_to_dex()
		save_f = open(self.sav_path, 'rb+')
		self.write_pokedex_data(save_f)
		self.write_box_data(save_f, target_game)
		self.fix_checksum(save_f)

	def add_owned_mons_to_dex(self):
		for bx in self.box_data[0]:
			for mon in bx:
				if mon is None: continue
				if mon.is_egg: continue
				mon_dex = gamedb.get_dex_number(self.game, mon.species)
				old_own = self.pokedex_data[1] & (1 << (mon_dex - 1))
				self.pokedex_data[1] |= (1 << (mon_dex - 1))
				self.pokedex_data[2] |= (1 << (mon_dex - 1))

	def write_pokedex_data(self, save_f):
		dex_size = len(gamedb.get_game_info(self.game, 'nat_dex')) - 1
		bit_size = dex_size // 8
		if dex_size % 8 != 0:
			bit_size += 1

		seen_a = gamedb.get_game_info(self.game, 'A_pokedex_seen')
		own_a = gamedb.get_game_info(self.game, 'A_pokedex_own')

		seen_b = b''
		own_b = b''
		for i in range(bit_size):
			seen_b += by.eb((self.pokedex_data[1] >> (i * 8)) & 0xff)
			own_b += by.eb((self.pokedex_data[2] >> (i * 8)) & 0xff)

		save_f.seek(seen_a)
		save_f.write(seen_b)
		save_f.seek(own_a)
		save_f.write(own_b)

	def write_box_data(self, save_f, target_game=None):
		box_addrs = gamedb.get_game_info(self.game, 'A_box_data')
		max_mons = gamedb.get_game_info(self.game, 'box_data_size')

		for i,adr in enumerate(box_addrs):
			cur_box_raw = self.make_game_box_data(self.box_data[0][i], max_mons, target_game)
			save_f.seek(adr)
			save_f.write(cur_box_raw)

	def make_game_box_data(self, _mons, max_mons, target_game=None):
		mons = [mon for mon in _mons if not mon is None]
		mon_ct = len(mons)
		spc = b''
		mon_data = b''
		ot_names = b''
		monnicks = b''
		if self.is_jpn:
			strlen = 6
		else:
			strlen = 11
		for mon in mons:
			if mon.is_egg:
				spc += b'\xFD'
			else:
				if not target_game is None:
					mon.game = target_game
				spc_id = gamedb.get_mon_index_r(mon.game, mon.species)
				# ~ print(mon.nickname, mon.species)
				spc += by.eb(spc_id)
			if mon.language == 'JPN':
				strfun = pokestr.enc2j
			else:
				strfun = pokestr.enc2e
			mon_data += mon.to_gen2()
			ot_names += strfun(mon.ot_name, strlen)
			monnicks += strfun(mon.nickname, strlen)
		spc += b'\xFF'
		leftover_space = max_mons - len(mons)
		spc += b'\x00' * leftover_space
		mon_data += b'\x00' * (0x20 * leftover_space)
		ot_names += b'\x00' * (strlen * leftover_space)
		monnicks += b'\x00' * (strlen * leftover_space)
		return by.eb(mon_ct) + spc + mon_data + ot_names + monnicks

class Save3:
	def __init__(self, rom_path, sav_path):
		self.sav_path = sav_path
		# get rom crc, so we know which game we're targeting
		rom_f = open(rom_path, 'rb')
		crc = crc32(rom_f.read())
		if not crc in gamedb.GAME_CRC.keys():
			raise Exception(f'Invalid ROM CRC : {crc:0>8X}')
		self.game, self.is_jpn, self.v_id, self.game_name = gamedb.GAME_CRC[crc]
		# figure out if save is initialized, and which slot is the
		# current one. then get section pointers
		save_f = open(self.sav_path, 'rb')
		cur_slot = self.get_current_save_slot(save_f)
		if cur_slot is None:
			# save is not initialized, or data is corrupt
			self.valid = False
			return
		self.valid = True
		self.sect_ptrs = self.get_sect_ptrs(save_f, cur_slot)
		# get important info from save, such as
		#   current tileset : TODO (need to know if in pokecenter)
		#   player name, gender, tid, and sid
		#   pokedex flags, and national dex unlock
		#   box mon data
		# -- maybe add
		#   badges
		#   other progress flags
		#     HoF, ...
		self.game_data = {
			'player_name': self.read_data_from_save(save_f, 'player_name', 's'),
			'player_gender': ('male','female')[self.read_data_from_save(save_f, 'player_gender', 'b')],
			'player_tid': self.read_data_from_save(save_f, 'player_tid', 'h'),
			'player_sid': self.read_data_from_save(save_f, 'player_sid', 'h'),
			'player_playtime': self.read_data_from_save(save_f, 'player_playtime', 't'),
		}
		self.pokedex_data = self.get_pokedex_data(save_f)
		if self.pokedex_data is None:
			self.valid = False
			return
		self.box_data = self.get_box_data(save_f)

	def read_data_from_save(self, save_f, key, typ):
		addr = gamedb.get_game_info(self.game, 'A_' + key)
		sseek(save_f, addr, self.sect_ptrs)
		if typ == 's':
			# string
			raw = save_f.read(0x20)
			if self.is_jpn:
				return pokestr.dec3j(raw)
			return pokestr.dec3e(raw)
		elif typ == 'b':
			# byte
			return by.rb(save_f)
		elif typ == 'h':
			# half
			return by.rh(save_f)
		elif typ == 'w':
			# word
			return by.rw(save_f)
		elif typ == 't':
			# playtime
			return (by.rh(save_f), by.rb(save_f), by.rb(save_f), by.rb(save_f))
		else:
			raise Exception

	def check_mon_valid(self, mon):
		game_mons = gamedb.get_game_info(self.game, 'nat_dex')
		game_movs = gamedb.get_game_info(self.game, 'move_list')
		# ~ game_item = gamedb.get_game_info(self.game, 'item_list')
		if not mon.species in game_mons:
			return False
		# ~ if not mon.held_item in game_item:
			# ~ return False
		for mv in mon.moves:
			if not mv in game_movs:
				return False
		return True

	def get_pokedex_data(self, save_f):
		dex_size = len(gamedb.get_game_info(self.game, 'nat_dex')) - 1
		bit_size = dex_size // 8
		if dex_size % 8 != 0:
			bit_size += 1
		# first, verify seen dex data
		seen1_a = gamedb.get_game_info(self.game, 'A_pokedex_seen1')
		seen2_a = gamedb.get_game_info(self.game, 'A_pokedex_seen2')
		seen3_a = gamedb.get_game_info(self.game, 'A_pokedex_seen3')
		sseek(save_f, seen1_a, self.sect_ptrs)
		seen1 = save_f.read(bit_size)
		sseek(save_f, seen2_a, self.sect_ptrs)
		seen2 = save_f.read(bit_size)
		sseek(save_f, seen3_a, self.sect_ptrs)
		seen3 = save_f.read(bit_size)
		if seen1 != seen2 or seen2 != seen3 or seen1 != seen3:
			return None
		seen_flag = 0
		for b in seen1[::-1]:
			seen_flag <<= 8
			seen_flag |= b
		# next, verify nat dex flags
		flag_type = gamedb.get_game_info(self.game, 'pokedex_nat_flags')
		nat1_a = gamedb.get_game_info(self.game, 'A_pokedex_nat1')
		# ~ nat2_a = gamedb.get_game_info(self.game, 'A_pokedex_nat2')
		nat3_a = gamedb.get_game_info(self.game, 'A_pokedex_nat3')
		if flag_type == 0:
			sseek(save_f, nat1_a, self.sect_ptrs)
			nat1 = by.rh(save_f)
			# ~ sseek(save_f, nat2_a, self.sect_ptrs)
			# ~ nat2 = by.rb(save_f)
			sseek(save_f, nat3_a, self.sect_ptrs)
			nat3 = by.rh(save_f)
			if nat1 == 0xDA01:
				has_nat1 = True
			elif nat1 == 0x0000:
				has_nat1 = False
			else:
				return None
			# ~ if nat2 & 0b01000000:
				# ~ has_nat2 = True
			# ~ else:
				# ~ has_nat2 = False
			if nat3 == 0x0302:
				has_nat3 = True
			elif nat3 == 0x0000:
				has_nat3 = False
			else:
				return None
		elif flag_type == 1:
			sseek(save_f, nat1_a, self.sect_ptrs)
			nat1 = by.rb(save_f)
			# ~ sseek(save_f, nat2_a, self.sect_ptrs)
			# ~ nat2 = by.rb(save_f)
			sseek(save_f, nat3_a, self.sect_ptrs)
			nat3 = by.rh(save_f)
			if nat1 == 0xB9:
				has_nat1 = True
			elif nat1 == 0x00:
				has_nat1 = False
			else:
				return None
			# ~ if nat2 & 0b00000001:
				# ~ has_nat2 = True
			# ~ else:
				# ~ has_nat2 = False
			if nat3 == 0x6258:
				has_nat3 = True
			elif nat3 == 0x0000:
				has_nat3 = False
			else:
				return None
		# ~ if not (has_nat1 == has_nat2 and has_nat2 == has_nat3):
		if not (has_nat1 == has_nat3):
			return None
		has_nat = has_nat1
		# finally, get own dex data
		own_a = gamedb.get_game_info(self.game, 'A_pokedex_own')
		sseek(save_f, own_a, self.sect_ptrs)
		own = save_f.read(bit_size)
		own_flag = 0
		for b in own[::-1]:
			own_flag <<= 8
			own_flag |= b
		return [has_nat, seen_flag, own_flag]

	def write_pokedex_data(self, save_f):
		dex_size = len(gamedb.get_game_info(self.game, 'nat_dex')) - 1
		bit_size = dex_size // 8
		if dex_size % 8 != 0:
			bit_size += 1

		seen1_a = gamedb.get_game_info(self.game, 'A_pokedex_seen1')
		seen2_a = gamedb.get_game_info(self.game, 'A_pokedex_seen2')
		seen3_a = gamedb.get_game_info(self.game, 'A_pokedex_seen3')
		flag_type = gamedb.get_game_info(self.game, 'pokedex_nat_flags')
		nat1_a = gamedb.get_game_info(self.game, 'A_pokedex_nat1')
		nat2_a = gamedb.get_game_info(self.game, 'A_pokedex_nat2')
		nat3_a = gamedb.get_game_info(self.game, 'A_pokedex_nat3')
		own_a = gamedb.get_game_info(self.game, 'A_pokedex_own')

		seen_b = b''
		own_b = b''
		for i in range(bit_size):
			seen_b += by.eb((self.pokedex_data[1] >> (i * 8)) & 0xff)
			own_b += by.eb((self.pokedex_data[2] >> (i * 8)) & 0xff)

		sseek(save_f, nat2_a, self.sect_ptrs)
		nat_2_byte = by.rb(save_f)
		if flag_type == 0:
			if self.pokedex_data[0]:
				sseek(save_f, nat1_a, self.sect_ptrs)
				by.wh(save_f, 0xDA01)
				sseek(save_f, nat2_a, self.sect_ptrs)
				by.wb(save_f, nat_2_byte | 0b01000000)
				sseek(save_f, nat3_a, self.sect_ptrs)
				by.wh(save_f, 0x0302)
			else:
				sseek(save_f, nat1_a, self.sect_ptrs)
				by.wh(save_f, 0x0000)
				sseek(save_f, nat2_a, self.sect_ptrs)
				by.wb(save_f, nat_2_byte & 0b10111111)
				sseek(save_f, nat3_a, self.sect_ptrs)
				by.wh(save_f, 0x0000)
		elif flag_type == 1:
			if self.pokedex_data[0]:
				sseek(save_f, nat1_a, self.sect_ptrs)
				by.wb(save_f, 0xB9)
				sseek(save_f, nat2_a, self.sect_ptrs)
				by.wb(save_f, nat_2_byte | 0b00000001)
				sseek(save_f, nat3_a, self.sect_ptrs)
				by.wh(save_f, 0x6258)
			else:
				sseek(save_f, nat1_a, self.sect_ptrs)
				by.wb(save_f, 0x00)
				sseek(save_f, nat2_a, self.sect_ptrs)
				by.wb(save_f, nat_2_byte & 0b11111110)
				sseek(save_f, nat3_a, self.sect_ptrs)
				by.wh(save_f, 0x0000)
		sseek(save_f, seen1_a, self.sect_ptrs)
		save_f.write(seen_b)
		sseek(save_f, seen2_a, self.sect_ptrs)
		save_f.write(seen_b)
		sseek(save_f, seen3_a, self.sect_ptrs)
		save_f.write(seen_b)
		sseek(save_f, own_a, self.sect_ptrs)
		save_f.write(own_b)

	def get_box_data(self, save_f):
		# box data is the sum of sects [5,13]
		raw = b''
		for i in range(5, 14):
			sect_size = gamedb.get_game_info(self.game, 'checksum_lens')[i]
			save_f.seek(self.sect_ptrs[i])
			raw += save_f.read(sect_size)
		raw_names = raw[0x8344:0x83C2]
		raw_paper = raw[0x83C2:]
		names = []
		for i in range(14):
			cur = raw_names[i*9:i*9+9]
			if self.is_jpn:
				names.append(pokestr.dec3j(cur))
			else:
				names.append(pokestr.dec3e(cur))
		papers = list(raw_paper)
		boxes = []
		for bx_i in range(14):
			cur_box = []
			for mn_i in range(30):
				ind = bx_i * 30 + mn_i
				cur_mon_raw = raw[4 + ind * 0x50:4 + ind * 0x50 + 0x50]
				if cur_mon_raw == b'\x00' * 0x50:
					cur_box.append(None)
					continue
				mon = poke.gen3_to_mon(cur_mon_raw)
				mon.game = self.game
				mon.update_game_inds()
				cur_box.append(mon)
			boxes.append(cur_box)
		current_box = by.gw(raw, 0)
		return (boxes, names, papers, current_box)

	def write_box_data(self, save_f, target_game=None):
		raw = by.ew(self.box_data[3])
		for bx in self.box_data[0]:
			for mon in bx:
				if mon is None:
					raw += b'\x00' * 0x50
				else:
					if not target_game is None:
						mon.game = target_game
					raw += mon.to_gen3()
		for nm in self.box_data[1]:
			if self.is_jpn:
				raw += pokestr.enc3j(nm, 9)
			else:
				raw += pokestr.enc3e(nm, 9)
		for wp in self.box_data[2]:
			raw += by.eb(wp)
		loc = 0
		cur_sect = 5
		sect_sizes = gamedb.get_game_info(self.game, 'checksum_lens')
		while loc < len(raw):
			amt_to_write = min(sect_sizes[cur_sect], len(raw) - loc)
			save_f.seek(self.sect_ptrs[cur_sect])
			save_f.write(raw[loc:loc+amt_to_write])
			loc += amt_to_write
			cur_sect += 1

	def get_current_save_slot(self, save_f):
		cur_slot = None
		cur_save_num = -1
		# check slot 0
		for i in range(14):
			chk = self.verify_sect(save_f, i * 0x1000)
			if chk == False: break
		else:
			cur_slot = 0
			save_f.seek(0xFFC)
			cur_save_num = by.rw(save_f)
		# check slot 1
		for i in range(14):
			chk = self.verify_sect(save_f, (i + 14) * 0x1000)
			if chk == False: break
		else:
			save_f.seek(0xEFFC)
			new_save_num = by.rw(save_f)
			if new_save_num > cur_save_num:
				cur_slot = 1
		return cur_slot

	def verify_sect(self, save_f, sect_loc):
		save_f.seek(sect_loc + 0xFF4)
		sect_id = by.rh(save_f)
		if sect_id >= 0xE:
			return False
		sect_size = gamedb.get_game_info(self.game, 'checksum_lens')[sect_id]
		chk_calc = self.calc_checksum(save_f, sect_loc, sect_size)
		save_f.seek(sect_loc + 0xFF6)
		chk_read = by.rh(save_f)
		return chk_read == chk_calc

	def calc_checksum(self, save_f, sect_loc, sect_size):
		c = 0
		save_f.seek(sect_loc)
		for _ in range(sect_size // 4):
			c += by.rw(save_f)
		c = c & 0xffffffff
		return ((c >> 16) + (c & 0xffff)) & 0xffff

	def get_sect_ptrs(self, save_f, slot):
		ptrs = [None]*0xE
		for i in range(14):
			save_f.seek(0xE000 * slot + 0x1000 * i + 0xFF4)
			sect_id = by.rh(save_f)
			ptrs[sect_id] = 0xE000 * slot + 0x1000 * i
		return ptrs

	def fix_all_checksums(self, save_f):
		for i in range(14):
			loc = self.sect_ptrs[i]
			siz = gamedb.get_game_info(self.game, 'checksum_lens')[i]
			self.fix_checksum(save_f, loc, siz)

	def fix_checksum(self, save_f, sect_loc, sect_size):
		chk = self.calc_checksum(save_f, sect_loc, sect_size)
		save_f.seek(sect_loc + 0xFF6)
		save_f.write(by.eh(chk))

	def add_owned_mons_to_dex(self):
		for bx in self.box_data[0]:
			for mon in bx:
				if mon is None: continue
				if mon.is_egg: continue
				mon_dex = gamedb.get_dex_number(self.game, mon.species)
				old_own = self.pokedex_data[1] & (1 << (mon_dex - 1))
				self.pokedex_data[1] |= (1 << (mon_dex - 1))
				self.pokedex_data[2] |= (1 << (mon_dex - 1))

	def save_to_file(self, target_game=None):
		for j,box in enumerate(self.box_data[0]):
			for i in range(len(box)):
				if isinstance(box[i], str):
					mon = poke.Mon()
					box[i] = mon.load(box[i])
		self.add_owned_mons_to_dex()
		save_f = open(self.sav_path, 'rb+')
		self.write_pokedex_data(save_f)
		self.write_box_data(save_f, target_game)
		self.fix_all_checksums(save_f)

	def find_empty_box_slot(self):
		for bx_i,bx in enumerate(self.box_data[0]):
			for slt_i,mon in enumerate(bx):
				if mon is None:
					return (bx_i, slt_i)
		return None

	def save2mon(self, box_i, slt_i):
		chk = self.box_data[0][box_i][slt_i]
		if chk is None: return
		if isinstance(chk, str):
			mn = poke.Mon()
			mn.load(chk)
			self.box_data[0][box_i][slt_i] = mn

	def mon2save(self, box_i, slt_i):
		chk = self.box_data[0][box_i][slt_i]
		if chk is None: return
		if not isinstance(chk, str):
			self.box_data[0][box_i][slt_i] = chk.save()

	def unlock_full_dex(self):
		full_dex = int('1' * 386, 2)
		self.pokedex_data[0] = True
		self.pokedex_data[1] = full_dex
		self.pokedex_data[2] = full_dex

	# ~ def add_gift_egg(self):
		# ~ target_slot = self.find_empty_box_slot()
		# ~ if target_slot is None: return
		# ~ gift = poke.Mon()
		# ~ gift.species = 0x12A # Seedot, thx susie
		# ~ gift.tid = self.game_data['player_tid']
		# ~ gift.sid = self.game_data['player_sid']
		# ~ #gift.pid = random.randint(0, 0xFFFFFFFF)
		# ~ pid_lo = random.randint(0, 0xFFFF)
		# ~ sv = random.randint(0, 7)
		# ~ pid_hi = gift.tid ^ gift.sid ^ pid_lo ^ sv
		# ~ gift.pid = pid_hi * 0x10000 + pid_lo
		# ~ gift.language = 'ENG'
		# ~ gift.ot_name = self.game_data['player_name']
		# ~ gift.moves = [117, 106, 147, 0]
		# ~ gift.pp = [10, 30, 15, 0]
		# ~ gift.friendship = 1
		# ~ gift.ot_gender = self.game_data['player_gender']
		# ~ gift.is_egg = True
		# ~ for i in range(6):
			# ~ test_iv = [random.randint(0, 31) for _ in range(5)]
			# ~ gift.iv[i] = max(test_iv)
		# ~ gift.ability = 34
		# ~ gift.met_location = gamedb.LANDMARKS3[0xFD]
		# ~ gift.ball = 'POKé'
		# ~ gift.game_id = 'Emerald'
		# ~ self.box_data[0][target_slot[0]][target_slot[1]] = gift

def load_save_n(n, path_g, path_s):
	cls = (None, Save1, Save2, Save3)[n]
	sav = cls(path_g, path_s)
	if not sav.valid: return None
	return sav

load_save3 = lambda g, s: load_save_n(3, g, s)
load_save2 = lambda g, s: load_save_n(2, g, s)
load_save1 = lambda g, s: load_save_n(1, g, s)

def load_save(path):
	# path should be of filetype .sav
	# and the directory should have the rom file in it
	fn, ext = path.rsplit('.', 1)
	assert ext == 'sav'
	# find rom file
	possible_ext = ('gba', 'gbc', 'gb', 'sgb')
	for ext_chk in possible_ext:
		rom_path = '.'.join((fn, ext_chk))
		try:
			rom_chk = open(rom_path, 'rb')
		except:
			continue
		break
	else:
		return None
	crc = crc32(rom_chk.read())
	if not crc in gamedb.GAME_CRC.keys():
		print(f'{crc:0>8X}')
		return None
	game_dat = gamedb.GAME_CRC[crc]
	game = gamedb.GAME_DATA[game_dat[0]]
	gen = game['gen']
	if gen == 3:
		return load_save3(rom_path, path)
	elif gen == 2:
		return load_save2(rom_path, path)
	elif gen == 1:
		return load_save1(rom_path, path)

def print_save_profile(sav):
	# ~ game_name = gamedb.get_game_info(sav.game, 'name')
	game_name = sav.game_name
	player_name = sav.game_data['player_name']
	player_id = sav.game_data['player_tid']
	playtime = sav.game_data['player_playtime']
	num_seen = by.bitct(sav.pokedex_data[1])
	num_caught = by.bitct(sav.pokedex_data[2])
	print(f'Game     : {game_name}')
	print(f'Player   : {player_name}')
	print(f'ID No.   : {player_id}')
	print(f'Playtime : {playtime[0]}:{playtime[1]:0>2}')
	print(f'Pokédex  :')
	print(f'    Seen   - {num_seen}')
	print(f'    Caught - {num_caught}')

if __name__ == '__main__':
	# ~ print('0x{:0>8X}'.format(crc32(open('em_e.gba', 'rb').read())))
	# ~ sav = load_save3('frigo/Pokémon Frigo Returns By The Phantom - Ruby Hack.sav')
	# ~ sav = load_save3('emj.sav')
	# ~ sav = load_save3('alsive/altair.sav', 'alsive/altair.gba')

	# ~ sav = load_save('alsive/altair.sav')
	# ~ sav = load_save('pokecleaf.sav')
	# ~ sav = load_save('crystal_eng1.sav')
	# ~ sav = load_save('crysclear.sav')
	# ~ sav = load_save('alsive/vega.sav')
	# ~ sav = load_save('alsive/vega_j.sav')
	# ~ sav = load_save('g1/blue.sav')
	# ~ sav = load_save('sourcrys/sourcrystal.sav')
	# ~ sav = load_save('frigo/Pokémon Frigo Returns By The Phantom - Ruby Hack.sav')
	# ~ sav = load_save('rubydestiny/rd_rol.sav')
	# ~ sav = load_save('em_e.sav')
	sav = load_save('firered/firered_eng1.sav')

	# ~ loc = gamedb.get_game_info(sav.game, 'A_player_gender')
	# ~ sseek(save_f, loc, sav.sect_ptrs)
	# ~ byt = by.rb(save_f)
	# ~ sseek(save_f, loc, sav.sect_ptrs)
	# ~ save_f.write(by.eb(byt ^ 1))
	# ~ sav.fix_all_checksums(save_f)
	# ~ save_f.close()

	print_save_profile(sav)

	save_f = open(sav.sav_path, 'rb+')
	sav.unlock_full_dex()
	sav.write_pokedex_data(save_f)

	# ~ sav.box_data[0][0][0] = sav.box_data[0][0][6].copy()
	# ~ sav.box_data[0][0][0].species = 308
	# ~ sav.box_data[0][0][0].pid = 0
	sav.box_data[0][0][0].pokerus = 0
	# ~ sav.box_data[0][0][1] = sav.box_data[0][0][0].copy()
	# ~ sav.box_data[0][0][1].pid = 0xFFFFFFFF
	sav.box_data[0][0][1].pokerus = 0xF0
	# ~ sav.box_data[0][0][2] = sav.box_data[0][0][0].copy()
	# ~ sav.box_data[0][0][2].pid = 57639070
	sav.box_data[0][0][2].pokerus = 0x0F

	sav.write_box_data(save_f)
	sav.fix_all_checksums(save_f)

	# ~ sav.box_data[0][0][2] = None
	# ~ sav.box_data[0][0][0].species = 151
	# ~ sav.box_data[0][0][0].exp = 1000000
	# ~ sav.save_to_file()
	# ~ full_dex = int('1' * 386, 2)
	# ~ sav.pokedex_data[0] = True
	# ~ sav.pokedex_data[1] = full_dex
	# ~ sav.pokedex_data[2] = full_dex
	# ~ save_f = open(sav.sav_path, 'rb+')
	# ~ save_f.close()
	# ~ print(sav.__dict__)
	# ~ print(sav.box_data[0][0])

	# ~ sav.add_gift_egg()
	# ~ sav.add_gift_egg()
	# ~ sav.add_gift_egg()
	# ~ sav.add_gift_egg()
	# ~ sav.add_gift_egg()
	# ~ sav.save_to_file()
	# ~ print()
	# ~ sav.box_data[0][0][0].print_profile()
	# ~ print()
	# ~ sav.box_data[0][0][1].print_profile()
	# ~ print()
	# ~ sav.box_data[0][0][2].print_profile()
	# ~ print(sav.box_data[0][-1][0].met_location)
