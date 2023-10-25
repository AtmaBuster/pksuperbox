import struct
from PIL import Image

def conv1bpp2bpp(dat):
	bo = b''
	for i in range(len(dat)):
		bo += dat[i:i+1]
		bo += dat[i:i+1]
	return bo

def conv2bpp4bpp(dat):
	bo = b''
	print(dat)
	for i in range(len(dat) // 2):
		cur_row = dat[i*2:i*2+2]
		lo = cur_row[0]
		hi = cur_row[1]
		for i in range(4):
			cur_b = 0
			for j in range(2):
				lo_bit = lo & 1
				hi_bit = hi & 1
				lo >>= 1
				hi >>= 1
				cur_b <<= 4
				cur_b |= (hi_bit << 1) | lo_bit
			bo += struct.pack('B', cur_b)
	print(bo)
	return bo

def conv1bpp4bpp(dat):
	return conv2bpp4bpp(conv1bpp2bpp(dat))

def make_image_1bpp(dat, pal, w):
	w_p = w * 8
	h_p = len(dat) // w_p * 8
	h = h_p // 8
	imo = Image.new('RGBA', (w_p, h_p))
	pxl = imo.load()
	i = 0
	for t_y in range(h):
		for t_x in range(w):
			for p_y in range(8):
				if i >= len(dat): continue
				row = dat[i]
				for p_x in range(8):
					x_px = t_x * 8 + p_x
					y_px = t_y * 8 + p_y
					c = pal[(row >> p_x) & 1]
					pxl[x_px,y_px] = c
				i += 1
	return imo

def make_image_2(dat, pal, w, tp=False):
	w_p = w * 8
	h_p = len(dat) // w_p * 4
	if len(dat) % (w_p * 2) != 0:
		h_p += 8
	h = h_p // 8
	if tp:
		imo = Image.new('RGBA', (h_p, w_p))
	else:
		imo = Image.new('RGBA', (w_p, h_p))
	pxl = imo.load()
	i = 0
	for t_y in range(h):
		for t_x in range(w):
			for p_y in range(8):
				if i >= len(dat): continue
				pxl_lo = dat[i]
				pxl_hi = dat[i+1]
				if tp:
					txloc = t_y * 8
					tyloc = t_x * 8
				else:
					txloc = t_x * 8
					tyloc = t_y * 8
				for p_x in range(8):
					c = pal[((pxl_hi >> p_x) & 1) * 2 + ((pxl_lo >> p_x) & 1)]
					pxl[txloc+7-p_x,tyloc+p_y] = c
				i += 2
	return imo

def make_image_3(dat, pal, w):
	w_p = w * 8
	h_p = len(dat) // w_p * 2
	if len(dat) % (w_p * 2) != 0:
		h_p += 8
	h = h_p // 8
	imo = Image.new('RGBA', (w_p, h_p))
	pxl = imo.load()
	i = 0
	for t_y in range(h):
		for t_x in range(w):
			for p_y in range(8):
				for p_x in range(4):
					if i >= len(dat): continue
					p01 = dat[i]
					p0 = p01 & 0xf
					p1 = p01 >> 4
					pxl[t_x * 8 + p_x * 2 + 0, t_y * 8 + p_y] = pal[p0]
					pxl[t_x * 8 + p_x * 2 + 1, t_y * 8 + p_y] = pal[p1]
					i += 1
	return imo

def pal_from_raw(rawpal, use_tp=False):
	cols = []
	for i in range(len(rawpal) // 2):
		if i == 0 and use_tp:
			r, g, b, a = 0, 0, 0, 0
		else:
			col = struct.unpack('H', rawpal[i*2:i*2+2])[0]
			r = ((col >>  0) & 0x1f) * 8
			g = ((col >>  5) & 0x1f) * 8
			b = ((col >> 10) & 0x1f) * 8
			a = 255
		cols.append((r,g,b,a))
	return cols
