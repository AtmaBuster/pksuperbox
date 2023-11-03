def read_text_file(fn, enc=None):
	path = 'assets/text/' + fn + '.txt'
	if enc is None:
		txt = open(path).read()
	else:
		txt = open(path, encoding=enc).read()
	lins = txt.replace('#', 'é').split('\n')
	lins = [tuple(l.replace('\\n', '\n').split('@')) for l in lins if l != '']
	return tuple(lins)


# data
class DBs:
	lang_dir = ('eng','jpn','fre','ita','ger','spa')
	def __init__(self):
		self.BANKSTR  = None
		self.DEX      = None
		self.ABILITY  = None
		self.MOVE     = None
		self.LANDMARK = None
		self.NATURE   = None
		self.ITEM     = None
		self.TYPE     = None
		self.EGGGROUP = None
		self.MONFORM  = None
DB = DBs()

def load_dbs(lang):
	DB.BANKSTR  = read_text_file(DB.lang_dir[lang] + '/bankstr')
	DB.DEX      = read_text_file(DB.lang_dir[lang] + '/dex', 'utf8')
	DB.ABILITY  = read_text_file(DB.lang_dir[lang] + '/ability')
	DB.MOVE     = read_text_file(DB.lang_dir[lang] + '/move')
	DB.LANDMARK = read_text_file(DB.lang_dir[lang] + '/landmark')
	DB.NATURE   = read_text_file(DB.lang_dir[lang] + '/nature')
	DB.ITEM     = read_text_file(DB.lang_dir[lang] + '/item')
	DB.TYPE     = read_text_file(DB.lang_dir[lang] + '/type')
	DB.EGGGROUP = read_text_file(DB.lang_dir[lang] + '/egggroup')
	DB.MONFORM  = read_text_file(DB.lang_dir[lang] + '/monform', 'utf8')


# getters
def getter(i, db, defaults):
	if i < len(db):
		return db[i]
	return tuple([d.format(i) for d in defaults])

bankstr  = lambda i: getter(i, DB.BANKSTR,  ('ERROR: STRING {}',))
dex      = lambda i: getter(i, DB.DEX,      ('??????????','??????????','??????????','??????????','??????????','??????????','Unknown','0','0','0','0','There is no information available on this Pok#mon.'))
ability  = lambda i: getter(i, DB.ABILITY,  ('Ability {}', 'Unknown ability.'))
move     = lambda i: getter(i, DB.MOVE,     ('Move {}', 'Unknown move.', '0'))
landmark = lambda i: getter(i, DB.LANDMARK, ('landmark_{:X}', '???'))
nature   = lambda i: getter(i, DB.NATURE,   ('Nature {}',))
item     = lambda i: getter(i, DB.ITEM,     ('Item {}', '?????'))
mtype    = lambda i: getter(i, DB.TYPE,     ('???',))
egggroup = lambda i: getter(i, DB.EGGGROUP, ('???',))
monform  = lambda i: getter(i, DB.MONFORM,  ('???',))


# bankstring lambdas

last_bankstring = [0]
def bslambda():
	i = last_bankstring[0]
	last_bankstring[0] += 1
	return lambda: bankstr(i)[0]
bs_notimplemented      = bslambda()
bs_options_textspeed   = bslambda()
bs_options_windowframe = bslambda()
bs_options_teststring  = bslambda()
bs_bank_unsaveddata    = bslambda()
bs_options_fullscreen  = bslambda()
bs_dex_emptyentry      = bslambda()
bs_dex_unknownspecies  = bslambda()
bs_dex_speciessign     = bslambda()
bs_stat_hp             = bslambda()
bs_stat_attack         = bslambda()
bs_stat_defense        = bslambda()
bs_stat_speed          = bslambda()
bs_stat_spattack       = bslambda()
bs_stat_spdefense      = bslambda()
bs_dex_abilitysign     = bslambda()
bs_dex_heightsign      = bslambda()
bs_dex_weightsign      = bslambda()
bs_stat_total          = bslambda()
bs_dex_formsign        = bslambda()
bs_credits_code        = bslambda()
bs_credits_art         = bslambda()
bs_credits_music       = bslambda()
bs_credits_special     = bslambda()
bs_credits_nameplate   = bslambda()
bs_options_volumes     = bslambda()
bs_box_quittomenu      = bslambda()
bs_box_savedata        = bslambda()
bs_box_wallpaper       = bslambda()
bs_box_name            = bslambda()
bs_box_jumptobox       = bslambda()
bs_box_swapcontents    = bslambda()
bs_box_filterboxes     = bslambda()
bs_box_managegroups    = bslambda()
bs_box_sortboxes       = bslambda()
bs_dex_clearsort       = bslambda()
bs_dex_filtergrp       = bslambda()
bs_dex_setsort         = bslambda()
bs_dex_reversesort     = bslambda()
bs_dex_nexttype        = bslambda()
bs_dex_prevtype        = bslambda()
bs_options_shiny       = bslambda()
