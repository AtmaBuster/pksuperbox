import run_script as scr
import os, sys, shutil
import os.path

def list_files(path):
	return [path + f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

crcscr = {
	0x1F1C08FB : ('emerald', 'Pokémon Emerald Version'),
	0xFD6EB54C : ('altairsirius', 'Pokémon Altair'),
	0x4404DCB3 : ('altairsirius', 'Pokémon Sirius'),
	0xEA87BD6E : ('vega', 'Pokémon Vega'),
	0x3CAB0ABA : ('frigo', 'Pokémon Frigo Returns'),
	0xCE1B46EB : ('reforged', 'Pokémon Gold 97: Reforged'),
	0x5DF73EF7 : ('reforged', 'Pokémon Silver 97: Reforged'),
	0x300699D8 : ('rubydestinyrol', 'Pokémon Ruby Destiny: Reign of Legends'),
	0xDD88761C : ('firered', 'Pokémon FireRed Version'),
	0x84EE4776 : ('firered', 'Pokémon FireRed Version'),
	0xD69C96CC : ('leafgreen', 'Pokémon LeafGreen Version'),
	0xDAFFECEC : ('leafgreen', 'Pokémon LeafGreen Version'),
	0x926EE644 : ('brown', 'Pokémon Brown'),
}
crc_prio = ( # higher in list = first to run
	0xDD88761C, 0x84EE4776, # firered
	0xD69C96CC, 0xDAFFECEC, # leafgreen
	0x1F1C08FB, # emerald
	0xEA87BD6E, # vega
	0xFD6EB54C, # altair
	0x4404DCB3, # sirius
	0x3CAB0ABA, # frigo
	0xCE1B46EB, # reforged gold
	0x5DF73EF7, # reforged silver
	0x926EE644, # brown
	0x300699D8, # ruby destiny reign of legends
)

def try_file(rom, hits):
	scr_nam, gam_nam = crcscr[rom.crc]
	print(f'Found "{gam_nam}"')
	scr_fn = f'scripts/{scr_nam}.srp'
	runner = scr.Script(scr_fn)
	runner.vars['hitlist'] = hits
	print(f'Running "{scr_fn}"...')
	retval = runner.run(rom)
	new_mon_ct = 0
	for i in retval:
		if not hits.get(i):
			new_mon_ct += 1
		hits.set(i)
	print(f'Done. Got {new_mon_ct} new Pokémon sprites.')

def clean():
	pth = '../assets/image/mon/'
	dlist = [pth + f for f in os.listdir(pth)]
	for p in dlist:
		shutil.rmtree(p)

def main():
	fil = list_files('roms/')
	fil_act = []
	for filnam in fil:
		rom = scr.ROMFile(filnam)
		if rom.crc in crcscr.keys():
			fil_act.append(rom)
	fil_act = sorted(fil_act, key=lambda x: crc_prio.index(x.crc))
	hitlist = scr.HitList()
	hitlist.set(0)
	if len(fil_act) == 0:
		print('Could not find any valid ROMs in this directory')
	else:
		for filnam in fil_act:
			try_file(filnam, hitlist)
		print()
		print('Finished all valid ROMs in this directory!')
	print('Copying built-in images...')
	shutil.copytree('builtin/mon/', '../assets/image/mon/', dirs_exist_ok=True)
	print('Copied!')

if __name__ == '__main__':
	args = sys.argv[1:]
	if len(args) == 1 and args[0] == 'clean':
		clean()
	else:
		main()
